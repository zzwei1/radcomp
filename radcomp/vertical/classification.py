# coding: utf-8
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from os import path
from sklearn import decomposition
from sklearn.cluster import KMeans
from radcomp import learn, USER_DIR
from j24 import ensure_dir


META_SUFFIX = '_metadata'
MODEL_DIR = ensure_dir(path.join(USER_DIR, 'class_schemes'))

def scheme_name(basename='baecc+1415', n_eigens=30, n_clusters=20,
                reduced=True):
    if reduced:
        qualifier = '_reduced'
    else:
        qualifier = ''
    schemefmt = '{base}_{neig}eig{nclus}clus{qualifier}'
    return schemefmt.format(base=basename, neig=n_eigens, nclus=n_clusters,
                            qualifier=qualifier)

def model_path(name):
    """/path/to/classification_scheme_name.pkl"""
    return path.join(MODEL_DIR, name + '.pkl')


def train(data_df, pca, quiet=False, reduced=False, n_clusters=20):
    if not quiet:
        learn.pca_stats(pca)
    if reduced:
        km = KMeans(init='k-means++', n_clusters=n_clusters, n_init=10)
    else:
        km = KMeans(init=pca.components_, n_clusters=pca.n_components, n_init=1)
    km.fit(data_df)
    return km


def pca_fit(data_df, whiten=False, **kws):
    pca = decomposition.PCA(whiten=whiten, **kws)
    pca.fit(data_df)
    return pca


def load(name):
    with open(model_path(name), 'rb') as f:
        return pickle.load(f)


def plot_reduced(data, n_clusters):
    # http://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_digits.html
    reduced_data = decomposition.PCA(n_components=2).fit_transform(data)
    kmeans = KMeans(init='k-means++', n_clusters=n_clusters, n_init=10)
    kmeans.fit(reduced_data) 
    # Step size of the mesh. Decrease to increase the quality of the VQ.
    h = .02     # point in the mesh [x_min, x_max]x[y_min, y_max].
    # Plot the decision boundary. For that, we will assign a color to each
    x_min, x_max = reduced_data[:, 0].min() - 1, reduced_data[:, 0].max() + 1
    y_min, y_max = reduced_data[:, 1].min() - 1, reduced_data[:, 1].max() + 1
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))
    # Obtain labels for each point in mesh. Use last trained model.
    Z = kmeans.predict(np.c_[xx.ravel(), yy.ravel()])
    # Put the result into a color plot
    Z = Z.reshape(xx.shape)
    plt.figure()
    plt.imshow(Z, interpolation='nearest',
               extent=(xx.min(), xx.max(), yy.min(), yy.max()),
               cmap=plt.cm.Vega20,
               aspect='auto', origin='lower')
    plt.plot(reduced_data[:, 0], reduced_data[:, 1], 'k.', markersize=2)
    # Plot the centroids as a white X
    centroids = kmeans.cluster_centers_
    plt.scatter(centroids[:, 0], centroids[:, 1],
                marker='x', s=169, linewidths=3,
                color='w', zorder=10)
    plt.title('K-means clustering (PCA-reduced data)\n'
              'Centroids are marked with white cross')
    plt.xlim(x_min, x_max)
    plt.ylim(y_min, y_max)
    plt.xticks(())
    plt.yticks(())


class VPC:
    """vertical profile classification scheme"""
    
    def __init__(self, pca=None, km=None, hlimits=None, params=None,
                 reduced=False, n_eigens=None):
        self.pca = pca
        self.km = km # k means
        self.hlimits = hlimits
        self.params = params
        self.params_extra = []
        self.reduced = reduced
        self.kdpmax = None
        self.data = None # training or classification data
        self._n_eigens = n_eigens

    @classmethod
    def using_metadict(cls, metadata, **kws):
        return cls(hlimits=metadata['hlimits'], params=metadata['fields'], **kws)

    @classmethod
    def load(cls, name):
        obj = load(name)
        if isinstance(obj, cls):
            return obj
        raise Exception('Not a {} object.'.format(cls))

    def save(self, name):
        with open(model_path(name), 'wb') as f:
            pickle.dump(self, f)

    def train(self, data=None, n_eigens=None, extra_df=None, **kws):
        if n_eigens is None:
            n_eigens = self._n_eigens
        if data is None:
            training_data = self.data
        else:
            training_data = self.prepare_data(data, n_components=n_eigens,
                                              extra_df=extra_df)
        km = train(training_data, self.pca, reduced=self.reduced, **kws)
        self.km = km

    def classify(self, data_scaled, **kws):
        data = self.prepare_data(data_scaled, **kws)
        return pd.Series(data=self.km.predict(data), index=data_scaled.major_axis)

    def cluster_centroids(self):
        centroids = self.km.cluster_centers_
        n_extra = len(self.params_extra)
        if n_extra<1:
            components = centroids
            extra = []
        else:
            components = centroids[:, :-n_extra]
            extra = centroids[:, -n_extra:]
        if self.reduced:
            centroids = self.pca.inverse_transform(components)
        return pd.DataFrame(centroids.T), pd.DataFrame(extra, columns=self.params_extra)

    def prepare_data(self, data_scaled, extra_df=None, n_components=0, save=True):
        metadata = dict(fields=data_scaled.items.values,
                        hlimits=(data_scaled.minor_axis.min(),
                                 data_scaled.minor_axis.max()))   
        data_df = learn.pn2df(data_scaled)
        if self.pca is None:
            self.pca = pca_fit(data_df, n_components=n_components)
        if self.reduced:
            data = pd.DataFrame(self.pca.transform(data_df), index=data_df.index)
        else:
            data = data_df
        data.index = data.index.round('1min')
        if extra_df is not None:
            data = pd.concat([data, extra_df], axis=1)
        if save:
            self.data = data
            self.params = metadata['fields']
            if extra_df is not None:
                self.params_extra = pd.DataFrame(extra_df).columns.values
            self.hlimits = metadata['hlimits']
        return data
