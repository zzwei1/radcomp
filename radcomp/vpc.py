#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Vertical profile classification
@author: Jussi Tiira
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.io
import matplotlib as mpl
from os import path
from functools import partial
from sklearn import decomposition
from sklearn.cluster import KMeans
from sklearn.externals import joblib
from scipy.ndimage.filters import median_filter
from radcomp import learn

HOME = path.expanduser('~')
DATA_DIR = path.join(HOME, 'DATA', 'ToJussi')
RESULTS_DIR = path.join(HOME, 'results', 'radcomp', 'vertical')
META_SUFFIX = '_metadata'
NAN_REPLACEMENT = {'ZH': -10, 'ZDR': 0, 'KDP': 0}

def mean_delta(t):
    dt = t[-1]-t[0]
    return dt/(len(t)-1)

def data_range(dt_start, dt_end):
    fnames = fname_range(dt_start, dt_end)
    pns = map(vprhimat2pn, fnames)
    return pd.concat(pns, axis=2).loc[:, :, dt_start:dt_end]

def fname_range(dt_start, dt_end):
    dt_range = pd.date_range(dt_start.date(), dt_end.date())
    dt2path_map = partial(dt2path, datadir=DATA_DIR)
    return map(dt2path_map, dt_range)

def dt2path(dt, datadir):
    return path.join(datadir, dt.strftime('%Y%m%d_IKA_VP_from_RHI.mat'))

def vprhimat2pn(datapath):
    data = scipy.io.loadmat(datapath)['VP_RHI']
    fields = list(data.dtype.fields)
    fields.remove('ObsTime')
    fields.remove('height')
    str2dt = lambda tstr: pd.datetime.strptime(tstr,'%Y-%m-%dT%H:%M:%S')
    t = list(map(str2dt, data['ObsTime'][0][0]))
    h = data['height'][0][0][0]
    data_dict = {}
    for field in fields:
        data_dict[field] = data[field][0][0].T
    return pd.Panel(data_dict, major_axis=h, minor_axis=t)

def m2km(m, pos):
    '''formatting m in km'''
    return '{:.0f}'.format(m*1e-3)

def plotpn(pn, fields=None, scaled=False, cmap='gist_ncar', n_extra_ax=0, **kws):
    if fields is None:
        fields = pn.items
    vmins = {'ZH': -15, 'ZDR': -1, 'RHO': 0, 'KDP': 0, 'DP': 0, 'PHIDP': 0}
    vmaxs = {'ZH': 30, 'ZDR': 4, 'RHO': 1, 'KDP': 0.26, 'DP': 360, 'PHIDP': 360}
    labels = {'ZH': 'dBZ', 'ZDR': 'dB', 'KDP': 'deg/km', 'DP': 'deg', 'PHIDP': 'deg'}
    n_rows = len(fields) + n_extra_ax
    fig = plt.figure(figsize=(8,3+1.1*n_rows))
    gs = mpl.gridspec.GridSpec(n_rows, 2, width_ratios=(35, 1), wspace=0.02,
                           top=1-0.22/n_rows, bottom=0.35/n_rows, left=0.1, right=0.905)
    axarr = []
    for i, field in enumerate(fields):
        subplot_kws = {}
        if i>0:
            subplot_kws['sharex'] = axarr[0]
        ax = fig.add_subplot(gs[i, 0], **subplot_kws)
        ax_cb = fig.add_subplot(gs[i, 1])
        axarr.append(ax)
        fieldup = field.upper()
        if scaled:
            scalekws = {'vmin': 0, 'vmax': 1}
            label = 'scaled'
        elif fieldup in labels:
            scalekws = {'vmin': vmins[fieldup], 'vmax': vmaxs[fieldup]}
            label = labels[fieldup]
        else:
            scalekws = {}
            label = field
        t = pn[field].columns
        t_shifted = t + mean_delta(t)/2
        im = ax.pcolormesh(t_shifted, pn[field].index, 
                      np.ma.masked_invalid(pn[field].values), cmap=cmap,
                      **scalekws, label=field, **kws)
        #fig.autofmt_xdate()
        ax.xaxis.set_major_formatter(mpl.dates.DateFormatter('%H'))
        ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(m2km))
        ax.set_ylim(0,11000)
        ax.set_ylabel('Height, km')
        #fig.colorbar(im, ax=ax, label=label)
        fig.colorbar(im, cax=ax_cb, label=label)
    for j in range(n_extra_ax):
        ax = fig.add_subplot(gs[i+1+j, 0], sharex=axarr[0])
        axarr.append(ax)
    axarr[-1].set_xlabel('Time, UTC')
    axarr[0].set_title(str(pn[field].columns[0].date()))
    for ax in axarr[:-1]:
        plt.setp(ax.get_xticklabels(), visible=False)
    return fig, axarr

