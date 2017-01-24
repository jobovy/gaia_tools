###############################################################################
# tgasSelect.py: Selection function for (part of) the TGAS data set
###############################################################################
###############################################################################
#
# This file contains routines to compute the selection function of subsets
# of the Gaia DR1 TGAS data. As usual, care should be taken when using this
# set of tools for a subset for which the selection function has not been 
# previously tested.
#
# The basic, underlying, complete set of 2MASS counts was generated by the 
# following SQL query (applied using Python tools):
#
"""
select floor((j_m+(j_m-k_m)*(j_m-k_m)+2.5*(j_m-k_m))*10), \
floor((j_m-k_m+0.05)/1.05*3), floor(hp12index/16384), count(*) as count \
from twomass_psc, twomass_psc_hp12 \
where (twomass_psc.pts_key = twomass_psc_hp12.pts_key \
AND (ph_qual like 'A__' OR (rd_flg like '1__' OR rd_flg like '3__')) \
AND (ph_qual like '__A' OR (rd_flg like '__1' OR rd_flg like '__3')) \
AND use_src='1' AND ext_key is null \
AND (j_m-k_m) > -0.05 AND (j_m-k_m) < 1.0 AND j_m < 13.5 AND j_m > 2) \
group by floor((j_m+(j_m-k_m)*(j_m-k_m)+2.5*(j_m-k_m))*10), \
floor((j_m-k_m+0.05)/1.05*3),floor(hp12index/16384) \
order by floor((j_m+(j_m-k_m)*(j_m-k_m)+2.5*(j_m-k_m))*10) ASC;
"""
#
# and saved in 2massc_jk_jt_hp5_forsf.txt. The basic set of counts with 
# 6 < J < 10, 0.0 < J-Ks < 0.8 in HEALPix pixels was generated by the following
# SQL query
#
"""
select floor(hp12index/16384), count(*) as count \
from twomass_psc, twomass_psc_hp12 \
where (twomass_psc.pts_key = twomass_psc_hp12.pts_key \
AND (ph_qual like 'A__' OR (rd_flg like '1__' OR rd_flg like '3__')) \
AND (ph_qual like '__A' OR (rd_flg like '__1' OR rd_flg like '__3')) \
AND use_src='1' AND ext_key is null \
AND (j_m-k_m) > 0.0 AND (j_m-k_m) < 0.8 AND j_m > 6 AND j_m < 10) \
group by floor(hp12index/16384) \
order by floor(hp12index/16384) ASC;
"""
#
# and saved in 2massc_hp5.txt
###############################################################################
import os, os.path
import hashlib
import tqdm
import numpy
from scipy import interpolate
import astropy.coordinates as apco
import healpy
from galpy.util import bovy_plot, bovy_coords, multi
from matplotlib import cm
import gaia_tools.load
try:
    import mwdust
except ImportError:
    _MWDUSTLOADED= False
else:
    _MWDUSTLOADED= True
