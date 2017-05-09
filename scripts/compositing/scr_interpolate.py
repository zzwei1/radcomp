#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
@author: Jussi Tiira
"""
#import netCDF4 as nc
import os
import matplotlib.pyplot as plt
#import numpy as np
import pandas as pd
import itertools
from glob import glob
from radcomp.qpe import radx, radxpaths, interpolation
from j24 import ensure_dir

plt.ion()
debug = True

basepath = '/media/jussitii/04fafa8f-c3ca-48ee-ae7f-046cf576b1ee'
resultspath = '/home/jussitii/results/radcomp'
if debug:
    gridpath = os.path.join(basepath, 'test', 'cf', 'grids')
else:
    gridpath = os.path.join(basepath, 'grids')
intrp_path = os.path.join(gridpath, 'interpolated')


def discard(filepath, ncdata):
    """Return True if the file was discarded."""
    datadir = os.path.dirname(filepath)
    discardir = os.path.join(datadir, 'discarded')
    ensure_dir(discardir)
    ncdata.close()
    discardfilepath = os.path.join(discardir, os.path.basename(filepath))
    os.rename(filepath, discardfilepath)


def dts(filepaths):
    l_dt = []
    for f0, f1 in itertools.izip(filepaths, filepaths[1:]):
        nc0 = radx.RADXgrid(f0)
        nc1 = radx.RADXgrid(f1)
        t0 = nc0.datetime()[0]
        t1 = nc1.datetime()[0]
        dt = t1-t0
        l_dt.append(dt)
    return l_dt


def filepaths_sep3(fromlist=True):
    if fromlist:
        fpaths_dict = radxpaths.load()
        fpaths_df = pd.concat(fpaths_dict.values())
        fpaths_good = list(fpaths_df.filepath.values)
        fpaths_good.sort()
    else:
        fpaths_all = glob(os.path.join(gridpath, site, '*', 'ncf_20160903_[12]?????.nc'))
        fpaths_all.extend(glob(os.path.join(gridpath, site, '*', 'ncf_20160904_0[0-6]????.nc')))
        fpaths_all.sort()
        fpaths_good = radxpaths.filter_filepaths(fpaths_all)
    return fpaths_good


if debug and False:
    testpath = os.path.join(basepath, 'test')
    testfilepaths = glob(os.path.join(testpath, 'KER', '03', '*.nc'))
    #testfilepaths = glob.glob(os.path.join(testpath, 'KUM', '*.nc'))
    testfilepaths.sort()
    testfilepaths_good = radxpaths.filter_filepaths(testfilepaths)
    testncs=[radx.RADXgrid(f) for f in testfilepaths_good]
    test_interp = False
    if test_interp:
        test_intrp_path = os.path.join(testpath, 'interpolated')
        interpolation.batch_interpolate(testfilepaths_good, test_intrp_path,
                                        save_png=True)
    kumfilepath = os.path.join(testpath, 'ncf_20160904_033827.nc')
    kerfilepath = os.path.join(testpath, 'ncf_20160904_033918.nc')
    kerVOL_Afilepath = os.path.join(testpath, 'KER', '03', 'ncf_20160903_130208.nc')
    kerFMIBfilepath = os.path.join(testpath, 'KER', '03', 'ncf_20160903_130417.nc')
    vanfilepath = os.path.join(testpath, 'ncf_20160904_034033.nc')
    irmafilepath = os.path.join(testpath, 'ncf_20160903_130933.nc')
    irma = radx.RADXgrid(irmafilepath)
    kumnc = radx.RADXgrid(kumfilepath)
    kernc = radx.RADXgrid(kerfilepath)
    vannc = radx.RADXgrid(vanfilepath)
    vol_a = radx.RADXgrid(kerVOL_Afilepath, 'r')
    fmib = radx.RADXgrid(kerFMIBfilepath)
    vol_a.z_min = fmib.z_min
    for task in (vol_a, fmib):
        plt.figure()
        plt.imshow(task.dbz(), vmin=-20, vmax=60)
        plt.title('corrected DBZ for ' + task.task_name)
        plt.colorbar()

for site in radx.SITES:
    filepaths_good = filepaths_sep3()
    interpolation.batch_interpolate(filepaths_good, intrp_path,
                                    data_site=site, save_png=True)


def testcase():
    #filename0 = 'ncf_20160904_033827.nc' # KUM
    #filename1 = 'ncf_20160904_033958.nc' # KUM, dt=91s
    #filename0 = 'ncf_20160904_033918.nc' # KER
    #filename1 = 'ncf_20160904_034208.nc' # KER, dt=170s
    filename0 = 'ncf_20160904_034033.nc' # VAN
    filename1 = 'ncf_20160904_034056.nc' # VAN, dt=23s
    filepath0 = os.path.join(testpath, filename0)
    filepath1 = os.path.join(testpath, filename1)
    nc0 =  radx.RADXgrid(filepath0)
    nc1 =  radx.RADXgrid(filepath1)
    
    #datafilepath = os.path.join(gridpath, 'KUM', '20160903', filename0)
    #ncdata = nc.Dataset(datafilepath, 'r')
    I1 = nc0.rainrate()
    I2 = nc1.rainrate()
    
    interpd = interpolation.interp(I1, I2)
    radx.plot_rainmap(I1)
    for rmap in interpd:
        radx.plot_rainmap(rmap)
    radx.plot_rainmap(I2)
    
    t0 = nc0.datetime()[0]
    t1 = nc1.datetime()[0]
    dt = t1-t0 
    
    #gdata = gio.read_radx_grid(datafilepath)