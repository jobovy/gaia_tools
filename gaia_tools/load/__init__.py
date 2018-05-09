import os, os.path
import warnings
import pickle
import numpy
import numpy.lib.recfunctions
import astropy.io.ascii
try:
    import fitsio
    fitsread= fitsio.read
except ImportError:
    import astropy.io.fits as pyfits
    fitsread= pyfits.getdata
_APOGEE_LOADED= True
try:
    import apogee.tools.read as apread
except (ImportError,RuntimeError): # RuntimeError if apogee env. not setup
    _APOGEE_LOADED= False
from gaia_tools.load import path, download
from gaia_tools.util import save_pickles
def twomass(dr='tgas'):
    """
    NAME:
       twomass
    PURPOSE:
       Load the 2MASS data matched to TGAS data
    INPUT:
       dr= ('tgas') data release
    OUTPUT:
       data table
    HISTORY:
       2017-01-17 - Written - Bovy (UofT/CCA)
    """
    if not dr.lower() == 'tgas':
        raise ValueError('Only the 2MASS data matched to TGAS is available currently')
    filePath= path.twomassPath(dr=dr)
    if not os.path.exists(filePath):
        download.twomass(dr=dr)
    return fitsread(filePath,1)

def apogee(**kwargs):
    """
    PURPOSE:
       read the APOGEE allStar file
    INPUT:
       IF the apogee package is not installed:
           dr= (13) SDSS data release

       ELSE you can use the same keywords as apogee.tools.read.allstar:

       rmcommissioning= (default: True) if True, only use data obtained after commissioning
       main= (default: False) if True, only select stars in the main survey
       exclude_star_bad= (False) if True, remove stars with the STAR_BAD flag set in ASPCAPFLAG
       exclude_star_warn= (False) if True, remove stars with the STAR_WARN flag set in ASPCAPFLAG
       ak= (default: True) only use objects for which dereddened mags exist
       akvers= 'targ' (default) or 'wise': use target AK (AK_TARG) or AK derived from all-sky WISE (AK_WISE)
       rmnovisits= (False) if True, remove stars with no good visits (to go into the combined spectrum); shouldn't be necessary
       adddist= (default: False) add distances (DR10/11 Hayden distances, DR12 combined distances)
       distredux= (default: DR default) reduction on which the distances are based
       rmdups= (False) if True, remove duplicates (very slow)
       raw= (False) if True, just return the raw file, read w/ fitsio
    OUTPUT:
       allStar data
    HISTORY:
       2013-09-06 - Written - Bovy (IAS)
    """
    if not _APOGEE_LOADED:
        warnings.warn("Falling back on simple APOGEE interface; for more functionality, install the jobovy/apogee package")
        dr= kwargs.get('dr',13)
        filePath= path.apogeePath(dr=dr)
        if not os.path.exists(filePath):
            download.apogee(dr=dr)
        return fitsread(filePath,1)
    else:
        return apread.allStar(**kwargs)

def apogeerc(**kwargs):
    """
    NAME:
       apogeerc
    PURPOSE:
       read the APOGEE RC data
    INPUT:
       IF the apogee package is not installed:
           dr= (13) SDSS data release

       ELSE you can use the same keywords as apogee.tools.read.rcsample:

       main= (default: False) if True, only select stars in the main survey
       dr= data reduction to load the catalog for (automatically set based on APOGEE_REDUX if not given explicitly)
    OUTPUT:
       APOGEE RC sample data
    HISTORY:
       2013-10-08 - Written - Bovy (IAS)
    """
    if not _APOGEE_LOADED:
        warnings.warn("Falling back on simple APOGEE interface; for more functionality, install the jobovy/apogee package")
        dr= kwargs.get('dr',13)
        filePath= path.apogeercPath(dr=dr)
        if not os.path.exists(filePath):
            download.apogeerc(dr=dr)
        return fitsread(filePath,1)
    else:
        return apread.rcsample(**kwargs)
  
def gaiarv(dr=2):
    """
    NAME:
       gaiarv
    PURPOSE:
       Load the RV subset of the Gaia data
    INPUT:
       dr= (2) data release
    OUTPUT:
       data table
    HISTORY:
       2018-04-25 - Written for DR2 - Bovy (UofT)
    """
    filePaths= path.gaiarvPath(dr=dr,format='fits')
    if not numpy.all([os.path.exists(filePath) for filePath in filePaths]):
        download.gaiarv(dr=dr)
    return numpy.lib.recfunctions.stack_arrays(\
        [fitsread(filePath,ext=1) for filePath in filePaths],
        autoconvert=True)

