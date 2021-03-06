# coding: utf-8
"""Visualization related tools."""

#import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ticker import MaxNLocator
from matplotlib import colors
import pyart # for colormaps
from mpl_toolkits.mplot3d import Axes3D

import radcomp.visualization as vis
import j24.visualization as jvis
from radcomp import vertical, learn


DATETIME_FMT_CSV = '%Y-%m-%d %H:%M'
DISPLACEMENT_FACTOR = 0.5
LABELS = dict(density='$\\rho$, kg$\,$m$^{-3}$',
              intensity='LWE, mm$\,$h$^{-1}$',
              liq='LWP, cm',
              FR='FR',
              temp_mean='$T_s$, $^{\circ}C$',
              azs='$\\alpha_{ZS}$')
DEFAULT_DISCRETE_CMAP = 'tab20'


#converter = mpl.dates.ConciseDateConverter()
#mpl.units.registry[np.datetime64] = converter
#mpl.units.registry[datetime.date] = converter
#mpl.units.registry[datetime.datetime] = converter


def plot_data(data, ax=None, **kws):
    """plot Series"""
    ax = ax or plt.gca()
    return ax.plot(data.index, data.values, drawstyle='steps', **kws)


def plot_vp(data, ax=None, **kws):
    """plot vertical profile"""
    ax = ax or plt.gca()
    return ax.plot(data.values, data.index, **kws)


def _plot_vp_betweenx(s1, s2, ax=None, **kws):
    """fill_betweenx wrapper for Series objects"""
    ax = ax or plt.gca()
    return ax.fill_betweenx(s1.index, s1.values, s2.values, **kws)


def vp_xlim(name, ax, has_ml):
    """Set x limits in a vertical profile plot."""
    search_name = name.upper()
    if search_name in vis.LABELS:
        ax.set_xlabel(vis.LABELS[search_name])
        vmins, vmaxs = vis.vlims(has_ml=has_ml)
        ax.set_xlim(left=vmins[search_name], right=vmaxs[search_name])
    else:
        ax.set_xlabel(name)


def plot_vps(df, axarr=None, fig_kws={'dpi': 110, 'figsize': (5.5, 3.3)},
             has_ml=False, color2=None, **kws):
    """Plot DataFrame of vertical profile parameters."""
    ncols = df.shape[1]
    if axarr is None:
        fig, axarr = plt.subplots(nrows=1, ncols=ncols, sharey=True, **fig_kws)
    else:
        fig = axarr[0].get_figure()
    for i, (name, data) in enumerate(df.T.sort_index().iterrows()):
        ax = axarr[i]
        if name == 'T':
            locator = MaxNLocator(steps=(1,2,10), nbins=5, prune='lower')
            kws2 = kws.copy()
            if color2 is not None:
                kws2.update(color=color2)
            plot_vp(data, ax=ax, **kws2)
        else:
            locator = MaxNLocator(steps=(1,2,10), nbins=4)
            plot_vp(data, ax=ax, **kws)
        vp_xlim(name, ax, has_ml)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.grid(True)
    set_h_ax(axarr[0], has_ml=has_ml, nbins=10)
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.15, top=0.9, wspace=0.05)
    for ax in axarr[1:]:
        plt.setp(ax.get_yticklabels(), visible=False)
    return axarr


def plot_vps_betweenx(df1, df2, axarr=None, has_ml=False, color2=None,
                      fig_kws={'dpi': 110, 'figsize': (5, 3)}, **kws):
    """Plot areas between vertical profile curves."""
    ncols = df1.shape[1]
    if axarr is None:
        fig, axarr = plt.subplots(nrows=1, ncols=ncols, sharey=True, **fig_kws)
    else:
        fig = axarr[0].get_figure()
    for i, name in enumerate(df1.columns.sort_values()):
        ax = axarr[i]
        if (name == 'T') and (color2 is not None):
            kws2 = kws.copy()
            kws2.update(facecolor=color2)
            _plot_vp_betweenx(df1[name], df2[name], ax=ax, **kws2)
        else:
            _plot_vp_betweenx(df1[name], df2[name], ax=ax, **kws)
        vp_xlim(name, ax, has_ml)
    set_h_ax(axarr[0], has_ml=has_ml, nbins=10)
    fig.subplots_adjust(left=0.13, right=0.95, bottom=0.15, top=0.9, wspace=0.1)
    for ax in axarr[1:]:
        plt.setp(ax.get_yticklabels(), visible=False)
    return axarr


