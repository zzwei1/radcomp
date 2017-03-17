# coding: utf-8
import numpy as np
import pandas as pd
import matplotlib as mpl
#import matplotlib.pyplot as plt
import scipy.io
from os import path
from functools import partial
from radcomp.vertical import (filtering, classification, plotting,
                              NAN_REPLACEMENT)
from radcomp import vertical, HOME, USER_DIR
from j24 import daterange2str

DATA_DIR = path.join(HOME, 'DATA', 'ToJussi')
COL_START = 'start'
COL_END = 'end'


def case_id_fmt(t_start, t_end=None, fmt='{year}{month}{day}', hour_fmt='%H',
                day_fmt='%d', month_fmt='%m', year_fmt='%y'):
    return daterange2str(t_start, t_end, dtformat=fmt, day_fmt=day_fmt,
                         month_fmt=month_fmt, year_fmt=year_fmt).lower()

def read_case_times(name):
    filepath = path.join(USER_DIR, 'cases', name + '.csv')
    dts = pd.read_csv(filepath, parse_dates=[COL_START, COL_END])
    indexing_func = lambda row: case_id_fmt(row[COL_START], row[COL_END])
    dts.index = dts.apply(indexing_func, axis=1)
    dts.index.name = 'id'
    return dts


def read_cases(name):
    dts = read_case_times(name)
    cases_list = [Case.from_dtrange(row[1][COL_START], row[1][COL_END]) for row in dts.iterrows()]
    dts['case'] = cases_list
    return dts


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


def fname_range(dt_start, dt_end):
    dt_range = pd.date_range(dt_start.date(), dt_end.date())
    dt2path_map = partial(dt2path, datadir=DATA_DIR)
    return map(dt2path_map, dt_range)


def kdp2phidp(kdp, dr_km):
    kdp_filled = kdp.fillna(0)
    return 2*kdp_filled.cumsum().multiply(dr_km, axis=0)


def data_range(dt_start, dt_end):
    fnames = fname_range(dt_start, dt_end)
    pns = map(vprhimat2pn, fnames)
    return pd.concat(pns, axis=2).loc[:, :, dt_start:dt_end]


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
    pn_new = filtering.fltr_median(pn_new)
    pn_new = filtering.fltr_ground_clutter_median(pn_new)
    return pn_new


def dt2pn(dt0, dt1):
    pn_raw = data_range(dt0, dt1)
    return prepare_pn(pn_raw)


def fillna(dat, field=''):
    """Fill nan values with values representing zero scatterers."""
    data = dat.copy()
    if isinstance(data, pd.Panel):
        for field in list(data.items):
            data[field].fillna(NAN_REPLACEMENT[field.upper()], inplace=True)
    elif isinstance(data, pd.DataFrame):
        data.fillna(NAN_REPLACEMENT[field.upper()], inplace=True)
    return data


def prepare_data(pn, fields=['ZH', 'ZDR', 'kdp'], hmax=10e3, kdpmax=None):
    """Prepare data for classification. Scaling has do be done separately."""
    data = pn[fields, 0:hmax, :].transpose(0,2,1)
    if kdpmax is not None:
        data['KDP'][data['KDP']>kdpmax] = np.nan
    return fillna(data)


def prep_data(pn, vpc):
    """prepare_data wrapper"""
    return prepare_data(pn, fields=vpc.params, hmax=vpc.hmax, kdpmax=vpc.kdpmax)


def scale_data(pn):
    """Scale radar parameters so that values are same order of magnitude."""
    scaling_limits = {'ZH': (-10, 30), 'ZDR': (0, 3), 'zdr': (0, 3), 'KDP': (0, 0.5), 
                      'kdp': (0, 0.15)}
    scaled = pn.copy()
    for field, data in scaled.iteritems():
        data -= scaling_limits[field][0]
        data *= 1.0/scaling_limits[field][1]
        scaled[field] = data
    return scaled


