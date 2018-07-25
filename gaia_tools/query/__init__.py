# gaia_tools.query: some helper functions for querying the Gaia database
import re
import time
import numpy
from astropy.table import Table
from astroquery.gaia import Gaia
from gaia_tools.query import cache as query_cache
query_cache.autoclean()

def query(sql_query,local=False,timeit=False,use_cache=True,verbose=False,
          dbname='catalogs',user='postgres'):
    """
    NAME:
       query
    PURPOSE:
       perform a query, either on a local server or on the Gaia archive
    INPUT:
       sql_query - the text of the query
       local= (False) if True, run the query on a local postgres database
       timeit= (False) if True, print how long the query ran
       use_cache= (True) if True use the query cache (load from the cache if exists, store to the cache for reuse otherwise)
       verbose= (False) if True, up verbosity level
       dbname= ('catalogs') if local, the name of the postgres database
       user= ('postgres') if local, the name of the postgres user
    OUTPUT:
       result
    HISTORY:
       2018-05-02 - Written - Bovy (UofT)
    """
    if local and 'gaiadr2.' in sql_query:
        sql_query= sql_query.replace('gaiadr2.','gaiadr2_')
    elif not local and 'gaiadr2_' in sql_query:
        sql_query= sql_query.replace('gaiadr2_','gaiadr2.')
    if local: # Other changes necessary for using the local database
        sql_query= _localize(sql_query)
    if use_cache:
        out= query_cache.load(sql_query)
        if out: return out
    if local:
        import psycopg2
        conn= psycopg2.connect("dbname={} user={}".format(dbname,user))
        cur= conn.cursor()
        if timeit: start= time.time()
        cur.execute(sql_query)
        if timeit: print("Query took {:.3f} s".format(time.time()-start))
        out= cur.fetchall()
        names= [desc[0] for desc in cur.description]
        cur.close()
        conn.close()       
        out= Table(numpy.array(out),names=names)
    else:
        if timeit: start= time.time()
        job= Gaia.launch_job_async(sql_query,verbose=verbose)
        if timeit: print("Query took {:.3f} s".format(time.time()-start))
        out= job.get_results()
    if use_cache:
        query_cache.save(sql_query,out)
    return out

def _localize(sql_query):
    # Figure out what the 'gaia' table is called in the query
    gaia_tablename= 'gaia'
    re_out= re.search(r"(?<=(FROM|from) gaiadr2(.|_)gaia_source AS ).*?(?=\s)",sql_query)
    try:
        gaia_tablename= re_out.group(0)
    except AttributeError: pass
    # Are we matching to 2mass?
    tmass_join_str= """INNER JOIN gaiadr2_tmass_best_neighbour AS tmass_match ON tmass_match.source_id = {}.source_id
INNER JOIN gaiadr1.tmass_original_valid AS tmass ON tmass.tmass_oid = tmass_match.tmass_oid""".format(gaia_tablename)
    if tmass_join_str in sql_query:
        sql_query= sql_query.replace(tmass_join_str,
                               """INNER JOIN gaiadr2_tmass_best_neighbour as tmass ON tmass.source_id = {}.source_id""".format(gaia_tablename))
    # Are we matching to PanSTARRS1?
    panstarrs1_join_str= """INNER JOIN gaiadr2_panstarrs1_best_neighbour AS panstarrs1_match ON panstarrs1_match.source_id = {}.source_id
INNER JOIN gaiadr2_panstarrs1_original_valid AS panstarrs1 ON panstarrs1.obj_id = panstarrs1_match.original_ext_source_id""".format(gaia_tablename)
    if panstarrs1_join_str in sql_query:
        sql_query= sql_query.replace(panstarrs1_join_str,
                               """INNER JOIN gaiadr2_panstarrs1_best_neighbour as panstarrs1 ON panstarrs1.source_id = {}.source_id""".format(gaia_tablename))
    return sql_query
