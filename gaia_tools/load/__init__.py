import os, os.path
import warnings
import pickle
from operator import itemgetter   
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

def apogee(xmatch=None,**kwargs):
    """
    PURPOSE:
       read the APOGEE allStar file
    INPUT:
       IF the apogee package is not installed:
           dr= (14) SDSS data release
           use_astroNN= (False) if True, swap in astroNN (Leung & Bovy 2019a) parameters (get placed in, e.g., TEFF and TEFF_ERR) and add astroNN distances (Leung & Bovy 2019b) and ages (Mackereth, Bovy, Leung, et al. 2019); use 'use_astroNN_abundances', 'use_astroNN_distances', and 'use_astroNN_ages' to only add abundances, distances, or ages respectively

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
    
       ALWAYS ALSO

       xmatch= (None) if set, cross-match against a Vizier catalog (e.g., vizier:I/345/gaia2 for Gaia DR2) using gaia_tools.xmatch.cds and return the overlap
       +gaia_tools.xmatch.cds keywords
    OUTPUT:
       allStar data[,xmatched table]
    HISTORY:
       2013-09-06 - Written - Bovy (IAS)
       2018-05-09 - Add xmatch - Bovy (UofT)
    """
    if not _APOGEE_LOADED:
        _warn_apogee_fallback()
        dr= kwargs.get('dr',14)
        filePath= path.apogeePath(dr=dr)
        if not os.path.exists(filePath):
            download.apogee(dr=dr)
        data= fitsread(filePath,1)
        #Add astroNN? astroNN files matched line-by-line to allStar, 
        #so match here [ages not matched line-by-line...]
        if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False) \
                or kwargs.get('use_astroNN_abundances'):
            _warn_astroNN_abundances()
            astroNNdata= astroNN()
            data= _swap_in_astroNN(data,astroNNdata)
        if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False) \
                or kwargs.get('use_astroNN_distances'):
            _warn_astroNN_distances()
            astroNNDistancesdata= astroNNDistances()
            data= _add_astroNN_distances(data,astroNNDistancesdata)
        if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False) \
                or kwargs.get('use_astroNN_ages'):
            _warn_astroNN_ages()
            astroNNAgesdata= astroNNAges()
            data= _add_astroNN_ages(data,astroNNAgesdata)
        if not xmatch is None:
            if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False) \
                    or kwargs.get('use_astroNN_ages'):
                matchFilePath= filePath.replace('rc-','rc-astroNN-ages-')
            else:
                matchFilePath= filePath
            kwargs.pop('use_astroNN',False)
            kwargs.pop('use_astroNN_abundances',False)
            kwargs.pop('use_astroNN_distances',False)
            kwargs.pop('use_astroNN_ages',False)
            kwargs.pop('astroNN',False)
            ma,mai= _xmatch_cds(data,xmatch,matchFilePath,**kwargs)
            return (data[mai],ma)
        else:
            return data
    else:
        kwargs['xmatch']= xmatch
        return apread.allStar(**kwargs)

