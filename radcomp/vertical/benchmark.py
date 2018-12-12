# coding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals
__metaclass__ = type

from os import path

import pandas as pd

from radcomp import USER_DIR


BENCHMARK_DIR = path.join(USER_DIR, 'benchmark')


class VPCBenchmark:
    """score VPC classification results"""

    def __init__(self, data=None):
        self.data = data

    def fit(self, vpc):
        raise NotImplementedError


class ProcBenchmark(VPCBenchmark):
    """
    Compare VPC classification against a supervised process classification.
    """
    def __init__(self, **kws):
        super().__init__(**kws)
        self.data_fitted = None
        self.n_clusters = None

    @classmethod
    def from_csv(cls, name='fingerprint', **kws):
        """new instance from csv"""
        csv = path.join(BENCHMARK_DIR, name + '.csv')
        df = pd.read_csv(csv, parse_dates=['start', 'end'])
        dtypes = dict(ml=bool, hm=bool, dgz=bool, inv=bool)
        data = df.astype(dtypes)
        return cls(data=data, **kws)

    def fit(self, vpc):
        """Generate comparison with VPC."""
        dfs = []
        for start, row in self.data.iterrows():
            ser = vpc.training_result[row['start']:row['end']]
            df = pd.DataFrame(ser, columns=['cl'])
            for name, value in row.iloc[2:].iteritems():
                df[name] = value
            dfs.append(df)
        self.data_fitted = pd.concat(dfs)
        self.n_clusters = vpc.n_clusters

    def query_frac(self, cl, q='hm'):
        """fraction of matched query for a given class"""
        df = self.data_fitted
        n = df.query('cl==@cl & {}'.format(q)).shape[0]
        n_cl_occ = (df['cl'] == cl).sum()
        return n/n_cl_occ

    def query_fracs(self, q='hm'):
        """fractions of matched query per class"""
        fracs = pd.Series(index=range(self.n_clusters), data=range(self.n_clusters))
        return fracs.apply(self.query_frac, q=q)


if __name__ == '__main__':
    pb = ProcBenchmark.from_csv()
