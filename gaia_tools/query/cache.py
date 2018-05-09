# gaia_tools.query.cache: tools for caching the results from queries
import os, os.path
import datetime
import glob
import hashlib
import pickle
import dateutil.parser
from gaia_tools.util import save_pickles

_CACHE_DIR= os.path.join(os.path.expanduser('~'),'.gaia_tools','query_cache')
if not os.path.exists(_CACHE_DIR):
    os.makedirs(_CACHE_DIR)

def current_files():
    """
    NAME:
       current_files
    PURPOSE:
       return the current set of files in the cache
    INPUT:
       (none)
    OUTPUT:
       full path, either of existing file or a new path
    HISTORY:
       2018-05-04 - Written - Bovy (UofT)
    """
    return glob.glob(os.path.join(_CACHE_DIR,'*.pkl'))

def file_path(sql_query):
    """
    NAME:
       file_path
    PURPOSE:
       return the file path in the cache corresponding to the query
    INPUT:
       sql_query - the text of the query
    OUTPUT:
       full path, either of existing file or a new path
    HISTORY:
       2018-05-04 - Written - Bovy (UofT)
    """
    thash= hashlib.md5(sql_query.encode('utf-8')).hexdigest()
    all_current_files= current_files()
    for existing_file in all_current_files:
        if thash in existing_file: return existing_file
    return os.path.join(_CACHE_DIR,'{}_{}.pkl'\
                        .format(datetime.datetime.today().isoformat(),thash))

def save(sql_query,results):
    """
    NAME:
       save
    PURPOSE:
       save the results of a query in the cache
    INPUT:
       sql_query - the text of the query
       results - the results of the query
    OUTPUT:
       (none, just stores)
    HISTORY:
       2018-05-04 - Written - Bovy (UofT)
    """
    save_pickles(file_path(sql_query),results)

def load(sql_query):
    """
    NAME:
       load
    PURPOSE:
       load the results of a query in the cache
    INPUT:
       sql_query - the text of the query
    OUTPUT:
       results from the query or False if the query does not exist in the cache
    HISTORY:
       2018-05-04 - Written - Bovy (UofT)
    """
    thash= hashlib.md5(sql_query.encode('utf-8')).hexdigest()
    all_current_files= current_files()
    for existing_file in all_current_files:
        if thash in existing_file:
            with open(existing_file,'rb') as savefile:
                results= pickle.load(savefile)
            return results
    return False

def cleanall():
    return clean(all=True)
def autoclean():
    return clean(auto=True)
def clean(all=False,auto=False):
    """
    NAME:
       clean
    PURPOSE:
       clean out the cache: removes all cached files that follow the standard datetime_hash.pkl filename format; renamed files will be retained
    INPUT:
       all= (False) if True, remove *all* cached files (including renamed ones)
       auto= (False) if True, autoclean (remove all files in standard format more than one week old; all=True still removes all files)
    OUTPUT:
       (none)
    HISTORY:
       2018-05-04 - Written - Bovy (UofT)
       2018-05-06 - Added all and auto options - Bovy (UofT)
    """
    one_week_ago= datetime.datetime.now()-datetime.timedelta(days=7)
    all_current_files= current_files()
    for existing_file in all_current_files:
        if all:
            os.remove(existing_file)
            continue
        try:
            tdate,thashpkl= os.path.basename(existing_file).split('_')
            tdate= dateutil.parser.parse(tdate)
            if auto and tdate > one_week_ago: continue
        except: continue
        thash,pkl= thashpkl.split('.')
        if not len(thash) == 32 or not pkl == 'pkl': continue
        os.remove(existing_file)
    return None
