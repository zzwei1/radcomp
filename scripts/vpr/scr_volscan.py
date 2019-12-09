# coding: utf-8

from os import path
from glob import glob

import pyart
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

import radcomp.visualization as vis
from radcomp.tools import rhi
from radcomp.vertical import case, classification
from j24 import ensure_dir

#import conf


def plot_vrhi_vs_rhi(vrhi, rhi, field='ZH'):
    fig, axarr = plt.subplots(1, 2, figsize=(12, 5))
    vdisp = pyart.graph.RadarDisplay(vrhi)
    rhidisp = pyart.graph.RadarDisplay(rhi)
    vkw = dict(vmin=vis.VMINS[field], vmax=vis.VMAXS[field])
    mapping = dict(ZH='reflectivity',
                   KDP='specific_differential_phase',
                   ZDR='differential reflectivity')
    if field in mapping:
        field = mapping[field]
    vdisp.plot(field, ax=axarr[0], **vkw)
    rhidisp.plot(field, ax=axarr[1], **vkw)
    for ax in axarr:
        ax.set_ylim(0, 10)
        ax.set_xlim(0, 80)
    return axarr


def hyycase(outdir):
    ds = xr.open_dataset(path.join(outdir, '20140221_IKA_vpvol.nc'))
    hax = np.arange(200, 10050, 50)
    dsi = ds.interp(height=hax)
    c = case.Case.from_xarray(ds=dsi, has_ml=False)
    scheme_snow = 'snow_t075_30eig16clus_pca'
    c.load_classification(scheme_snow)
    return c


def raw2vpvol_nc_batch():
    """Batch process raw volume scans to hyde VPs"""



if __name__ == '__main__':
    hdd = '/media/jussitii/04fafa8f-c3ca-48ee-ae7f-046cf576b1ee'
    filedir = path.join(hdd, 'IKA_final', '20140221')
    outdir = ensure_dir(path.expanduser('~/DATA/vpvol'))
    #rhifile = path.join(hdd, 'IKA_final/20140221/201402212355_IKA.RHI_HV.raw')
    #rrhi = pyart.io.read(rhifile)
    #testdir = path.expanduser(path.join(hdd, 'test_volscan2'))
    #files = glob(path.join(testdir, '*[A-F].raw'))
    #files.sort()
    #vr = rhi.create_volume_scan(files)
    #vrhi = pyart.util.cross_section_ppi(vr, [rhi.AZIM_IKA_HYDE])
    #axarr = plot_vrhi_vs_rhi(vrhi, rrhi, field='KDP')
    #filedir = path.join(hdd, 'test_volscan3')
    #ds1 = rhi.xarray_workflow(filedir, dir_out=None, recalculate_kdp=True)
    #rhi.plot_compare_kdp(vrhi)
    #ds2 = xr.open_dataset(path.join(outdir, '20140221_IKA_vpvol.nc'))
    #plt.figure()
    #ds2.KDP.T.plot(vmax=0.3)
    #c = hyycase(outdir)
    #c.plot()
    fnames = pd.Series(glob(path.join(filedir, '*PPI3_[A-F].raw')))
    tstrs = fnames.apply(lambda s: s[-27:-15])
    g = fnames.groupby(tstrs)
    vrhis = dict()
    for tstr, df in g:
        print(tstr)
        df.sort_values(inplace=True)
        vs = rhi.create_volume_scan(df)
        vrhi = pyart.util.cross_section_ppi(vs, [rhi.AZIM_IKA_HYDE])
        t, vp = rhi.vrhi2vp(vrhi)
        vrhis[t] = vp
    df = pd.concat(vrhis)
    df.index.rename(['time', 'height'], inplace=True)
    ds = df.to_xarray()