class Case:
    def __init__(self, data=None, cl_data=None, cl_data_scaled=None,
                 classes=None, class_scheme=None):
        self.data = data
        self.cl_data = cl_data # non-scaled classifiable data
        self.cl_data_scaled = cl_data_scaled # scaled classifiable data
        self.classes = classes
        self.class_scheme = class_scheme
        self._cl_ax = None

    @classmethod
    def from_dtrange(cls, t0, t1):
        pn = dt2pn(t0, t1)
        return cls(data=pn)

    def name(self, **kws):
        return case_id_fmt(self.t_start(), self.t_end(), **kws)

    def t_start(self):
        return self.data.minor_axis[0]

    def t_end(self):
        return self.data.minor_axis[-1]

    def load_classification(self, name):
        self.class_scheme = classification.VPC.load(name)
        self.classify()

    def prepare_cl_data(self, save=True):
        if self.data is not None:
            cl_data = prep_data(self.data, self.class_scheme)
            if save:
                self.cl_data = cl_data
            return cl_data
        return None
        
    def scale_cl_data(self, save=True):
        """scaled version of classification data"""
        if self.cl_data is None:
            self.prepare_cl_data()
        if self.cl_data is not None:
            scaled = scale_data(self.cl_data)
            if save:
                self.cl_data_scaled = scaled
            return scaled
        return None

    def classify(self, scheme=None, save=True):
        """classify based on class_scheme"""
        if scheme is not None:
            self.class_scheme = scheme
        if self.cl_data_scaled is None:
            self.scale_cl_data()
        if self.cl_data_scaled is not None and self.class_scheme is not None:
            classes = classification.classify(self.cl_data_scaled, self.class_scheme.km)
            if save:
                self.classes = classes
            return classes
        return None

    def plot_classes(self):
        return plotting.plot_classes(self.cl_data_scaled, self.classes)

    def plot(self, params=None, interactive=True, **kws):
        if params is None:
            if self.class_scheme is not None:
                params = self.class_scheme.params
            else:
                params = ['ZH', 'zdr', 'kdp']
        fig, axarr = plotting.plotpn(self.data, fields=params, **kws)
        if self.classes is not None:
            for iax in range(len(axarr)-1):
                plotting.class_colors(self.classes, ax=axarr[iax])
        if interactive:
            for ax in axarr:
                # TODO: cursor not showing
                mpl.widgets.Cursor(ax, horizOn=False, color='red', linewidth=2)
            fig.canvas.mpl_connect('button_press_event', self.on_click_plot_cs)
        return fig, axarr

    def train(self):
        return self.class_scheme.train(self.cl_data_scaled)

    def on_click_plot_cs(self, event):
        """on click plot cross section"""
        dt = mpl.dates.num2date(event.xdata).replace(tzinfo=None)
        if self._cl_ax is None:
            axkws = dict()
            update = False
        else:
            cl_ax = self._cl_ax
            if isinstance(cl_ax, np.ndarray):
                for ax in cl_ax:
                    ax.clear()
            else:
                ax = cl_ax
                ax.clear()
            axkws = dict(ax=cl_ax)
            update = True
        self._cl_ax = self.plot_cl_data_at(dt, **axkws)
        if update:
            ax.get_figure().canvas.draw()

    def plot_cl_data_at(self, dt, **kws):
        data = self.cl_data
        displacement = self.mean_delta()
        i = data.major_axis.get_loc(dt-displacement, method='nearest')
        axarr = data.iloc[:, i, :].plot(subplots=True, **kws)
        axarr[0].set_title(str(dt))
        for ax in axarr:
            param=ax.get_lines()[0].get_label().upper()
            ax.set_ylim(plotting.VMINS[param], plotting.VMAXS[param])
            ax.set_ylabel(plotting.LABELS[param])
        ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(vertical.m2km))
        ax.set_xlabel('height, km')
        return axarr

    def mean_delta(self):
        return plotting.mean_delta(self.data.minor_axis)
