import os, os.path
import numpy
import astropy.io.ascii
from gaia_tools.load import path, download
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