def rotate_tick_labels(rot, ax=None):
    if ax is None:
        ax = plt.gca()
    for tick in ax.get_xticklabels():
        tick.set_rotation(rot)


def mean_delta(t):
    dt = t[-1]-t[0]
    return dt/(len(t)-1)


def set_h_label(ax, has_ml, narrow=False):
    ml_label = 'Height, km\nabove ML top' if narrow else 'Height, km above ML top'
    label = ml_label if has_ml else 'Height, km'
    ax.set_ylabel(label)


def set_h_ax(ax, hlims=(0, 10e3), has_ml=False, label=None, nbins=3, **kws):
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(vertical.m2km))
    steps = [1, 2, 5, 10] # acceptable step multipliers
    locator = MaxNLocator(nbins=nbins, integer=True, steps=steps, **kws)
    ax.yaxis.set_major_locator(locator)
    ax.set_ylim(*hlims)
    if label is None:
        set_h_label(ax, has_ml)


def nice_cb_ticks(cb, nbins=5, steps=(1, 5, 10), **kws):
    # TODO: general for plotting, to be moved
    cb_tick_locator = mpl.ticker.MaxNLocator(nbins=nbins, steps=steps, **kws)
    cb.locator = cb_tick_locator
    cb.update_ticks()


def _pn_fig(fig_scale_factor, n_rows, fig_h_factor=1.1, fig_w_factor=1,
            **fig_kws):
    """Initialize figure for plotpn."""
    fw = fig_scale_factor*fig_w_factor*8
    fh = fig_scale_factor*(3+fig_h_factor*n_rows)
    return plt.figure(figsize=(fw, fh), **fig_kws)


def _pn_gs(fig_scale_factor, n_rows, left_extra=0):
    """Initialize gridspec for plotpn."""
    left = 0.1*(11/(10+fig_scale_factor)) + left_extra
    right = 0.905*(10+fig_scale_factor)/11
    top = 1-0.22/n_rows
    bottom = 0.35/n_rows
    return mpl.gridspec.GridSpec(n_rows, 2, width_ratios=(35, 1), wspace=0.02,
                                 top=top, bottom=bottom,
                                 left=left, right=right)


def _gs_extra(fig_scale_factor, n_rows, right=0.14):
    left = 0.07*(11/(10+fig_scale_factor))
    top = 1-0.22/n_rows
    bottom = 0.35/n_rows
    return mpl.gridspec.GridSpec(n_rows, 1, left=left, right=right,
                                 top=top, bottom=bottom)


def _pn_scalekws(field, scaled, has_ml):
    """plotpn helper function for setting scaling arguments and cb label"""
    fieldup = field.upper()
    if scaled:
        scalekws = {'vmin': 0, 'vmax': 1}
        cb_label = 'scaled {}'.format(field)
    elif fieldup in vis.LABELS:
        vmins, vmaxs = vis.vlims(has_ml=has_ml)
        scalekws = {'vmin': vmins[fieldup],
                    'vmax': vmaxs[fieldup]}
        cb_label = vis.LABELS[fieldup]
    else:
        scalekws = {}
        cb_label = field
    return scalekws, cb_label


def _pn_x(df, x_is_date):
    """plotpn helper fucntion for setting x values"""
    if x_is_date:
        t = df.columns
        x = t - mean_delta(t)*DISPLACEMENT_FACTOR
    else:
        x = df.columns.sort_values()
    dx = mean_delta(x)
    x_last = x[-1:]+dx
    return x.append(x_last)


def field_gamma(field):
    """cmap normalization gamma per radar parameter"""
    try:
        return vis.GAMMA[field.upper()]
    except KeyError:
        return 1