def galah(dr=2,xmatch=None,**kwargs):
    """
    NAME:
       galah
    PURPOSE:
       Load the GALAH data
    INPUT:
       dr= (2) data release
       xmatch= (None) if set, cross-match against a Vizier catalog (e.g., vizier:I/345/gaia2 for Gaia DR2) using gaia_tools.xmatch.cds and return the overlap
       +gaia_tools.xmatch.cds keywords
    OUTPUT:
       data table[,xmatched table]
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
       2018-04-19 - Updated for DR2 - Bovy (UofT)
       2018-05-08 - Add xmatch - Bovy (UofT)
    """
    if dr == 1 or dr == '1':
        filePath, ReadMePath= path.galahPath(dr=dr)
    else:
        filePath= path.galahPath(dr=dr)
    if not os.path.exists(filePath):
        download.galah(dr=dr)
    if dr == 1  or dr == '1':
        data= astropy.io.ascii.read(filePath,readme=ReadMePath)
        data['RA']._fill_value= numpy.array([-9999.99])
        data['dec']._fill_value= numpy.array([-9999.99])
    else:
        data= fitsread(filePath,1)
    if not xmatch is None:
        if dr == 1  or dr == '1':
            kwargs['colRA']= kwargs.get('colRA','RA')
            kwargs['colDec']= kwargs.get('colDec','dec')
        else:
            kwargs['colRA']= kwargs.pop('colRA','raj2000')
            kwargs['colDec']= kwargs.pop('colDec','dej2000')
        ma,mai= _xmatch_cds(xmatch,filePath,**kwargs)
        return (data[mai],ma)
    else:
        return data

def lamost(dr=2,cat='all'):
    """
    NAME:
       lamost
    PURPOSE:
       Load the LAMOST data
    INPUT:
       dr= (2) data release
       cat= ('all') 'all', 'A', 'M', 'star' (see LAMOST docs)
    OUTPUT:
       data table
    HISTORY:
       2016-10-13 - Written - Bovy (UofT)
    """
    filePath= path.lamostPath(dr=dr,cat=cat)
    if not os.path.exists(filePath):
        download.lamost(dr=dr,cat=cat)
    data= fitsread(filePath,1)
    return data

def rave(dr=5, usecols=None):
    """
    NAME:
       rave
    PURPOSE:
       Load the RAVE data
    INPUT:
       dr= (5) data release
       usecols= (sequence, optional) indices to read from RAVE data
    OUTPUT:
       data table
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
    """
    filePath, ReadMePath= path.ravePath(dr=dr)
    if not os.path.exists(filePath):
        download.rave(dr=dr)
    if dr == 4:
        data= astropy.io.ascii.read(filePath,readme=ReadMePath)
    elif dr == 5:
        if usecols:
            data= numpy.genfromtxt(filePath,delimiter=',', names=True, usecols=usecols)
        else:
            data= numpy.genfromtxt(filePath,delimiter=',', names=True)
    return data

def raveon(dr=5):
    """
    NAME:
       raveon
    PURPOSE:
       Load the RAVE-on data
    INPUT:
       dr= (5) RAVE data release
    OUTPUT:
       data table
    HISTORY:
       2016-09-20 - Written - Bovy (UofT)
    """
    filePath= path.raveonPath(dr=dr)
    if not os.path.exists(filePath):
        download.raveon(dr=dr)
    data= fitsread(filePath,1)
    return data

def tgas(dr=1):
    """
    NAME:
       tgas
    PURPOSE:
       Load the TGAS data
    INPUT:
       dr= (1) data release
    OUTPUT:
       data table
    HISTORY:
       2016-09-14 - Written - Bovy (UofT)
    """
    filePaths= path.tgasPath(dr=dr)
    if not numpy.all([os.path.exists(filePath) for filePath in filePaths]):
        download.tgas(dr=dr)
    return numpy.lib.recfunctions.stack_arrays(\
        [fitsread(filePath,ext=1) for filePath in filePaths],
        autoconvert=True)

def _xmatch_cds(xcat,filePath,**kwargs):
    if xcat.lower() == 'gaiadr2' or xcat.lower() == 'gaia2':
        xcat= 'vizier:I/345/gaia2'
    maxdist= kwargs.pop('maxdist',2.)
    # Check whether the cached x-match exists
    xmatch_filename= xmatch_cache_filename(filePath,xcat,maxdist)
    if os.path.exists(xmatch_filename):
        with open(xmatch_filename,'rb') as savefile:
            ma= pickle.load(savefile)
            mai= pickle.load(savefile)
    else:
        from gaia_tools.xmatch import cds
        ma,mai= cds(data,xcat=xcat,maxdist=maxdist,**kwargs)
        save_pickles(xmatch_filename,ma,mai)
    return (ma,mai)

def xmatch_cache_filename(filePath,xcat,maxdist):
    filename,fileExt= os.path.splitext(filePath)
    cachePath= filename+'_xmatch_{}_maxdist_{:.2f}'.format(xcat.replace('/','_').replace(':','_'),maxdist)+'.pkl'
    return cachePath
    