def apogeerc(xmatch=None,**kwargs):
    """
    NAME:
       apogeerc
    PURPOSE:
       read the APOGEE RC data
    INPUT:
       IF the apogee package is not installed:
           dr= (14) SDSS data release
           use_astroNN= (False) if True, swap in astroNN (Leung & Bovy 2019a) parameters (get placed in, e.g., TEFF and TEFF_ERR) and add astroNN distances (Leung & Bovy 2019b) and ages (Mackereth, Bovy, Leung, et al. 2019); use 'use_astroNN_abundances', 'use_astroNN_distances', and 'use_astroNN_ages' to only add abundances, distances, or ages respectively

       ELSE you can use the same keywords as apogee.tools.read.rcsample:

       main= (default: False) if True, only select stars in the main survey
       dr= data reduction to load the catalog for (automatically set based on APOGEE_REDUX if not given explicitly)

       ALWAYS ALSO

       xmatch= (None) if set, cross-match against a Vizier catalog (e.g., vizier:I/345/gaia2 for Gaia DR2) using gaia_tools.xmatch.cds and return the overlap
       +gaia_tools.xmatch.cds keywords
    OUTPUT:
       APOGEE RC sample data[,xmatched table]
    HISTORY:
       2013-10-08 - Written - Bovy (IAS)
       2018-05-09 - Add xmatch - Bovy (UofT)
    """
    if not _APOGEE_LOADED:
        _warn_apogee_fallback()
        dr= kwargs.get('dr',14)
        filePath= path.apogeercPath(dr=dr)
        if not os.path.exists(filePath):
            download.apogeerc(dr=dr)
        data= fitsread(filePath,1)
        # Swap in astroNN results?
        if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False) \
                or kwargs.get('use_astroNN_abundances'):
            _warn_astroNN_abundances()
            astroNNdata= astroNN()
            # Match on (ra,dec)
            from gaia_tools.xmatch import xmatch as gxmatch
            m1,m2,_= gxmatch(data,astroNNdata,maxdist=2.,
                             colRA1='RA',colDec1='DEC',epoch1=2000.,
                             colRA2='RA',colDec2='DEC',epoch2=2000.)
            data= data[m1]
            astroNNdata= astroNNdata[m2]
            data= _swap_in_astroNN(data,astroNNdata)
        if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False) \
                or kwargs.get('use_astroNN_distances'):
            _warn_astroNN_distances()
            astroNNdata= astroNNDistances()
            # Match on (ra,dec)
            from gaia_tools.xmatch import xmatch as gxmatch
            m1,m2,_= gxmatch(data,astroNNdata,maxdist=2.,
                             colRA1='RA',colDec1='DEC',epoch1=2000.,
                             colRA2='ra_apogee',colDec2='dec_apogee',
                             epoch2=2000.)
            data= data[m1]
            astroNNdata= astroNNdata[m2]
            data= _add_astroNN_distances(data,astroNNdata)
        if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False) \
                or kwargs.get('use_astroNN_ages'):
            _warn_astroNN_ages()
            astroNNAgesdata= astroNNAges()
            data= _add_astroNN_ages(data,astroNNAgesdata)
        if not xmatch is None:
            if kwargs.get('use_astroNN',False) or kwargs.get('astroNN',False):
                matchFilePath= filePath.replace('rc-','rc-astroNN-')
            elif kwargs.get('use_astroNN_abundances',False):
                matchFilePath= filePath.replace('rc-','rc-astroNN-abundances-')
            elif kwargs.get('use_astroNN_distances',False):
                matchFilePath= filePath.replace('rc-','rc-astroNN-distances-')
            elif kwargs.get('use_astroNN_ages',False):
                matchFilePath= filePath.replace('rc-','rc-astroNN-ages-')
            else:
                matchFilePath= filePath
            kwargs.pop('use_astroNN',False)
            kwargs.pop('use_astroNN_abundances',False)
            kwargs.pop('use_astroNN_distances',False)
            kwargs.pop('use_astroNN_ages',False)
            kwargs.pop('astroNN',False)           
            ma,mai= _xmatch_cds(data,xmatch,matchFilePath,**kwargs)
            return (data[mai],ma)
        else:
            return data
    else:
        kwargs['xmatch']= xmatch
        return apread.rcsample(**kwargs)
  
def astroNN(**kwargs):
    """
    NAME:
       astroNN
    PURPOSE:
       read the astroNN file (Leung & Bovy 2019a)
    INPUT:
       dr= data reduction to load the catalog for (automatically set based on APOGEE_REDUX if not given explicitly)
    OUTPUT:
       astroNN data
    HISTORY:
       2018-10-20 - Written - Bovy (UofT)
    """
    if not _APOGEE_LOADED:
        _warn_apogee_fallback()
        dr= kwargs.get('dr',14)
        filePath= path.astroNNPath(dr=dr)
        if not os.path.exists(filePath):
            download.astroNN(dr=dr)
        data= fitsread(filePath,1)
        return data
    else:
        return apread.astroNN(**kwargs)

def astroNNDistances(**kwargs):
    """
    NAME:
       astroNNDistances
    PURPOSE:
       read the astroNNDistances file (Leung & Bovy 2019b)
    INPUT:
       dr= data reduction to load the catalog for (automatically set based on APOGEE_REDUX if not given explicitly)
    OUTPUT:
       astroNN data
    HISTORY:
       2019-02-15 - Written - Bovy (UofT)
    """
    if not _APOGEE_LOADED:
        _warn_apogee_fallback()
        dr= kwargs.get('dr',14)
        filePath= path.astroNNDistancesPath(dr=dr)
        if not os.path.exists(filePath):
            download.astroNNDistances(dr=dr)
        data= fitsread(filePath,1)
        return data
    else:
        return apread.astroNNDistances(**kwargs)

def astroNNAges(**kwargs):
    """
    NAME:
       astroNNAges
    PURPOSE:
       read the astroNNAges file (Mackereth, Bovy, Leung, et al. 2019)
    INPUT:
       dr= data reduction to load the catalog for (automatically set based on APOGEE_REDUX if not given explicitly)
    OUTPUT:
       astroNN data
    HISTORY:
       2019-02-15 - Written - Bovy (UofT)
    """
    if not _APOGEE_LOADED:
        _warn_apogee_fallback()
        dr= kwargs.get('dr',14)
        filePath= path.astroNNAgesPath(dr=dr)
        if not os.path.exists(filePath):
            download.astroNNAges(dr=dr)
        data= fitsread(filePath,1)
        return data
    else:
        return apread.astroNNAges(**kwargs)

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
        ma,mai= _xmatch_cds(data,xmatch,filePath,**kwargs)
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

def _xmatch_cds(data,xcat,filePath,**kwargs):
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
    
