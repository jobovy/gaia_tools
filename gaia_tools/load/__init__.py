import os, os.path
import astropy.io.ascii
from gaia_tools.load import path, download
def galah(dr=1):
    filePath, ReadMePath= path.galahPath(dr=dr)
    if not os.path.exists(filePath):
        download.galah(dr=dr)
    data= astropy.io.ascii.read(filePath,readme=ReadMePath)
    return data