def plotpn(pn, fields=None, scaled=False, cmap='pyart_RefDiff', n_extra_ax=0,
           x_is_date=True, fig_scale_factor=0.65, fig_kws={'dpi': 110},
           n_ax_shift=0, has_ml=False, cmap_override={}, lim_override=False,
           hlims=(0, 10e3), gs_kws={}, **kws):
    """Plot Panel of VPs"""
    if fields is None:
        fields = pn.items
    n_rows = len(fields) + n_extra_ax
    fig = _pn_fig(fig_scale_factor, n_rows, **fig_kws)
    gs = _pn_gs(fig_scale_factor, n_rows, **gs_kws)
    axarr = []
    h = -1
    # coordinate string formatting
    coords = list(fields)
    # always include T in coords if available
    if ('T' in pn) and ('T' not in fields):
        coords += ['T']
    # top axes
    for h in range(n_ax_shift):
        ax = fig.add_subplot(gs[h, 0])
        axarr.append(ax)
    # pcolormesh axes
    i = -1 # in case fields is empty
    for i, field in enumerate(np.sort(fields)):
        cm = cmap if field not in cmap_override else cmap_override[field]
        subplot_kws = {}
        if i > 0:
            subplot_kws['sharex'] = axarr[0]
            subplot_kws['sharey'] = axarr[n_ax_shift]
        ax = fig.add_subplot(gs[h+1+i, 0], **subplot_kws)
        ax_cb = fig.add_subplot(gs[h+1+i, 1])
        axarr.append(ax)
        if lim_override:
            scalekws, cb_label = _pn_scalekws(field, scaled, not has_ml)
        else:
            scalekws, cb_label = _pn_scalekws(field, scaled, has_ml)
        kws.update(scalekws)
        x = _pn_x(pn[field], x_is_date)
        gamma = field_gamma(field)
        im = ax.pcolormesh(x, pn[field].index,
                           np.ma.masked_invalid(pn[field].values), cmap=cm,
                           label=field, norm=colors.PowerNorm(gamma), **kws)
        # coordinate string formatting
        fmt_coord = lambda x, y: format_coord_pn(x, y, pn.loc[coords, :, :],
                                                 x_is_date=x_is_date)
        ax.format_coord = fmt_coord
        #
        use_ml_label = has_ml and not x_is_date
        set_h_ax(ax, has_ml=use_ml_label, hlims=hlims) if i == 1 else set_h_ax(ax, label='', hlims=hlims)
        ax.autoscale(False)
        cb = fig.colorbar(im, cax=ax_cb, label=cb_label)
        nice_cb_ticks(cb)
    # bottom axes
    for j in range(n_extra_ax-n_ax_shift):
        k = h+i+2+j
        ax = fig.add_subplot(gs[k, 0], sharex=axarr[0])
        axarr.append(ax)
    if x_is_date:
        axarr[-1].set_xlabel('Time, UTC')
        formatter = concise_formatter()
        axarr[-1].xaxis.set_major_formatter(formatter)
        axarr[0].set_title(str(pn[field].columns[0].date()))
    # Hide xticks for all but last.
    for ax in axarr[:-1]:
        plt.setp(ax.get_xticklabels(), visible=False)
    return fig, axarr


def concise_formatter():
    """formatting nice looking date ticks"""
    auto = mpl.dates.AutoDateLocator()
    formats = ['%Y', '%b', '%d', '%H', '%H:%M', '%S.%f']
    zero_formats = ['', '%Y', '%b', '%b-%d', '%H:%M', '%H:%M']
    return mpl.dates.ConciseDateFormatter(auto, formats=formats,
                                          zero_formats=zero_formats,
                                          show_offset=False)


def class_color(cid, cmap=DEFAULT_DISCRETE_CMAP, **kws):
    """j24.visualization.class_color wrapper"""
    return jvis.class_color(cid, cmap=cmap, **kws)


def class_colors(classes, cmap=DEFAULT_DISCRETE_CMAP, **kws):
    """j24.visualization.class_colors wrapper"""
    return jvis.class_colors(classes, cmap=cmap, **kws)


def plot_classes(data, classes):
    figs = []
    axarrs = []
    n_classes = classes.max()+1
    for eigen in range(n_classes):
        i_classes = np.where(classes == eigen)[0]
        if len(i_classes) == 0:
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


def pcolor_class(g, **kws):
    gt = g.transpose(0, 2, 1)
    gt.minor_axis = list(range(gt.shape[2]))
    fig, axarr = plotpn(gt, x_is_date=False, **kws)
    return axarr


