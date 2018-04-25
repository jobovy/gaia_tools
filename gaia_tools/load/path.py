import os, os.path

_GAIA_TOOLS_DATA= os.getenv('GAIA_TOOLS_DATA')
if _GAIA_TOOLS_DATA is None:
    raise RuntimeError(
        'Environment variable `GAIA_TOOLS_DATA` is not set. '
        'This is required to define where the Gaia data are downloaded to. '
        'See the readme: https://github.com/jobovy/gaia_tools#data-files-and-environment-variables '
        'for more information.'
    )

def twomassPath(dr='tgas'):
    return os.path.join(_GAIA_TOOLS_DATA,'Gaia','gdr1','dstn_match',
                        'tgas-matched-2mass.fits.gz')

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

def gaiaSourcePath(dr=1,format='fits'):
    if format == 'csv': extension= 'csv.gz'
    else: extension= format
    if dr == 1 or dr == '1':
        out= []
        for jj in range(20):
            out.extend(\
              [os.path.join(_GAIA_TOOLS_DATA,'Gaia','gdr1','gaia_source',
                            format,
                            'GaiaSource_000-%03i-%03i.%s' % (jj,ii,extension))
               for ii in range(256)])
        out.extend([os.path.join(_GAIA_TOOLS_DATA,'Gaia','gdr1','gaia_source',
                            format,
                            'GaiaSource_000-020-%03i.%s' % (ii,extension))
                    for ii in range(111)])
        return out

def galahPath(dr=2):
    if dr == 1 or dr == '1':
        return (os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,
                             'catalog.dat'),
                os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'ReadMe'))
    elif dr == 2 or dr == '2':
        return os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % int(dr),
                            'GALAH_DR2_catalog.fits')

def lamostPath(dr=2,cat='all'):
    if cat.lower() == 'all':
        filename= 'dr2.fits'
    elif cat.lower() == 'a':
        filename= 'dr2_a_stellar.fits'
    elif cat.lower() == 'm':
        filename= 'dr2_m_stellar.fits'
    elif cat.lower() == 'star' or cat.lower() == 'stars':
        filename= 'dr2_stellar.fits'
    return os.path.join(_GAIA_TOOLS_DATA,'lamost','DR%i' % dr,filename)

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

def tgasPath(dr=1,old=False):
    if old:
        return [os.path.join(_GAIA_TOOLS_DATA,'Gaia','tgas_source','fits',
                             'TgasSource_000-000-%03i.fits' % ii)
                for ii in range(16)]
    else:
        return [os.path.join(_GAIA_TOOLS_DATA,'Gaia','gdr1','tgas_source','fits',
                             'TgasSource_000-000-%03i.fits' % ii)
                for ii in range(16)]
