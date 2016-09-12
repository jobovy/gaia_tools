###############################################################################
#
#   gaia_tools.read.download: download data files automagically
#
###############################################################################
import sys
import os, os.path
import shutil
import tempfile
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
