# Script to sniff whether DR2 has appeared and grab everything once it appears
import os
import time
from datetime import datetime, timedelta
import pytz
import subprocess
import hashlib

_DR2_URL= 'http://cdn.gea.esac.esa.int/Gaia/gdr2/'
_MD5_FILENAME= 'MD5SUM.txt'

_CEST= pytz.timezone('Europe/Brussels')
_TIME_START_CHECKING= _CEST.localize(datetime(2018,4,25,11,55,0))
_TIME_START_CHECKING_MORE= _CEST.localize(datetime(2018,4,25,11,59,30))
_DT_UNTIL_DOWNLOAD_ALL= 10*60 # seconds
_MAX_DOWNLOAD_TRIES= 50 # don't try to download and fail more than this
_CUT_DIRS= 2
download_tries= 0
_VERBOSE= True
_HOLD_OFF_UNTIL_SOON_BEFORE= True

def dr2_available(dr2_url=_DR2_URL):
    try:
        cmd= 'curl -s --head %s | head -n 1 | grep "HTTP/1.[01] [23].." >/dev/null' % (dr2_url)
        output= os.system(cmd)
        return not bool(int(output))
    except:
        return False

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

while True:
    # Only start checking soon before the official release date, sleep until
    if _HOLD_OFF_UNTIL_SOON_BEFORE:
        if datetime.now(_CEST) < _TIME_START_CHECKING:
            print("Waiting to start checking; current time CEST:",
                  datetime.now(_CEST))
            time.sleep(10)
            continue
    # Then check whether the data is available
    if _VERBOSE: print("DR2 available?",dr2_available(_DR2_URL))
    if not dr2_available(_DR2_URL):
        if datetime.now(_CEST) < _TIME_START_CHECKING_MORE:
            time.sleep(30)
        else:
            time.sleep(5)
            # If nothing seems to appear, switch to just really grabbing all
            if datetime.now(_CEST) > (_TIME_START_CHECKING_MORE\
                                      +timedelta(0,_DT_UNTIL_DOWNLOAD_ALL)):
                os.chdir('../')
                _DR2_URL= 'http://cdn.gea.esac.esa.int/Gaia/'
                _CUT_DIRS= 1
        continue
    # Once it's available, start grabbing it
    try:
        subprocess.check_call(['wget','-r','-nH','-nc',
                               '--cut-dirs=%i' % _CUT_DIRS,
                               '--no-parent',
                               '--reject="index.html*",vot.gz',
                               _DR2_URL])
    except: # Any issue, just try again 10 seconds later
        time.sleep(10)
        download_tries+= 1
        if download_tries > _MAX_DOWNLOAD_TRIES: break
        else: continue
    # Once we think we've downloaded it all, go into directories and check MD5
    all_dirs= [x[0] for x in os.walk('./')]
    all_dirs.append('./') # Just to make sure we check the main dir...
    _CONTINUE= False
    for dir in all_dirs:       
        if 'votable' in dir or 'vo' in dir: continue
        if _VERBOSE: print("Checking directory %s" % (dir))
        if not os.path.exists(os.path.join(dir,_MD5_FILENAME)):
            continue
        with open(os.path.join(dir,_MD5_FILENAME),'r') as md5file:
            for line in md5file:
                target_hash,tfile= line.split()
                if not os.path.exists(os.path.join(dir,tfile)): continue
                current_hash= md5(os.path.join(dir,tfile))
                if _VERBOSE:
                    print("md5sums of file %s:" % tfile)
                    print("%s" % target_hash)
                    print("%s" % current_hash)
                if target_hash.strip() != current_hash:
                    print('MD5 does not match for %s' % tfile)
                    # Remove the file
                    os.remove(os.path.join(dir,tfile))
                    _CONTINUE= True
    if _CONTINUE: continue
    else: break