def scale_data(pn):
    scaling_limits = {'ZH': (-10, 30), 'ZDR': (0, 3), 'zdr': (0, 3), 'KDP': (0, 0.5), 
                      'kdp': (0, 0.15)}
    scaled = pn.copy()
    for field, data in scaled.iteritems():
        data -= scaling_limits[field][0]
        data *= 1.0/scaling_limits[field][1]
        scaled[field] = data
    return scaled

def fillna(dat, field=''):
    data = dat.copy()
    if isinstance(data, pd.Panel):
        for field in list(data.items):
            data[field].fillna(NAN_REPLACEMENT[field.upper()], inplace=True)
    elif isinstance(data, pd.DataFrame):
        data.fillna(NAN_REPLACEMENT[field.upper()], inplace=True)
    return data

def kdp2phidp(kdp, dr_km):
    kdp_filled = kdp.fillna(0)
    return 2*kdp_filled.cumsum().multiply(dr_km, axis=0)

def prepare_pn(pn, kdpmax=0.5):
    dr = pd.Series(pn.major_axis.values, index=pn.major_axis).diff().bfill()
    dr_km = dr/1000
    pn_new = pn.copy()
    pn_new['KDP_orig'] = pn_new['KDP'].copy()
    pn_new['KDP'][pn_new['KDP']<0] = np.nan
    pn_new['phidp'] = kdp2phidp(pn_new['KDP'], dr_km)
    kdp = pn_new['KDP'] # a view
    kdp[kdp>kdpmax] = 0
    kdp[kdp<0] = 0
    pn_new = fltr_median(pn_new)
    pn_new = fltr_ground_clutter_median(pn_new)
    return pn_new

def prepare_data(pn, fields=['ZH', 'ZDR', 'kdp'], hmax=10e3, kdpmax=None):
    data = pn[fields, 0:hmax, :].transpose(0,2,1)
    if kdpmax is not None:
        data['KDP'][data['KDP']>kdpmax] = np.nan
    return fillna(data)

def class_colors(classes, ymin=-0.2, ymax=0, ax=None, cmap='Vega20', alpha=1, **kws):
    t = classes.index
    dt = mean_delta(t)*1.5
    clss = classes.shift(freq=dt).dropna().astype(int)
    if ax is None:
        ax = plt.gca()
    cm = plt.get_cmap(cmap)
    t0 = clss.index[0]
    for t1, icolor in clss.iteritems():
        if t1<=t0:
            continue
        ax.axvspan(t0, t1, ymin=ymin, ymax=ymax, facecolor=cm.colors[icolor], 
                   alpha=alpha, clip_on=False, **kws)
        t0 = t1

def plot_classes(data, classes, n_eigens):
    figs = []
    axarrs = []
    for eigen in range(n_eigens):
        i_classes = np.where(classes==eigen)[0]
        pn_class = data.iloc[:, i_classes, :]
        fig, axarr = learn.plot_class(pn_class, ylim=(-1, 2))
        axarr[0].legend().set_visible(True)
        figs.append(fig)
        axarrs.append(axarr)
        for ax in axarr:
            if ax.xaxis.get_ticklabels()[0].get_visible():
                ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(m2km))
    return figs, axarrs

def reject_outliers(df, m=2):
    d = df.subtract(df.median(axis=1), axis=0).abs()
    mdev = d.median(axis=1)
    s = d.divide(mdev, axis=0).replace(np.inf, np.nan).fillna(0)
    return df[s<m].copy()

def fltr_median(pn):
    pn_out = pn.copy()
    sizes = {'ZDR': (5, 1), 'KDP': (20, 1)}
    keys = list(map(str.lower, sizes.keys()))
    new = create_filtered_fields_if_missing(pn, sizes.keys())[keys]
    nullmask = pn['ZH'].isnull()
    for field, data in new.iteritems():
        df = median_filter_df(data, param=field, nullmask=nullmask, size=sizes[field.upper()])
        pn_out[field] = df
    return pn_out

def fltr_rolling(df, window=5, stdlim=0.1, fill_value=0, **kws):
    r = df.rolling(window=window, center=True)
    # not ready, maybe not needed