# Support to swap in astroNN into the APOGEE data
def _elemIndx(elem,dr=14):
    """Version of apogee.tools.elemIndx for internal use here, not as general"""
    if dr == 14:
        _ELEM_SYMBOL= ['c','ci','n','o','na','mg','al','si','p','s','k','ca',
                       'ti','tiii','v','cr','mn','fe','co','ni','cu','ge','ce',
                       'rb','y','nd']
    else:
        raise ValueError('The functionality you are attempting to use is only available for APOGEE DR14')
    try:
        return _ELEM_SYMBOL.index(elem.lower())
    except ValueError:
        raise KeyError("Element %s is not part of the APOGEE elements (can't do everything!) or something went wrong)" % elem)

def _swap_in_astroNN(data,astroNNdata):
    for tag,indx in zip(['TEFF','LOGG'],[0,1]):
        data[tag]= astroNNdata['astroNN'][:,indx]
        data[tag+'_ERR']= astroNNdata['astroNN_error'][:,indx]
    for tag,indx in zip(['C','CI','N','O','Na','Mg','Al','Si','P','S','K',
                         'Ca','Ti','TiII','V','Cr','Mn','Fe','Co','Ni'],
                        range(2,22)):
        data['X_H'][:,_elemIndx(tag.upper())]=\
            astroNNdata['astroNN'][:,indx]
        data['X_H_ERR'][:,_elemIndx(tag.upper())]=\
            astroNNdata['astroNN_error'][:,indx]
        if tag.upper() != 'FE':
            data['{}_FE'.format(tag.upper())]=\
                astroNNdata['astroNN'][:,indx]-astroNNdata['astroNN'][:,19]
            data['{}_FE_ERR'.format(tag.upper())]=\
                numpy.sqrt(astroNNdata['astroNN_error'][:,indx]**2.
                           +astroNNdata['astroNN_error'][:,19]**2.)
        else:
            data['FE_H'.format(tag.upper())]=\
                        astroNNdata['astroNN'][:,indx]
            data['FE_H_ERR'.format(tag.upper())]=\
                astroNNdata['astroNN_error'][:,indx]
    return data

def _add_astroNN_distances(data,astroNNDistancesdata):
    fields_to_append= ['dist','dist_model_error','dist_error',
                       'weighted_dist','weighted_dist_error']
    if True:
        # Faster way to join structured arrays (see https://stackoverflow.com/questions/5355744/numpy-joining-structured-arrays)
        newdtype= data.dtype.descr+\
            [(f,'<f8') for f in fields_to_append]
        newdata= numpy.empty(len(data),dtype=newdtype)
        for name in data.dtype.names:
            newdata[name]= data[name]
        for f in fields_to_append:
            newdata[f]= astroNNDistancesdata[f]
        return newdata
    else:
        return numpy.lib.recfunctions.append_fields(\
            data,
            fields_to_append,
            [astroNNDistancesdata[f] for f in fields_to_append],
            [astroNNDistancesdata[f].dtype for f in fields_to_append],
            usemask=False)

def _add_astroNN_ages(data,astroNNAgesdata):
    fields_to_append= ['astroNN_age','astroNN_age_total_std',
                       'astroNN_age_predictive_std','astroNN_age_model_std']
    if True:
        # Faster way to join structured arrays (see https://stackoverflow.com/questions/5355744/numpy-joining-structured-arrays)
        newdtype= data.dtype.descr+\
            [(f,'<f8') for f in fields_to_append]
        newdata= numpy.empty(len(data),dtype=newdtype)
        for name in data.dtype.names:
            newdata[name]= data[name]
        for f in fields_to_append:
            newdata[f]= numpy.zeros(len(data))-9999.
        data= newdata
    else:
        # This, for some reason, is the slow part (see numpy/numpy#7811
        data= numpy.lib.recfunctions.append_fields(\
            data,
            fields_to_append,
            [numpy.zeros(len(data))-9999. for f in fields_to_append],
            usemask=False)
    # Only match primary targets
    hash1= dict(zip(data['APOGEE_ID'][(data['EXTRATARG'] & 2**4) == 0],
                    numpy.arange(len(data))[(data['EXTRATARG'] & 2**4) == 0]))
    hash2= dict(zip(astroNNAgesdata['APOGEE_ID'],
                    numpy.arange(len(astroNNAgesdata))))
    common= numpy.intersect1d(\
        data['APOGEE_ID'][(data['EXTRATARG'] & 2**4) == 0],
        astroNNAgesdata['APOGEE_ID'])
    indx1= list(itemgetter(*common)(hash1))
    indx2= list(itemgetter(*common)(hash2))
    for f in fields_to_append:
        data[f][indx1]= astroNNAgesdata[f][indx2]
    return data

def _warn_apogee_fallback():
    warnings.warn("Falling back on simple APOGEE interface; for more functionality, install the jobovy/apogee package")

def _warn_astroNN_abundances():
    warnings.warn("Swapping in stellar parameters and abundances from Leung & Bovy (2019a)")

def _warn_astroNN_distances():
    warnings.warn("Adding distances from Leung & Bovy (2019b)")

def _warn_astroNN_ages():
    warnings.warn("Adding ages from Mackereth, Bovy, Leung, et al. (2019)")
