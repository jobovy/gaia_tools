import os, os.path
_GAIA_TOOLS_DATA= os.getenv('GAIA_TOOLS_DATA')
def galahPath(dr=1):
    return (os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'catalog.dat'),
            os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'ReadMe'))