def hists_by_class(data, classes, cmap=DEFAULT_DISCRETE_CMAP, **kws):
    """histograms of data grouping by class"""
    cm = plt.get_cmap(cmap)
    xmin = dict(density=0, intensity=0, liq=0, temp_mean=-15, FR=0)
    xmax = dict(density=500, intensity=4, liq=0.08, temp_mean=5, FR=1)
    incr = dict(density=50, intensity=0.25, liq=0.01, temp_mean=2, FR=0.1)
    param = data.name
    axarr = data.hist(by=classes, sharex=True, sharey=True, normed=True,
                      bins=np.arange(xmin[param], xmax[param], incr[param]))
    axflat = axarr.flatten()
    axflat[0].set_xlim(xmin[param], xmax[param])
    fig = axflat[0].get_figure()
    frameax = fig.add_subplot(111, frameon=False)
    frameax.tick_params(labelcolor='none', top='off', bottom='off', left='off',
                        right='off')
    frameax.set_xlabel(LABELS[param])
    frameax.set_ylabel('probability density')
    for ax in axflat:
        rotate_tick_labels(0, ax=ax)
        try:
            iclass = int(float(ax.get_title()))
        except ValueError:
            continue
        titletext = '{}'.format(iclass)
        ax.set_title('')
        ax.text(0.88, 0.82, titletext, horizontalalignment='center',
                verticalalignment='center', transform=ax.transAxes)
        for p in ax.patches:
            p.set_color(class_color(iclass, cm, **kws))
    return fig


def scatter_class_pca(profiles_pca, classes, color_fun=class_color, plot3d=True):
    """scatterplot of profiles in pca space highlighting classes"""
    profs_pca = profiles_pca.copy()
    profs_pca['class'] = classes
    cg = profs_pca.groupby('class')
    markers = ['d', 'o', 'v', '^', 's', 'p', '>', '*', 'x', 'D', 'h', '<']
    fig = plt.figure()
    kws3d = {}
    if plot3d:
        kws3d['projection'] = '3d'
    ax = fig.add_subplot(111, **kws3d)
    for cl, eig in cg:
        marker_kws = dict(color=color_fun(cl), marker=markers[(cl-1) % len(markers)])
        if plot3d:
            ax.scatter(eig[0], eig[1], eig[2], **marker_kws)
            ax.set_zlabel('component 3')
        else:
            eig.plot.scatter(0, 1, ax=ax, **marker_kws)
        ax.set_xlabel('component 1')
        ax.set_ylabel('component 2')
    return ax


def cm_blue():
    """colormap of only blue color"""
    blue = (0.29803921568627451, 0.44705882352941179, 0.69019607843137254, 1.0)
    return mpl.colors.ListedColormap([blue]*50)


def bar_plot_colors(ax, classes, class_color_fun=class_color, **cmkw):
    pa = ax.patches
    check_rect = lambda p: isinstance(p, mpl.patches.Rectangle)
    pa = np.array(pa)[list(map(check_rect, pa))]
    for i, p in enumerate(pa):
        color = class_color_fun(classes[i], default=(1, 1, 1, 0), **cmkw)
        p.set_color(color)


def plot_growth_zones(x, ax=None, levels=('ml'), **kws):
    """Plot interpolated sounding data on growth zone edges."""
    ax = ax or plt.gca()
    contours = []
    args = (x.columns, x.index, x)
    kws['linewidths'] = 0.6
    kws['linestyles'] = 'solid'
    try:
        np.array(levels).astype(float) # check if numeric
        con = ax.contour(*args, levels=levels, colors='black', **kws)
        contours.append(con)
    except ValueError:
        if 'hm' in levels:
            con = ax.contour(*args, levels=[-8, -3], colors='red', **kws)
            contours.append(con)
        if 'dend' in levels:
            con = ax.contour(*args, levels=[-20, -10], colors='dimgray', **kws)
            contours.append(con)
        if 'ml' in levels:
            con = ax.contour(*args, levels=[0], colors='orange', **kws)
            contours.append(con)
    for con in contours:
        plt.clabel(con, fontsize=6, fmt='%1.0f')
    return ax


def dict2coord(d):
    """dictionary as 'key1=value1, key2=value2, ...' string"""
    return ', '.join('{0}={1:.2f}'.format(*x) for x in d.items())


def num2date(num):
    """num2date wrapper"""
    return mpl.dates.num2date(num).replace(tzinfo=None)


