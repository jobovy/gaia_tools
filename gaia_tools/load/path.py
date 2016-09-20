import os, os.path
_GAIA_TOOLS_DATA= os.getenv('GAIA_TOOLS_DATA')
def galahPath(dr=1):
    return (os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'catalog.dat'),
            os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'ReadMe'))

def ravePath(dr=4):
    return (os.path.join(_GAIA_TOOLS_DATA,
                         'rave','DR%i' % dr,'ravedr%i.dat' % dr),
            os.path.join(_GAIA_TOOLS_DATA,'rave','DR%i' % dr,'ReadMe'))

def raveonPath(dr=5):
    return os.path.join(_GAIA_TOOLS_DATA,
                        'raveon','DR%i' % dr,'RAVE-on-v1.0.fits.gz')

def tgasPath(dr=1):
    return [os.path.join(_GAIA_TOOLS_DATA,'Gaia','tgas_source','fits',
                         'TgasSource_000-000-%03i.fits' % ii)
            for ii in range(16)]
