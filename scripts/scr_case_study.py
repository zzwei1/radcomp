#!/usr/bin/env python2
# coding: utf-8
"""
@author: Jussi Tiira
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
from os import path
from radcomp.vertical import case, RESULTS_DIR
from radcomp import CACHE_DIR
from j24 import ensure_dir
from baecc import prepare

plt.ion()
plt.close('all')
np.random.seed(0)
results_dir = ensure_dir(path.join(RESULTS_DIR, 'case_study'))
TABLE_PKL = path.join(CACHE_DIR, 'ground_table.pkl')
EVENTS_PKL = path.join(CACHE_DIR, 'ground_events.pkl')

def store_ground_data(casesname_baecc='tiira2017_baecc', 
                      casesname_1415='tiira2017_1415', **kws):
    e = prepare.events(casesname_baecc=casesname_baecc, 
                       casesname_1415=casesname_1415)
    table = prep_table(e, **kws)
    table.to_pickle(TABLE_PKL)
    with open(EVENTS_PKL, 'wb') as f:
        pickle.dump(e, f)
    return table

def load_events():
    with open(EVENTS_PKL, 'rb') as f:
        return pickle.load(f)

def prep_events(e, cases):
    e.events.index = cases.index
    return e

def prep_table(e, cases=None, **kws):
    table = prepare.param_table(e=e, **kws)
    table.index = table.index.droplevel()
    if cases is not None:
        table.index.set_levels(cases.index, level=0, inplace=True)
    return table

def plot_data(data, ax, **kws):
    return ax.plot(data.index, data.values, drawstyle='steps', **kws)

def fltr_long_period(data_in, minutes=30):
    data = data_in.copy()
    selection = data.tdelta>pd.tseries.offsets.Minute(minutes).delta
    data.loc[selection,['density','D_max','D_0_gamma', 'N_w']] = np.nan
    return data

def plot_case(name, cases, g, n_comp=20):
    scheme = '2014rhi_{n}comp'.format(n=n_comp)
    data_g = g.loc[name]
    c = cases.case[name]
    c.load_classification(scheme)
    fig, axarr = c.plot(cmap='viridis', n_extra_ax=3)
    ax_r = axarr[-3]
    ax_rho = axarr[-2]
    ax_d = axarr[-1]
    plot_data(data_g['intensity'], ax_r)
    ax_r.set_ylabel('LWE, mm$\,$h$^{-1}$')
    plot_data(data_g['density'], ax_rho)
    ax_rho.set_ylabel('Density, kg$\,$m$^{-3}$')
    plot_data(data_g['D_max'], ax_d, label='$D_{max}$')
    plot_data(data_g['D_0_gamma'], ax_d, label='$D_0$')
    ax_d.set_ylabel('mm')
    ax_d.legend()
    #figs, axarrs = vpc.plot_classes(data_scaled, classes, pca.n_components)

cases = case.read_cases('analysis')
g = pd.read_pickle(TABLE_PKL)
for name in cases.index.values:
    plot_case(name, cases, g)
