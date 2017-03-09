# coding: utf-8

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from radcomp import vertical, learn

def mean_delta(t):
    dt = t[-1]-t[0]
    return dt/(len(t)-1)

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
        ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(vertical.m2km))
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

def plot_classes(data, classes):
    figs = []
    axarrs = []
    n_classes = classes.max()+1
    for eigen in range(n_classes):
        i_classes = np.where(classes==eigen)[0]
        if len(i_classes)==0:
            continue
        pn_class = data.iloc[:, i_classes, :]
        fig, axarr = learn.plot_class(pn_class, ylim=(-1, 2))
        axarr[0].legend().set_visible(True)
        figs.append(fig)
        axarrs.append(axarr)
        for ax in axarr:
            if ax.xaxis.get_ticklabels()[0].get_visible():
                ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(vertical.m2km))
    return figs, axarrs