def num2tstr(num):
    """datenumber to datetime string representation"""
    try:
        t = num2date(num)
    except TypeError:
        # already a datetime?
        t = num
    return t.strftime(DATETIME_FMT_CSV)


def format_coord(x, y):
    """coordinate formatter replacement"""
    return 'x={x}, y={y:.2f}'.format(x=x, y=y)


def format_coord_xtime(x, y):
    """coordinate formatter replacement when x is time"""
    return 'x={x}, y={y:.0f}'.format(x=num2tstr(x), y=y)


def format_coord_pn(x, y, data, x_is_date=False):
    """coordinate formatter replacement with data display"""
    values = {}
    for label in data.items:
        if x_is_date:
            try:
                x = num2date(x)
            except TypeError:
                # let's hope it's already a datetime
                pass
        else:
            x = round(x)
        ix = data.minor_axis.get_loc(x, method='nearest')
        iy = data.major_axis.get_loc(y, method='nearest')
        values[label] = data[label].iloc[iy, ix]
    if x_is_date:
        xystr = format_coord_xtime(x, y)
    else:
        xystr = format_coord(x, y)
    return ', '.join([xystr, dict2coord(values)])


def plot_bm_stats(stat, ax=None, **kws):
    """Plot benchmark stats."""
    ax = ax or plt.gca()
    stat.plot.bar(stacked=True, ax=ax, **kws)
    ax.grid(axis='y')
    ax.set_ylabel('number of profiles')
    ax.set_xlabel('class')
    ax.set_title('unsupervised classification vs. reference analysis')
    return ax


def boxplot_t_echotop(c, ax=None, **kws):
    """boxplot of echo top temperature by class"""
    ax = ax or plt.gca()
    data = pd.concat([c.t_echotop(), c.vpc.classes], axis=1)
    data.boxplot(by='class', ax=ax, **kws)
    ax.get_figure().suptitle('')
    ax.set_title('')
    ax.invert_yaxis()
    ax.set_xlabel('class')
    ax.set_ylabel('echo top temperature')
    return ax


def boxplot_t_surf(c, ax=None, whis=4, **kws):
    """Plot surface temperature distribution by class."""
    t_cl = pd.concat([c.t_surface(), c.vpc.classes], axis=1)
    meanprops = dict(linestyle='-', color='darkred')
    medianprops = dict()
    boxprops = dict()
    if ax is None:
        fig, ax = plt.subplots(dpi=110, figsize=(5,3.5))
    else:
        fig = ax.get_figure()
    tup = t_cl.boxplot(by='class', whis=whis, return_type='both', showmeans=True,
                       meanline=True, meanprops=meanprops, patch_artist=True,
                       medianprops=medianprops, boxprops=boxprops, ax=ax, **kws)
    ax, lines = tup.temp_mean
    for med in lines['medians']:
        med.set_color('yellow')
    for box in lines['boxes']:
        box.set_alpha(0.5)
    #t_cl.boxplot(by='class', showcaps=False, showbox=False, showfliers=False, ax=ax)
    ax.set_title('Surface temperature distribution by class')
    ax.set_xlabel('class')
    ax.set_ylabel('$T_s$')
    fig = ax.get_figure()
    fig.suptitle('')
    return fig, ax, lines


def boxplot_t_combined(c, i_dis=tuple(), ax=None):
    """boxplot of surface and echo top temperature distributions by class"""
    if ax is None:
        fig, ax = plt.subplots(dpi=110)
    else:
        fig = ax.get_figure()
    t_top = pd.concat([c.t_echotop(), c.vpc.classes], axis=1)
    if c.has_ml:
        pos_minus = None
    else:
        displacement = 0.1
        pos_minus = np.arange(1, c.vpc.n_clusters+1).astype(float)
        pos_plus = pos_minus.copy()
        pos_minus[i_dis] -= displacement
        pos_plus[i_dis] += displacement
    color = 'gray'
    whiskerprops = dict()
    capprops = dict(color='k')
    bp_top = t_top.boxplot(by='class', ax=ax, whis=[2.5, 97.5],
                          showfliers=False, patch_artist=True,
                          positions=pos_minus, whiskerprops=whiskerprops,
                          capprops=capprops, return_type='dict')['t_top']
    for box in bp_top['boxes']:
        box.set_alpha(0.5)
        box.set_facecolor(color)
        box.set_edgecolor(color)
    for whis in bp_top['whiskers']:
        whis.set_color(color)
    for med in bp_top['medians']:
        med.set_color('green')
    if not c.has_ml:
        _, _, bp_bot = boxplot_t_surf(c, ax=ax, positions=pos_plus)
        ax.legend((box, bp_bot['boxes'][0]), ('echo top', 'surface'))
    ax.set_xticks(np.arange(c.vpc.n_clusters)+1)
    ax.invert_yaxis()
    ax.set_title('')
    ax.set_ylabel(vis.LABELS['T'])
    ax.set_xlabel('profile class')
    fig.suptitle('')
    prepend_class_xticks(ax, c.has_ml)
    return fig, ax, bp_top


