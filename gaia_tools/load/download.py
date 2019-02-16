###############################################################################
#
#   gaia_tools.read.download: download data files automagically
#
###############################################################################
import sys
import os, os.path
import shutil
import tempfile
from ftplib import FTP
import subprocess
from astropy.io import ascii
from gaia_tools.load import path
_MAX_NTRIES= 2
_ERASESTR= "                                                                                "
def twomass(dr='tgas',verbose=True,spider=False):
    filePath= path.twomassPath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 'tgas':
        _download_file(\
            'http://portal.nersc.gov/project/cosmo/temp/dstn/gaia/tgas-matched-2mass.fits.gz',
            filePath,verbose=verbose,spider=spider)
    return None    
    
def apogee(dr=14,verbose=True,spider=False):
    filePath= path.apogeePath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 12:
        _download_file(\
            'http://data.sdss3.org/sas/dr12/apogee/spectro/redux/r5/allStar-v603.fits',
            filePath,verbose=verbose,spider=spider)
    elif dr == 13:
        _download_file(\
            'https://data.sdss.org/sas/dr13/apogee/spectro/redux/r6/allStar-l30e.2.fits',
            filePath,verbose=verbose,spider=spider)
    elif dr == 14:
        _download_file(\
            'https://data.sdss.org/sas/dr14/apogee/spectro/redux/r8/stars/l31c/l31c.2/allStar-l31c.2.fits',
            filePath,verbose=verbose,spider=spider)
    return None    
    
def apogeerc(dr=14,verbose=True,spider=False):
    filePath= path.apogeercPath(dr=dr)
    if os.path.exists(filePath): return None
    _download_file(\
        'https://data.sdss.org/sas/dr%i/apogee/vac/apogee-rc/cat/apogee-rc-DR%i.fits' % (dr,dr),
        filePath,verbose=verbose,spider=spider)
    return None    
    
def astroNN(dr=14,verbose=True,spider=False):
    filePath= path.astroNNPath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 14:
        _download_file(\
            'https://github.com/henrysky/astroNN_spectra_paper_figures/ra\
w/master/astroNN_apogee_dr14_catalog.fits',
            filePath,verbose=verbose,spider=spider)
    return None    
    
def astroNNDistances(dr=14,verbose=True,spider=False):
    filePath= path.astroNNDistancesPath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 14:
        _download_file(\
            'https://github.com/henrysky/astroNN_gaia_dr2_paper/raw/master/'\
            'apogee_dr14_nn_dist.fits',
            filePath,verbose=verbose,spider=spider)
    return None    
    
def astroNNAges(dr=14,verbose=True,spider=False):
    filePath= path.astroNNAgesPath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 14:
        _download_file(\
            'http://www.astro.ljmu.ac.uk/~astjmack/APOGEEGaiaAges/'\
            'astroNNBayes_ages_goodDR14.fits',
            filePath,verbose=verbose,spider=spider)
    return None    
    
def galah(dr=2,verbose=True,spider=False):
    if dr == 1 or dr == '1':
        filePath, ReadMePath= path.galahPath(dr=dr)
    else:
        filePath= path.galahPath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 1:
        _download_file(\
            'https://cloudstor.aarnet.edu.au/plus/index.php/s/OMc9QWGG1koAK2D/download?path=%2F&files=catalog.dat',
            filePath,verbose=verbose,spider=spider)
        _download_file(\
            'https://cloudstor.aarnet.edu.au/plus/index.php/s/OMc9QWGG1koAK2D/download?path=%2F&files=ReadMe',
            ReadMePath,verbose=verbose,spider=spider)
    elif dr == 2 or dr == '2' or dr == 2.1 or dr == '2.1':
        # GALAH updated catalog May 10 2018; remove catalog downloaded before
        if os.path.exists(filePath.replace('DR2.1','DR2')):
            os.remove(filePath.replace('DR2.1','DR2'))
        _download_file(\
          os.path.join('https://datacentral.aao.gov.au/teamdata/GALAH/public/',
                       os.path.basename(filePath)),
            filePath,verbose=verbose,spider=spider)
    return None    
    
def lamost(dr=2,cat='all',verbose=True):
    filePath= path.lamostPath(dr=dr,cat=cat)
    if os.path.exists(filePath): return None
    downloadPath= filePath.replace(
        filePath,
        'http://dr2.lamost.org/catdl?name=%s' % os.path.basename(filePath))
    _download_file(downloadPath+'.gz',filePath+'.gz',verbose=verbose)
    # gunzip the file
    try:
        subprocess.check_call(['gunzip',
                               filePath+'.gz'])
    except subprocess.CalledProcessError:
        raise IOError('gunzipping the LAMOST catalog %s failed ...' % os.path.basename(filePath))
    return None    

def rave(dr=5,verbose=True):
    filePath, ReadMePath= path.ravePath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 4:
        vizier('III/272',filePath,ReadMePath,
               catalogname='ravedr4.dat',readmename='ReadMe')
    elif dr == 5:
        # Have to figure out what will happen tonight!
        _download_file(\
            'https://www.rave-survey.org/data/files/single?name=DR5/RAVE_DR5.csv.gz',
            filePath+'.gz',verbose=verbose)
        # gunzip the file
        try:
            subprocess.check_call(['gunzip',
                                   filePath+'.gz'])
        except subprocess.CalledProcessError:
            raise IOError('gunzipping the RAVE-DR5 catalog failed ...')
    return None    

def raveon(dr=5,verbose=True,spider=False):
    filePath= path.raveonPath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 5:
        _download_file(\
            'https://zenodo.org/record/154381/files/RAVE-on-v1.0.fits.gz',
            filePath,verbose=verbose,spider=spider)
    return None    
    
