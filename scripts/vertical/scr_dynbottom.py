# coding: utf-8
"""dynamic profile lower limit sandbox"""
from __future__ import absolute_import, division, print_function, unicode_literals
__metaclass__ = type

import numpy as np
import matplotlib.pyplot as plt
from radcomp.vertical import case, classification


def resample(data, low, high, num=150, **interp_kws):
    """Resample rows to a given length."""
    inew = np.linspace(low, high, num)
    data1 = data.reindex(data.index.union(inew))
    return data1.interpolate(**interp_kws).loc[inew]



basename = 'melting-test'
params = ['ZH', 'zdr', 'kdp']
hlimits = (190, 10e3)
n_eigens = 20
n_clusters = 20
reduced = True
use_temperature = False
t_weight_factor = 0.8

scheme = classification.VPC(params=params, hlimits=hlimits, n_eigens=n_eigens,
                            n_clusters=n_clusters,
                            reduced=reduced, t_weight_factor=t_weight_factor,
                            basename=basename, use_temperature=use_temperature)


if __name__ == '__main__':
    plt.close('all')
    plt.ion()
    cases = case.read_cases('melting-test')
    c = cases.case.iloc[1]
    c.class_scheme = scheme
    fig, axarr = c.plot(params=['ZH', 'zdr', 'RHO'], cmap='viridis')

