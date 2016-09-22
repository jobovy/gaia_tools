import os, os.path
_GAIA_TOOLS_DATA= os.getenv('GAIA_TOOLS_DATA')
def apogeePath(dr=13):
    if dr == 12:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'allStar-v603.fits')
    elif dr == 13:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'allStar-l30e.2.fits')

def apogeercPath(dr=13):
    return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                        'apogee-rc-DR%i.fits' % dr)

def galahPath(dr=1):
    return (os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'catalog.dat'),
            os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'ReadMe'))

def ravePath(dr=5):
    if dr == 4:
        return (os.path.join(_GAIA_TOOLS_DATA,
                             'rave','DR%i' % dr,'ravedr%i.dat' % dr),
                os.path.join(_GAIA_TOOLS_DATA,'rave','DR%i' % dr,'ReadMe'))
    elif dr == 5:
        return (os.path.join(_GAIA_TOOLS_DATA,
                             'rave','DR%i' % dr,'RAVE_DR5.csv'),
                None)

def raveonPath(dr=5):
    return os.path.join(_GAIA_TOOLS_DATA,
                        'raveon','DR%i' % dr,'RAVE-on-v1.0.fits.gz')

def tgasPath(dr=1):
    return [os.path.join(_GAIA_TOOLS_DATA,'Gaia','tgas_source','fits',
                         'TgasSource_000-000-%03i.fits' % ii)
            for ii in range(16)]