def tgas(dr=1,verbose=True):
    filePaths= path.tgasPath(dr=dr)
    old_filePaths= path.tgasPath(dr=dr,old=True)
    for filePath, old_filePath in zip(filePaths,old_filePaths):
        if os.path.exists(filePath): continue
        # after DR1, Gaia archive changed URL to include 'gdr1', which we 
        # now mirror locally, so check whether the file exists in the old 
        # location and mv if necessary
        if os.path.exists(old_filePath):
            try:
                # make all intermediate directories
                os.makedirs(os.path.dirname(filePath))
            except OSError: pass
            shutil.move(old_filePath,filePath)
            continue
        downloadPath= filePath.replace(path._GAIA_TOOLS_DATA.rstrip('/'),
                                       'http://cdn.gea.esac.esa.int')
        _download_file(downloadPath,filePath,verbose=verbose)
    return None    
    
def gaiarv(dr=2,verbose=True):
    filePaths= path.gaiarvPath(dr=dr,format='fits')
    csvFilePaths= path.gaiarvPath(dr=dr,format='csv')
    for filePath, csvFilePath in zip(filePaths,csvFilePaths):
        if os.path.exists(filePath): continue
        try:
            os.makedirs(os.path.dirname(filePath)) 
        except OSError: pass
        downloadPath= csvFilePath.replace(path._GAIA_TOOLS_DATA.rstrip('/'),
                                       'http://cdn.gea.esac.esa.int')
        _download_file(downloadPath,csvFilePath,verbose=verbose)
        data= ascii.read(csvFilePath,format='csv')
        data.write(filePath,format='fits')
    return None    
    
def vizier(cat,filePath,ReadMePath,
           catalogname='catalog.dat',readmename='ReadMe'):
    """
    NAME:
       vizier
    PURPOSE:
       download a catalog and its associated ReadMe from Vizier
    INPUT:
       cat - name of the catalog (e.g., 'III/272' for RAVE, or J/A+A/... for journal-specific catalogs)
       filePath - path of the file where you want to store the catalog (note: you need to keep the name of the file the same as the catalogname to be able to read the file with astropy.io.ascii)
       ReadMePath - path of the file where you want to store the ReadMe file
       catalogname= (catalog.dat) name of the catalog on the Vizier server
       readmename= (ReadMe) name of the ReadMe file on the Vizier server
    OUTPUT:
       (nothing, just downloads)
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
    """
    _download_file_vizier(cat,filePath,catalogname=catalogname)
    _download_file_vizier(cat,ReadMePath,catalogname=readmename)
    return None

def _download_file(downloadPath,filePath,verbose=False,spider=False):
    sys.stdout.write('\r'+"Downloading file %s ...\r" \
                         % (os.path.basename(filePath)))
    sys.stdout.flush()
    try:
        # make all intermediate directories
        os.makedirs(os.path.dirname(filePath)) 
    except OSError: pass
    # Safe way of downloading
    downloading= True
    interrupted= False
    file, tmp_savefilename= tempfile.mkstemp()
    os.close(file) #Easier this way
    ntries= 1
    while downloading:
        try:
            cmd= ['wget','%s' % downloadPath,
                  '-O','%s' % tmp_savefilename,
                  '--read-timeout=10',
                  '--tries=3']
            if not verbose: cmd.append('-q')
            if spider: cmd.append('--spider')
            subprocess.check_call(cmd)
            if not spider: shutil.move(tmp_savefilename,filePath)
            downloading= False
            if interrupted:
                raise KeyboardInterrupt
        except subprocess.CalledProcessError as e:
            if not downloading: #Assume KeyboardInterrupt
                raise
            elif ntries > _MAX_NTRIES:
                raise IOError('File %s does not appear to exist on the server ...' % (os.path.basename(filePath)))
            elif not 'exit status 4' in str(e):
                interrupted= True
            os.remove(tmp_savefilename)
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                raise OSError("Automagically downloading catalogs requires the wget program; please install wget and try again...")
            else:
                raise
        finally:
            if os.path.exists(tmp_savefilename):
                os.remove(tmp_savefilename)
        ntries+= 1
    sys.stdout.write('\r'+_ERASESTR+'\r')
    sys.stdout.flush()        
    return None

def _download_file_vizier(cat,filePath,catalogname='catalog.dat'):
    sys.stdout.write('\r'+"Downloading file %s ...\r" \
                         % (os.path.basename(filePath)))
    sys.stdout.flush()
    try:
        # make all intermediate directories
        os.makedirs(os.path.dirname(filePath)) 
    except OSError: pass
    # Safe way of downloading
    downloading= True
    interrupted= False
    file, tmp_savefilename= tempfile.mkstemp()
    os.close(file) #Easier this way
    ntries= 1
    while downloading:
        try:
            ftp= FTP('cdsarc.u-strasbg.fr')
            ftp.login()
            ftp.cwd(os.path.join('pub','cats',cat))
            with open(tmp_savefilename,'wb') as savefile:
                ftp.retrbinary('RETR %s' % catalogname,savefile.write)
            shutil.move(tmp_savefilename,filePath)
            downloading= False
            if interrupted:
                raise KeyboardInterrupt
        except:
            raise
            if not downloading: #Assume KeyboardInterrupt
                raise
            elif ntries > _MAX_NTRIES:
                raise IOError('File %s does not appear to exist on the server ...' % (os.path.basename(filePath)))
        finally:
            if os.path.exists(tmp_savefilename):
                os.remove(tmp_savefilename)
        ntries+= 1
    sys.stdout.write('\r'+_ERASESTR+'\r')
    sys.stdout.flush()        
    return None