_BASE_NSIDE= 2**5
_BASE_NPIX= healpy.nside2npix(_BASE_NSIDE)
_SFFILES_DIR= os.path.dirname(os.path.realpath(__file__))
######################### Read file with counts in hp6 ########################
_2mc_skyonly= numpy.loadtxt(os.path.join(_SFFILES_DIR,'2massc_hp5.txt')).T
# Make sure all HEALPix pixels are available
ta= numpy.zeros((2,_BASE_NPIX))
ta[0][_2mc_skyonly[0].astype('int')]= _2mc_skyonly[0]
ta[1][_2mc_skyonly[0].astype('int')]= _2mc_skyonly[1]
_2mc_skyonly= ta
#################### Read file with counts in jt, j-k, hp5 ####################
_2mc= numpy.loadtxt(os.path.join(_SFFILES_DIR,'2massc_jk_jt_hp5_forsf.txt')).T
# Make value center of bin and re-normalize
_2mc[0]+= 0.5
_2mc[1]+= 0.5
_2mc[0]/= 10.
_2mc[1]= _2mc[1]*1.05/3.-0.05
class tgasSelect(object):
    def __init__(self,
                 min_nobs=8.5,
                 max_nobs_std=10.,
                 max_plxerr=1.01, # Effectively turns this off
                 max_scd=0.7,
                 min_lat=20.,
                 jmin=2.,jmax=13.5,jkmin=-0.05,jkmax=1.0):
        """
        NAME:
           __init__
        PURPOSE:
           Initialize the TGAS selection function
        INPUT:
           Parameters for determining the 'good' part of the sky (applied at the 2^5 nside pixel level):
              min_nobs= (8.5) minimum mean number of observations
              max_nobs_std= (10) maximum spread in the number of observations
              max_plerr= (1.01) maximum mean parallax uncertainty (default: off)
              max_scd= (0.7) maximum mean scan_direction_strength_k4
              min_lat= (20.) minimum |ecliptic latitude| in degree
           Parameters determining the edges of the color-magnitude considered (don't touch these unless you know what you are doing):
              jmin= (2.) Minimum J-band magnitude to consider
              jmax= (13.5) Maximum J-band magnitude to consider
              jkmin (-0.05) Minimum J-K_s color to consider
              jkmax= (1.0) Maximum J-K_s color to consider
        OUTPUT:
           TGAS-selection-function object
        HISTORY:
           2017-01-17 - Started - Bovy (UofT/CCA)
        """
        # Load the data
        self._full_tgas= gaia_tools.load.tgas()
        self._full_twomass= gaia_tools.load.twomass(dr='tgas')
        self._full_jk= self._full_twomass['j_mag']-self._full_twomass['k_mag']
        self._full_jt= jt(self._full_jk,self._full_twomass['j_mag'])
        # Some overall statistics to aid in determining the good sky, setup 
        # related to statistics of 6 < J < 10
        self._setup_skyonly(min_nobs,max_nobs_std,max_plxerr,max_scd,min_lat)
        self._determine_selection(jmin,jmax,jkmin,jkmax)
        return None

    def _setup_skyonly(self,min_nobs,max_nobs_std,max_plxerr,max_scd,min_lat):
        self._tgas_sid= (self._full_tgas['source_id']/2**(35.\
                               +2*(12.-numpy.log2(_BASE_NSIDE)))).astype('int')
        self._tgas_sid_skyonlyindx= (self._full_jk > 0.)\
            *(self._full_jk < 0.8)\
            *(self._full_twomass['j_mag'] > 6.)\
            *(self._full_twomass['j_mag'] < 10.)
        nstar, e= numpy.histogram(self._tgas_sid[self._tgas_sid_skyonlyindx],
                                  range=[-0.5,_BASE_NPIX-0.5],bins=_BASE_NPIX)
        self._nstar_tgas_skyonly= nstar
        self._nobs_tgas_skyonly= self._compute_mean_quantity_tgas(\
            'astrometric_n_good_obs_al',lambda x: x/9.)
        self._nobsstd_tgas_skyonly= numpy.sqrt(\
            self._compute_mean_quantity_tgas(\
                'astrometric_n_good_obs_al',lambda x: (x/9.)**2.)
            -self._nobs_tgas_skyonly**2.)
        self._scank4_tgas_skyonly= self._compute_mean_quantity_tgas(\
            'scan_direction_strength_k4')
        self._plxerr_tgas_skyonly= self._compute_mean_quantity_tgas(\
            'parallax_error')
        tmp_decs, ras= healpy.pix2ang(_BASE_NSIDE,numpy.arange(_BASE_NPIX),
                                      nest=True)
        coos= apco.SkyCoord(ras,numpy.pi/2.-tmp_decs,unit="rad")
        coos= coos.transform_to(apco.GeocentricTrueEcliptic)
        self._eclat_skyonly= coos.lat.to('deg').value
        self._exclude_mask_skyonly= \
            (self._nobs_tgas_skyonly < min_nobs)\
            +(self._nobsstd_tgas_skyonly > max_nobs_std)\
            +(numpy.fabs(self._eclat_skyonly) < min_lat)\
            +(self._plxerr_tgas_skyonly > max_plxerr)\
            +(self._scank4_tgas_skyonly > max_scd)
        return None

    def _determine_selection(self,jmin,jmax,jkmin,jkmax):
        """Determine the Jt dependence of the selection function in the 'good'
        part of the sky"""
        self._jmin= jmin
        self._jmax= jmax
        self._jkmin= jkmin
        self._jkmax= jkmax
        jtbins= (numpy.amax(_2mc[0])-numpy.amin(_2mc[0]))/0.1+1
        nstar2mass, edges= numpy.histogramdd(\
            _2mc[:3].T,bins=[jtbins,3,_BASE_NPIX],
            range=[[numpy.amin(_2mc[0])-0.05,numpy.amax(_2mc[0])+0.05],
                   [jkmin,jkmax],[-0.5,_BASE_NPIX-0.5]],weights=_2mc[3])
        findx= (self._full_jk > jkmin)*(self._full_jk < jkmax)\
            *(self._full_twomass['j_mag'] < jmax)
        nstartgas, edges= numpy.histogramdd(\
            numpy.array([self._full_jt[findx],self._full_jk[findx],\
                             (self._full_tgas['source_id'][findx]\
                                  /2**(35.+2*(12.-numpy.log2(_BASE_NSIDE))))\
                             .astype('int')]).T,
            bins=[jtbins,3,_BASE_NPIX],
            range=[[numpy.amin(_2mc[0])-0.05,numpy.amax(_2mc[0])+0.05],
                   [jkmin,jkmax],[-0.5,_BASE_NPIX-0.5]])
        # Only 'good' part of the sky
        nstar2mass[:,:,self._exclude_mask_skyonly]= numpy.nan
        nstartgas[:,:,self._exclude_mask_skyonly]= numpy.nan
        nstar2mass= numpy.nansum(nstar2mass,axis=-1)
        nstartgas= numpy.nansum(nstartgas,axis=-1)
        exs= 0.5*(numpy.roll(edges[0],1)+edges[0])[1:]
        # Three bins separate
        sf_splines= []
        sf_props= numpy.zeros((3,3))
        for ii in range(3):
            # Determine the plateau, out of interest
            level_indx= (exs > 8.5)*(exs < 9.5)
            sf_props[ii,0]=\
                numpy.nanmedian((nstartgas/nstar2mass)[level_indx,ii])
            # Spline interpolate
            spl_indx= (exs > 4.25)*(exs < 13.5)\
                *(True-numpy.isnan((nstartgas/nstar2mass)[:,ii]))
            tsf_spline= interpolate.UnivariateSpline(\
                exs[spl_indx],(nstartgas/nstar2mass)[spl_indx,ii],
                w=1./((numpy.sqrt(nstartgas)/nstar2mass)[spl_indx,ii]+0.02),
                k=3,ext=1,s=numpy.sum(spl_indx)/4.)
            # Determine where the sf hits 50% completeness 
            # at the bright and faint end
            bindx= spl_indx*(exs < 9.)
            xs= numpy.linspace(numpy.amin(exs[bindx]),numpy.amax(exs[bindx]),
                               1001)
            sf_props[ii,1]=\
                interpolate.InterpolatedUnivariateSpline(tsf_spline(xs),
                                                         xs,k=1)(0.5)
            # Faint
            findx= spl_indx*(exs > 9.)\
                *((nstartgas/nstar2mass)[:,ii]*sf_props[ii,0] < 0.8)
            xs= numpy.linspace(numpy.amin(exs[findx]),numpy.amax(exs[findx]),
                               1001)
            sf_props[ii,2]=\
                interpolate.InterpolatedUnivariateSpline(tsf_spline(xs)[::-1],
                                                         xs[::-1],k=1)(0.5)
            sf_splines.append(tsf_spline)
        self._sf_splines= sf_splines
        self._sf_props= sf_props
        return None

    def __call__(self,j,jk,ra,dec):
        """
        NAME:
           __call__
        PURPOSE:
           Evaluate the selection function for multiple (J,J-Ks) 
           and single (RA,Dec)
        INPUT:
           j - apparent J magnitude
           jk - J-Ks color
           ra, dec - sky coordinates (deg)
        OUTPUT
           selection fraction
        HISTORY:
           2017-01-18 - Written - Bovy (UofT/CCA)
        """
        # Parse j, jk
        if isinstance(j,float):
            j= numpy.array([j])
        if isinstance(jk,float):
            jk= numpy.array([jk])
        # Parse RA, Dec
        theta= numpy.pi/180.*(90.-dec)
        phi= numpy.pi/180.*ra
        pix= healpy.ang2pix(_BASE_NSIDE,theta,phi,nest=True)
        if self._exclude_mask_skyonly[pix]:
            return numpy.zeros_like(j)
        jkbin= numpy.floor((jk-self._jkmin)\
                               /(self._jkmax-self._jkmin)*3.).astype('int')
        tjt= jt(jk,j)
        out= numpy.zeros_like(j)
        for ii in range(3):
            out[jkbin == ii]= self._sf_splines[ii](tjt[jkbin == ii])
        out[out < 0.]= 0.
        out[(j < self._jmin)+(j > self._jmax)]= 0.
        return out

    def determine_statistical(self,data,j,k):
        """
        NAME:
           determine_statistical
        PURPOSE:
           Determine the subsample that is part of the statistical sample
           described by this selection function object
        INPUT:
           data - a TGAS subsample (e.g., F stars)
           j - J magnitudes for data
           k - K_s magnitudes for data
        OUTPUT:
           index array into data that has True for members of the 
           statistical sample
        HISTORY:
           2017-01-18 - Written - Bovy (UofT/CCA)
        """
        # Sky cut
        data_sid= (data['source_id']\
                       /2**(35.+2*(12.-numpy.log2(_BASE_NSIDE)))).astype('int')
        skyindx= True-self._exclude_mask_skyonly[data_sid]
        # Color, magnitude cuts
        cmagindx= (j >= self._jmin)*(j <= self._jmax)\
            *(j-k >= self._jkmin)*(j-k <= self._jkmax)
        return skyindx*cmagindx

    def plot_mean_quantity_tgas(self,tag,func=None,**kwargs):
        """
        NAME:
           plot_mean_quantity_tgas
        PURPOSE:
           Plot the mean of a quantity in the TGAS catalog on the sky
        INPUT:
           tag - tag in the TGAS data to plot
           func= if set, a function to apply to the quantity
           +healpy.mollview plotting kwargs
        OUTPUT:
           plot to output device
        HISTORY:
           2017-01-17 - Written - Bovy (UofT/CCA)
        """
        mq= self._compute_mean_quantity_tgas(tag,func=func)
        cmap= cm.viridis
        cmap.set_under('w')
        kwargs['unit']= kwargs.get('unit',tag)
        kwargs['title']= kwargs.get('title',"")
        healpy.mollview(mq,nest=True,cmap=cmap,**kwargs)
        return None

    def _compute_mean_quantity_tgas(self,tag,func=None):
        """Function that computes the mean of a quantity in the TGAS catalog
        as a function of position on the sky, based on the sample with
        6 < J < 10 and 0 < J-Ks < 0.8"""
        if func is None: func= lambda x: x
        mq, e= numpy.histogram(self._tgas_sid[self._tgas_sid_skyonlyindx],
                               range=[-0.5,_BASE_NPIX-0.5],bins=_BASE_NPIX,
                               weights=func(self._full_tgas[tag]\
                                                [self._tgas_sid_skyonlyindx]))
        mq/= self._nstar_tgas_skyonly
        return mq
        
    def plot_2mass(self,jmin=None,jmax=None,
                   jkmin=None,jkmax=None,
                   cut=False,
                   **kwargs):
        """
        NAME:
           plot_2mass
        PURPOSE:
           Plot star counts in 2MASS
        INPUT:
           If the following are not set, fullsky will be plotted:
              jmin, jmax= minimum and maximum Jt
              jkmin, jkmax= minimum and maximum J-Ks
           cut= (False) if True, cut to the 'good' sky
           +healpy.mollview plotting kwargs
        OUTPUT:
           plot to output device
        HISTORY:
           2017-01-17 - Written - Bovy (UofT/CCA)
        """
        # Select stars
        if jmin is None or jmax is None \
                or jkmin is None or jkmax is None:
            pt= _2mc_skyonly[1]
        else:
            pindx= (_2mc[0] > jmin)*(_2mc[0] < jmax)\
                *(_2mc[1] > jkmin)*(_2mc[1] < jkmax)
            pt, e= numpy.histogram(_2mc[2][pindx],
                                   range=[-0.5,_BASE_NPIX-0.5],
                                   bins=_BASE_NPIX)
        pt= numpy.log10(pt)
        if cut: pt[self._exclude_mask_skyonly]= healpy.UNSEEN
        cmap= cm.viridis
        cmap.set_under('w')
        kwargs['unit']= r'$\log_{10}\mathrm{number\ counts}$'
        kwargs['title']= kwargs.get('title',"")
        healpy.mollview(pt,nest=True,cmap=cmap,**kwargs)
        return None

    def plot_tgas(self,jmin=None,jmax=None,
                  jkmin=None,jkmax=None,
                  cut=False,
                  **kwargs):
        """
        NAME:
           plot_tgas
        PURPOSE:
           Plot star counts in TGAS
        INPUT:
           If the following are not set, fullsky will be plotted:
              jmin, jmax= minimum and maximum Jt
              jkmin, jkmax= minimum and maximum J-Ks
           cut= (False) if True, cut to the 'good' sky
           +healpy.mollview plotting kwargs
        OUTPUT:
           plot to output device
        HISTORY:
           2017-01-17 - Written - Bovy (UofT/CCA)
        """
        # Select stars
        if jmin is None or jmax is None \
                or jkmin is None or jkmax is None:
            pt= self._nstar_tgas_skyonly
        else:
            pindx= (self._full_jt > jmin)*(self._full_jt < jmax)\
                *(self._full_jk > jkmin)*(self._full_jk < jkmax)
            pt, e= numpy.histogram((self._full_tgas['source_id']/2**(35.\
                      +2*(12.-numpy.log2(_BASE_NSIDE)))).astype('int')[pindx],
                                   range=[-0.5,_BASE_NPIX-0.5],
                                   bins=_BASE_NPIX)
        pt= numpy.log10(pt)
        if cut: pt[self._exclude_mask_skyonly]= healpy.UNSEEN
        cmap= cm.viridis
        cmap.set_under('w')
        kwargs['unit']= r'$\log_{10}\mathrm{number\ counts}$'
        kwargs['title']= kwargs.get('title',"")
        healpy.mollview(pt,nest=True,cmap=cmap,**kwargs)
        return None

    def plot_cmd(self,type='sf',cut=True):
        """
        NAME:
           plot_cmd
        PURPOSE:
           Plot the distribution of counts in the color-magnitude diagram
        INPUT:
           type= ('sf') Plot 'sf': selection function
                             'tgas': TGAS counts
                             '2mass': 2MASS counts
           cut= (True) cut to the 'good' part of the sky
        OUTPUT:
           Plot to output device
        HISTORY:
           2017-01-17 - Written - Bovy (UofT/CCA)
        """
        jtbins= (numpy.amax(_2mc[0])-numpy.amin(_2mc[0]))/0.1+1
        nstar2mass, edges= numpy.histogramdd(\
            _2mc[:3].T,bins=[jtbins,3,_BASE_NPIX],
            range=[[numpy.amin(_2mc[0])-0.05,numpy.amax(_2mc[0])+0.05],
                   [-0.05,1.0],[-0.5,_BASE_NPIX-0.5]],weights=_2mc[3])
        findx= (self._full_jk > -0.05)*(self._full_jk < 1.0)\
            *(self._full_twomass['j_mag'] < 13.5)
        nstartgas, edges= numpy.histogramdd(\
            numpy.array([self._full_jt[findx],self._full_jk[findx],\
                             (self._full_tgas['source_id'][findx]\
                                  /2**(35.+2*(12.-numpy.log2(_BASE_NSIDE))))\
                             .astype('int')]).T,
            bins=[jtbins,3,_BASE_NPIX],
            range=[[numpy.amin(_2mc[0])-0.05,numpy.amax(_2mc[0])+0.05],
                   [-0.05,1.0],[-0.5,_BASE_NPIX-0.5]])
        if cut:
            nstar2mass[:,:,self._exclude_mask_skyonly]= numpy.nan
            nstartgas[:,:,self._exclude_mask_skyonly]= numpy.nan
        nstar2mass= numpy.nansum(nstar2mass,axis=-1)
        nstartgas= numpy.nansum(nstartgas,axis=-1)
        if type == 'sf':
            pt= nstartgas/nstar2mass
            vmin= 0.
            vmax= 1.
            zlabel=r'$\mathrm{completeness}$'
        elif type == 'tgas' or type == '2mass':
            vmin= 0.
            vmax= 6.
            zlabel= r'$\log_{10}\mathrm{number\ counts}$'
            if type == 'tgas':
                pt= numpy.log10(nstartgas)
            elif type == '2mass':
                pt= numpy.log10(nstar2mass)
        return bovy_plot.bovy_dens2d(pt,origin='lower',
                                     cmap='viridis',interpolation='nearest',
                                     colorbar=True,shrink=0.78,
                                     vmin=vmin,vmax=vmax,zlabel=zlabel,
                                     yrange=[edges[0][0],edges[0][-1]],
                                     xrange=[edges[1][0],edges[1][-1]],
                                     xlabel=r'$J-K_s$',
                                     ylabel=r'$J+\Delta J$')
    def plot_magdist(self,type='sf',cut=True,splitcolors=False,overplot=False):
        """
        NAME:
           plot_magdist
        PURPOSE:
           Plot the distribution of counts in magnitude
        INPUT:
           type= ('sf') Plot 'sf': selection function
                             'tgas': TGAS counts
                             '2mass': 2MASS counts
           cut= (True) cut to the 'good' part of the sky
           splitcolors= (False) if True, plot the 3 color bins separately
        OUTPUT:
           Plot to output device
        HISTORY:
           2017-01-17 - Written - Bovy (UofT/CCA)
        """
        jtbins= (numpy.amax(_2mc[0])-numpy.amin(_2mc[0]))/0.1+1
        nstar2mass, edges= numpy.histogramdd(\
            _2mc[:3].T,bins=[jtbins,3,_BASE_NPIX],
            range=[[numpy.amin(_2mc[0])-0.05,numpy.amax(_2mc[0])+0.05],
                   [-0.05,1.0],[-0.5,_BASE_NPIX-0.5]],weights=_2mc[3])
        findx= (self._full_jk > -0.05)*(self._full_jk < 1.0)\
            *(self._full_twomass['j_mag'] < 13.5)
        nstartgas, edges= numpy.histogramdd(\
            numpy.array([self._full_jt[findx],self._full_jk[findx],\
                             (self._full_tgas['source_id'][findx]\
                                  /2**(35.+2*(12.-numpy.log2(_BASE_NSIDE))))\
                             .astype('int')]).T,
            bins=[jtbins,3,_BASE_NPIX],
            range=[[numpy.amin(_2mc[0])-0.05,numpy.amax(_2mc[0])+0.05],
                   [-0.05,1.0],[-0.5,_BASE_NPIX-0.5]])
        if cut:
            nstar2mass[:,:,self._exclude_mask_skyonly]= numpy.nan
            nstartgas[:,:,self._exclude_mask_skyonly]= numpy.nan
        nstar2mass= numpy.nansum(nstar2mass,axis=-1)
        nstartgas= numpy.nansum(nstartgas,axis=-1)
        exs= 0.5*(numpy.roll(edges[0],1)+edges[0])[1:]
        for ii in range(3):
            if type == 'sf':
                if splitcolors:
                    pt= nstartgas[:,ii]/nstar2mass[:,ii]
                else:
                    pt= numpy.nansum(nstartgas,axis=-1)\
                        /numpy.nansum(nstar2mass,axis=-1)
                vmin= 0.
                vmax= 1.
                ylabel=r'$\mathrm{completeness}$'
                semilogy= False
            elif type == 'tgas' or type == '2mass':
                vmin= 1.
                vmax= 10**6.
                ylabel= r'$\log_{10}\mathrm{number\ counts}$'
                semilogy= True
                if type == 'tgas':
                    if splitcolors:
                        pt= nstartgas[:,ii]
                    else:
                        pt= numpy.nansum(nstartgas,-1)
                elif type == '2mass':
                    if splitcolors:
                        pt= nstar2mass[:,ii]
                    else:
                        pt= numpy.nansum(nstar2mass,-1)
            bovy_plot.bovy_plot(exs,pt,ls='steps-mid',
                                xrange=[2.,14.],
                                yrange=[vmin,vmax],
                                semilogy=semilogy,
                                xlabel=r'$J+\Delta J$',
                                ylabel=ylabel,
                                overplot=(ii>0)+overplot)
            if not splitcolors: break
        return None

