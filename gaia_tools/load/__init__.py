import os, os.path
import numpy
import astropy.io.ascii
_APOGEE_LOADED= True
try:
    import apogee.tools.read as apread
except ImportError:
    _APOGEE_LOADED= False
from gaia_tools.load import path, download
def apogee(**kwargs):
    """
    PURPOSE:
       read the APOGEE allStar file
    INPUT:
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
        raise ImportError("Loading the APOGEE data requires the jobovy/apogee module to be installed")
    return apread.allStar(**kwargs)

def galah(dr=1):
    """
    NAME:
       galah
    PURPOSE:
       Load the GALAH data
    INPUT:
       dr= (1) data release
    OUTPUT:
       data table
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
    """
    filePath, ReadMePath= path.galahPath(dr=dr)
    if not os.path.exists(filePath):
        download.galah(dr=dr)
    data= astropy.io.ascii.read(filePath,readme=ReadMePath)
    data['RA']._fill_value= numpy.array([-9999.99])
    data['dec']._fill_value= numpy.array([-9999.99])
    return data
