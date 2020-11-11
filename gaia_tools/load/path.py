import os, os.path
import glob

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

def apogeePath(dr=14):
    if dr == 12:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'allStar-v603.fits')
    elif dr == 13:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'allStar-l30e.2.fits')
    elif dr == 14:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'allStar-l31c.2.fits')

def apogeercPath(dr=14):
    return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                        'apogee-rc-DR%i.fits' % dr)

def astroNNPath(dr=14):
    if dr == 14:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'astroNN_apogee_dr14_catalog.fits')
    else:
        raise ValueError('astroNN catalog for DR =/= 14 not available')

def astroNNDistancesPath(dr=14):
    if dr == 14:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'apogee_dr14_nn_dist.fits')
    else:
        raise ValueError('astroNN distances catalog for DR =/= 14 not available')

def astroNNAgesPath(dr=14):
    if dr == 14:
        return os.path.join(_GAIA_TOOLS_DATA,'apogee','DR%i' % dr,
                            'astroNNBayes_ages_goodDR14.fits')
    else:
        raise ValueError('astroNN ages catalog for DR =/= 14 not available')

def gaiarvPath(dr=2,format='fits'):
    if format == 'csv': extension= 'csv.gz'
    else: extension= format
    if dr == 2 or dr == '2':
        filenames= ['GaiaSource_1584380076484244352_2200921635402776448',
                    'GaiaSource_2200921875920933120_3650804325670415744',
                    'GaiaSource_2851858288640_1584379458008952960',
                    'GaiaSource_3650805523966057472_4475721411269270528',
                    'GaiaSource_4475722064104327936_5502601461277677696',
                    'GaiaSource_5502601873595430784_5933051501826387072',
                    'GaiaSource_5933051914143228928_6714230117939284352',
                    'GaiaSource_6714230465835878784_6917528443525529728']
        return [os.path.join(_GAIA_TOOLS_DATA,'Gaia','gdr2',
                             'gaia_source_with_rv',format,
                             f+'.%s' % extension) for f in filenames]

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
    elif dr == 2 or dr == '2':
        return glob.glob(os.path.join(_GAIA_TOOLS_DATA,'Gaia','gdr2',
                                      'gaia_source',format,
                                      'GaiaSource_*.%s' % extension))
    return out

def galahPath(dr=3):
    if dr == 1 or dr == '1':
        return (os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,
                             'catalog.dat'),
                os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % dr,'ReadMe'))
    elif dr == 2 or dr == '2' or dr == 2.1 or dr == '2.1':
        return os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % int(dr),
                            'GALAH_DR2.1_catalog.fits')
    elif dr == 3 or dr == '3':
        return os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % int(dr),
                            'GALAH_DR3_main_allstar_v1.fits')

def galahAgesPath(dr=3):
    if dr == 3 or dr == '3':
        return os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % int(dr),
                            'GALAH_DR3_VAC_ages_v1.fits')

def galahDynamicsPath(dr=3):
    if dr == 3 or dr == '3':
        return os.path.join(_GAIA_TOOLS_DATA,'galah','DR%i' % int(dr),
                            'GALAH_DR3_VAC_dynamics_v1.fits')

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
