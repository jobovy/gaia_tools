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
from gaia_tools.load import path
_MAX_NTRIES= 2
_ERASESTR= "                                                                                "
def galah(dr=1,verbose=True,spider=False):
    filePath, ReadMePath= path.galahPath(dr=dr)
    if os.path.exists(filePath): return None
    if dr == 1:
        _download_file(\
            'https://cloudstor.aarnet.edu.au/plus/index.php/s/OMc9QWGG1koAK2D/download?path=%2F&files=catalog.dat',
            filePath,verbose=verbose,spider=spider)
        _download_file(\
            'https://cloudstor.aarnet.edu.au/plus/index.php/s/OMc9QWGG1koAK2D/download?path=%2F&files=ReadMe',
            ReadMePath,verbose=verbose,spider=spider)
    return None    
    
def rave(dr=4,verbose=True):
    filePath, ReadMePath= path.ravePath(dr=dr)
    #if os.path.exists(filePath): return None
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
    for filePath in filePaths:
        if os.path.exists(filePath): continue
        downloadPath= filePath.replace(path._GAIA_TOOLS_DATA,
                                       'http://cdn.gea.esac.esa.int')
        _download_file(downloadPath,filePath,verbose=verbose)
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
       catalogname= (catalog.dat)name of the catalog on the Vizier server
       readmename= (ReadMe) name of the ReadMe file on the Vizier server
    OUTPUT:
       (nothing, just downloads)
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
    """
    _download_file_vizier('III/272',filePath,catalogname='ravedr4.dat')
    _download_file_vizier('III/272',ReadMePath,catalogname='ReadMe')
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