def fltr_ground_clutter(pn_orig, window=18, ratio_limit=8):
    '''simple threshold based gc filter'''
    #return pn_orig
    pn = pn_orig.copy()
    threshold = dict(ZDR=4, KDP=0.28)
    keys = list(map(str.lower, threshold.keys()))
    pn = create_filtered_fields_if_missing(pn, keys)
    for field, data in pn.iteritems():
        if field not in keys:
            continue
        for dt, col in data.iteritems():
            winsize=1
            while winsize<window:
                winsize += 1
                dat = col.iloc[:winsize].copy()
                med = dat.median()
                easy_thresh = 0.75*threshold[field.upper()]
                if med < easy_thresh or np.isnan(col.iloc[0]):
                    break # Do not filter.
                threshold_exceeded = dat.isnull().any() and med > threshold[field.upper()]
                median_limit_exceeded = med > ratio_limit*dat.abs().min()
                view = pn[field, :, dt].iloc[:window]
                if median_limit_exceeded:
                    view[view>0.95*med] = NAN_REPLACEMENT[field.upper()]
                    break
                if threshold_exceeded:
                    view[view>threshold[field.upper()]] = NAN_REPLACEMENT[field.upper()]
                    break
    return pn

def fltr_ground_clutter_median(pn, heigth_px=35, crop_px=20, size=(22, 2)):
    '''gc filter using a combination of threshold and median filter'''
    pn_new = pn.copy()
    ground_threshold = dict(ZDR=3.5, KDP=0.22)
    keys = list(map(str.lower, ground_threshold.keys()))
    pn_new = create_filtered_fields_if_missing(pn_new, keys)
    for field in keys:
        view = pn_new[field].iloc[:heigth_px]
        fltrd = median_filter_df(view, param=field, fill=True,
                                     nullmask=pn.ZH.isnull(), size=size)
        new_values = fltrd.iloc[:crop_px]
        selection = pn[field]>ground_threshold[field.upper()]
        selection.loc[:, selection.iloc[crop_px]] = False # not clutter
        selection.loc[:, selection.iloc[0]] = True
        selection.iloc[crop_px:] = False
        df = pn_new[field].copy()
        df[selection] = new_values[selection]
        pn_new[field] = df
    return pn_new

def median_filter_df(df, param=None, fill=True, nullmask=None, **kws):
    '''median_filter wrapper for DataFrames'''
    if nullmask is None:
        nullmask = df.isnull()
    if fill and param is not None:
        df_new = df.fillna(NAN_REPLACEMENT[param.upper()])
    else:
        df_new = df.copy()
    result = median_filter(df_new, **kws)
    result = pd.DataFrame(result, index=df_new.index, columns=df_new.columns)
    if param is not None:
        result[result.isnull()] = NAN_REPLACEMENT[param.upper()]
    result[nullmask] = np.nan
    return result

def create_filtered_fields_if_missing(pn, keys):
    '''copy original fields as new fields for processing'''
    pn_new = pn.copy()
    filtered_fields_exist = True
    keys = list(map(str.upper, keys))
    for key in keys:
        if key.lower() not in pn_new.items:
            filtered_fields_exist = False
    if not filtered_fields_exist:
        for key in keys:
            pn_new[key.lower()] = pn_new[key]
    return pn_new

def model_path(name):
    return path.join(RESULTS_DIR, 'models', name + '.pkl')

def save_model(model, name):
    savepath = model_path(name)
    joblib.dump(model, savepath)
    return savepath

def save_data(data, name):
    joblib.dump(data, model_path(name + '_data'))
    hmax = np.ceil(data.minor_axis.max())
    fields = list(data.items)
    metadata = dict(hmax=hmax, fields=fields)
    joblib.dump(metadata, model_path(name + META_SUFFIX))

def load_model(name):
    loadpath = model_path(name)
    model = joblib.load(loadpath)
    return model

def save_pca_kmeans(pca, kmeans, data, name):
    save_model(pca, name + '_pca')
    save_model(kmeans, name + '_kmeans')
    save_data(data, name)

def load_pca_kmeans(name):
    '''return pca, km, metadata'''
    pca = load_model(name + '_pca')
    km = load_model(name + '_kmeans')
    metadata = joblib.load(model_path(name + META_SUFFIX))
    return pca, km, metadata

def train(data_scaled, n_eigens, quiet=False, **kws):
    data_df = learn.pn2df(data_scaled)
    pca = pca_fit(data_df, n_components=n_eigens)
    if not quiet:
        learn.pca_stats(pca)
    km = kmeans(data_df, pca)
    return pca, km

def pca_fit(data_df, whiten=True, **kws):
    pca = decomposition.PCA(whiten=whiten, **kws)
    pca.fit(data_df)
    return pca

def kmeans(data_df, pca):
    km = KMeans(init=pca.components_, n_clusters=pca.n_components, n_init=1)
    km.fit(data_df)
    return km

def classify(data_scaled, km):
    data_df = learn.pn2df(data_scaled)
    return pd.Series(data=km.predict(data_df), index=data_scaled.major_axis)

def dt2pn(dt0, dt1):
    pn_raw = data_range(dt0, dt1)
    return prepare_pn(pn_raw)