class tgasEffectiveSelect(object):
    def __init__(self,tgasSel,MJ=1.8,JK=0.25,dmap3d=None,
                 maxd=None):
        """
        NAME:
           __init__
        PURPOSE:
           Initialize the effective TGAS selection function for a population of stars
        INPUT:
           tgasSel - a tgasSelect object with the TGAS selection function
           MJ= (1.8) absolute magnitude in J or an array of samples of absolute magnitudes in J for the tracer population
           JK= (0.25) J-Ks color or an array of samples of the J-Ks color
           dmap3d= if given, a mwdust.Dustmap3D object that returns the J-band extinction in 3D; if not set use no extinction
           maxd= (None) if given, only consider distances up to this maximum distance (in kpc)
        OUTPUT:
           TGAS-effective-selection-function object
        HISTORY:
           2017-01-18 - Started - Bovy (UofT/CCA)
        """
        self._tgasSel= tgasSel
        self._maxd= maxd
        # Parse MJ
        if isinstance(MJ,(int,float)):
            self._MJ= numpy.array([MJ])
        elif isinstance(MJ,list):
            self._MJ= numpy.array(MJ)
        else:
            self._MJ= MJ
        # Parse JK
        if isinstance(JK,(int,float)):
            self._JK= numpy.array([JK])
        elif isinstance(JK,list):
            self._JK= numpy.array(JK)
        else:
            self._JK= JK
        # Parse dust map
        if dmap3d is None:
            if not _MWDUSTLOADED:
                raise ImportError("mwdust module not installed, required for extinction tools; download and install from http://github.com/jobovy/mwdust")
            dmap3d= mwdust.Zero(filter='2MASS J')
        self._dmap3d= dmap3d
        return None

    def __call__(self,dist,ra,dec,MJ=None,JK=None):
        """
        NAME:
           __call__
        PURPOSE:
           Evaluate the effective selection function
        INPUT:
           distance - distance in kpc (can be array)
           ra, dec - sky coordinates (deg), scalars
           MJ= (object-wide default) absolute magnitude in J or an array of samples of absolute  magnitudes in J for the tracer population
           JK= (object-wide default) J-Ks color or an array of samples of the J-Ks color 
        OUTPUT
           effective selection fraction
        HISTORY:
           2017-01-18 - Written - Bovy (UofT/CCA)
        """
        if isinstance(dist,(int,float)):
            dist= numpy.array([dist])
        elif isinstance(dist,list):
            dist= numpy.array(dist)
        MJ, JK= self._parse_mj_jk(MJ,JK)
        distmod= 5.*numpy.log10(dist)+10.
        # Extract the distribution of A_J and A_J-A_Ks at this distance 
        # from the dust map, use twice the radius of a pixel for this
        lcen, bcen= bovy_coords.radec_to_lb(ra,dec,degree=True)
        pixarea, aj= self._dmap3d.dust_vals_disk(\
            lcen,bcen,dist,healpy.nside2resol(_BASE_NSIDE)/numpy.pi*180.)
        totarea= numpy.sum(pixarea)
        ejk= aj*(1.-1./2.5) # Assume AJ/AK = 2.5
        distmod= numpy.tile(distmod,(aj.shape[0],1))
        pixarea= numpy.tile(pixarea,(len(dist),1)).T
        out= numpy.zeros_like(dist)
        for mj,jk in zip(MJ,JK):
            tj= mj+distmod+aj
            tjk= jk+ejk
            out+= numpy.sum(pixarea*self._tgasSel(tj,tjk,ra,dec),axis=0)
        if not self._maxd is None:
            out[dist > self._maxd]= 0.
        return out/totarea/len(MJ)

    def volume(self,vol_func,xyz=False,MJ=None,JK=None,ndists=101,
               ncpu=None):
        """
        NAME:
           volume
        PURPOSE:
           Compute the effective volume of a spatial volume under this effective selection function
        INPUT:
           vol_func - function of 
                         (a) (ra/deg,dec/deg,dist/kpc)
                         (b) heliocentric Galactic X,Y,Z if xyz
                      that returns 1. inside the spatial volume under consideration and 0. outside of it, should be able to take array input of a certain shape and return an array with the same shape
           xyz= (False) if True, vol_func is a function of X,Y,Z (see above)
           MJ= (object-wide default) absolute magnitude in J or an array of samples of absolute  magnitudes in J for the tracer population
           JK= (object-wide default) J-Ks color or an array of samples of the J-Ks color 
           ndists= (101) number of distances to use in the distance integration
           ncpu= (None) if set to an integer, use this many CPUs to compute the effective selection function (only for non-zero extinction)
        OUTPUT
           effective volume
        HISTORY:
           2017-01-18 - Written - Bovy (UofT/CCA)
        """           
        # Pre-compute coordinates for integrand evaluation            
        if not hasattr(self,'_ra_cen_4vol') or \
                (hasattr(self,'_ndists_4vol') and ndists != self._ndists_4vol):
            theta,phi= healpy.pix2ang(\
                _BASE_NSIDE,numpy.arange(_BASE_NPIX)\
                    [True-self._tgasSel._exclude_mask_skyonly],nest=True)
            self._ra_cen_4vol= 180./numpy.pi*phi
            self._dec_cen_4vol= 90.-180./numpy.pi*theta
            dms= numpy.linspace(0.,18.,ndists)
            self._deltadm_4vol= dms[1]-dms[0]
            self._dists_4vol= 10.**(0.2*dms-2.)
            self._tiled_dists3_4vol= numpy.tile(self._dists_4vol**3.,
                                                (len(self._ra_cen_4vol),1))
            self._tiled_ra_cen_4vol= numpy.tile(self._ra_cen_4vol,
                                                 (len(self._dists_4vol),1)).T
            self._tiled_dec_cen_4vol= numpy.tile(self._dec_cen_4vol,
                                                 (len(self._dists_4vol),1)).T
            lb= bovy_coords.radec_to_lb(phi,numpy.pi/2.-theta)
            l= numpy.tile(lb[:,0],(len(self._dists_4vol),1)).T.flatten()
            b= numpy.tile(lb[:,1],(len(self._dists_4vol),1)).T.flatten()
            XYZ_4vol= \
                bovy_coords.lbd_to_XYZ(l,b,
                   numpy.tile(self._dists_4vol,
                              (len(self._ra_cen_4vol),1)).flatten())
            self._X_4vol= numpy.reshape(XYZ_4vol[:,0],(len(self._ra_cen_4vol),
                                                       len(self._dists_4vol)))
            self._Y_4vol= numpy.reshape(XYZ_4vol[:,1],(len(self._ra_cen_4vol),
                                                       len(self._dists_4vol)))
            self._Z_4vol= numpy.reshape(XYZ_4vol[:,2],(len(self._ra_cen_4vol),
                                                       len(self._dists_4vol)))
        # Cache effective-selection function
        MJ, JK= self._parse_mj_jk(MJ,JK)
        new_hash= hashlib.md5(numpy.array([MJ,JK])).hexdigest()
        if not hasattr(self,'_vol_MJ_hash') or new_hash != self._vol_MJ_hash \
             or (hasattr(self,'_ndists_4vol') and ndists != self._ndists_4vol):
            # Need to update the effective-selection function
            if isinstance(self._dmap3d,mwdust.Zero): #easy bc same everywhere
                effsel_4vol= self(self._dists_4vol,
                                  self._ra_cen_4vol[0],
                                  self._dec_cen_4vol[0],MJ=MJ,JK=JK)
                self._effsel_4vol= numpy.tile(effsel_4vol,
                                              (len(self._ra_cen_4vol),1))
            else: # Need to treat each los separately
                if ncpu is None:
                    self._effsel_4vol= numpy.empty((len(self._ra_cen_4vol),
                                                    len(self._dists_4vol)))
                    for ii,(ra_cen, dec_cen) \
                            in enumerate(tqdm.tqdm(zip(self._ra_cen_4vol,
                                                       self._dec_cen_4vol))):
                        self._effsel_4vol[ii]= self(self._dists_4vol,
                                                    ra_cen,dec_cen,MJ=MJ,JK=JK)
                else:
                    multiOut= multi.parallel_map(\
                        lambda x: self(self._dists_4vol,
                                       self._ra_cen_4vol[x],
                                       self._dec_cen_4vol[x],MJ=MJ,JK=JK),
                        range(len(self._ra_cen_4vol)),
                        numcores=ncpu)
                    self._effsel_4vol= numpy.array(multiOut)
            self._vol_MJ_hash= new_hash
            self._ndists_4vol= ndists
        out= 0.
        if xyz:
            out= numpy.sum(\
                self._effsel_4vol\
                    *vol_func(self._X_4vol,self._Y_4vol,self._Z_4vol)\
                    *self._tiled_dists3_4vol)
        else:
            out= numpy.sum(\
                self._effsel_4vol\
                    *vol_func(self._ra_cen_4vol,self._dec_cen_4vol,
                              self._dists_4vol)\
                    *self._tiled_dists3_4vol)
        return out*numpy.log(10.)/5.\
            *healpy.nside2pixarea(_BASE_NSIDE)*self._deltadm_4vol

    def _parse_mj_jk(self,MJ,JK):
        if MJ is None: MJ= self._MJ
        if JK is None: JK= self._JK
        # Parse MJ
        if isinstance(MJ,(int,float)):
            MJ= numpy.array([MJ])
        elif isinstance(MJ,list):
            MJ= numpy.array(MJ)
        # Parse JK
        if isinstance(JK,(int,float)):
            JK= numpy.array([JK])
        elif isinstance(JK,list):
            JK= numpy.array(JK)
        return (MJ,JK)

def jt(jk,j):
    return j+jk**2.+2.5*jk
