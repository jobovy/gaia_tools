# gaia_tools.query: some helper functions for querying the Gaia database
import numpy
from astropy.table import Table
from astroquery.gaia import Gaia
import psycopg2

def query(sql_query,local=False,dbname='catalogs',user='postgres'):
    """
    NAME:
       query
    PURPOSE:
       perform a query, either on a local server or on the Gaia archive
    INPUT:
       sql_query - the text of the query
    OUTPUT:
       result
    HISTORY:
       2018-05-02 - Written - Bovy (UofT)
    """
    if local and 'gaiadr2.' in sql_query:
        sql_query= sql_query.replace('gaiadr2.','gdr2_')
    elif not local and 'gdr2_' in sql_query:
        sql_query= sql_query.replace('gdr2_','gaiadr2.')
    if local:
        conn= psycopg2.connect("dbname={} user={}".format(dbname,user))
        cur= conn.cursor()
        cur.execute(sql_query)
        out= cur.fetchall()
        names= [desc[0] for desc in cur.description]
        cur.close()
        conn.close()       
        out= Table(numpy.array(out),names=names)
    else:
        job= Gaia.launch_job_async(sql_query)
        out= job.get_results()
    return out