def plot_occurrence_counts(count, ax=None, bottom=0, top=900):
    """Bar plot class counts and percentage.

    Args:
        count (Series)
    """
    ax = ax or plt.gca()
    #count.plot.bar(ax=ax) # bug in pd or mpl
    ax.bar(count.index, count.values, width=0.5) # workaround
    ax.set_xticks(count.index) # workaround
    ax.set_ylabel('Profile count')
    ax.yaxis.grid(True)
    ax.set_ylim(bottom=bottom, top=top)
    ax2 = ax.twinx()
    ax2.set_ylim(ax.get_ylim())
    ticks2 = np.array([0, 0.05, 0.1, 0.15])
    locs2 = ticks2*count.sum()
    ax2.set_yticks(locs2)
    ax2.set_yticklabels((ticks2*100).astype(int))
    ax2.set_ylabel('%')


def handle_ax(ax):
    """Prepare axes for redrawing."""
    if ax is None:
        ax_out = None
        axkws = dict()
        update = False
    else:
        cl_ax = ax
        # clear axes
        if isinstance(cl_ax, np.ndarray):
            for ax_out in cl_ax:
                ax_out.clear()
        else:
            ax_out = cl_ax
            ax_out.clear()
        axkws = dict(axarr=cl_ax)
        update = True
    return ax_out, update, axkws


def prepend_class_xticks(ax, has_ml):
    """Prepend class names with chars."""
    seasonchar = 'R' if has_ml else 'S'
    try:
        xticklabels = [str(int(float(t.get_text()))) for t in ax.get_xticklabels()]
    except ValueError:
        xticklabels = ax.get_xticks().astype(str)
    ax.set_xticklabels(np.array([seasonchar + l for l in xticklabels]))


def lineboxplot(dat, rain_season, color='blue', cen=None):
    """Plot individual profile lines, quantiles and optionally centroid."""
    axarr = plot_vps(dat.iloc[:,:,0], linewidth=0.5, alpha=0)
    kws = dict(has_ml=rain_season, axarr=axarr)
    for dt in dat.minor_axis:
        plot_vps(dat.loc[:,:,dt], linewidth=0.5, alpha=0.05,
                          color=color, color2='dimgrey', **kws)
    q1 = dat.apply(lambda df: df.quantile(q=0.25), axis=2)
    q3 = dat.apply(lambda df: df.quantile(q=0.75), axis=2)
    med = dat.median(axis=2)
    plot_vps(med, color='yellow', label='median', **kws)
    if cen is not None:
        cenn = cen.reindex_like(med) # add missing columns
        plot_vps(cenn, color='darkred', label='centroid', **kws)
    plot_vps_betweenx(q1, q3, alpha=0.5, label='50%', color2='dimgrey', **kws)
    axarr[-1].legend()
    return axarr


def cl_colorbar(vpc, ax, title='', label='', **kws):
    """VPC colorbar with colors of each class"""
    vals = vpc.precip_classes()
    labels = np.array(vpc.class_labels())[vals]
    colors = [vpc.class_color(cl) for cl in vpc.precip_classes()]
    cmap = mpl.colors.ListedColormap(colors)
    bounds = np.array(list(vals)+[vals[-1]+1]) - 0.5
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, boundaries=bounds,
                                   ticks=vals, ticklocation='left', **kws)
    cb.set_ticklabels(labels)
    if label:
        cb.set_label(label)
    if title:
        fontdict = dict(size=10)
        ax.set_title(title, loc='right', fontdict=fontdict)
    return cb
