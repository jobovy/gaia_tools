# Script to download the Gaia-matched 2MASS catalog from the Gaia Archive
#
# python3 -m download_tmass_best_neighbour
#
# Collapses the information in tmass_best_neighbor and tmass_original_valid 
# into a single table;
# The Gaia data is split into sets of 17 DR2 files (arranged by source_id)
# and the 2MASS data is downloaded into a similar format as the Gaia catalog 
# itself, so it can be loaded into a database in a similar way
import os, os.path
import time
import glob
import subprocess
import numpy
from astropy.io import ascii
from gaia_tools import query

# Read all GaiaSource files
gaia_source_files= glob.glob(os.path.join('gaia_source','csv',
                                          'GaiaSource_*.csv.gz'))
source_id_min= numpy.array([int(os.path.basename(f).split('.')[0]\
                                .split('_')[1])
                for f in gaia_source_files],dtype='int')
source_id_max= numpy.array([int(os.path.basename(f).split('.')[0]\
                                .split('_')[2])
                for f in gaia_source_files],dtype='int')
sort_indx= numpy.argsort(source_id_min)
source_id_min= source_id_min[sort_indx]
source_id_max= source_id_max[sort_indx]

skip= 17 # divisor of len(source_id), such that we get all
cnt= 0
for tmin,tmax in zip(source_id_min[::skip],source_id_max[skip-1::skip]):
    tmass_filename= os.path.join('tmass_best_neighbour','csv',
                                 'tmass_best_neighbour_{}_{}.csv.gz'.format(tmin,tmax))
    if os.path.exists(tmass_filename):
        continue
    print("Working on source_id between {} and {}".format(tmin,tmax))
    sql_query= """SELECT tmass_match.*, tmass.designation, tmass.ra, tmass.dec, tmass.j_m, tmass.j_msigcom, tmass.h_m, tmass.h_msigcom, tmass.ks_m, tmass.ks_msigcom, tmass.ext_key, tmass.ph_qual
FROM gaiadr2.tmass_best_neighbour AS tmass_match
INNER JOIN gaiadr1.tmass_original_valid AS tmass ON tmass.tmass_oid = tmass_match.tmass_oid
WHERE tmass_match.source_id BETWEEN {} AND {};""".format(tmin,tmax)
    while True:
        try:
            data= query.query(sql_query,use_cache=False,verbose=True)
        except:
            # Wait a while, try again ...
            time.sleep(60)
            continue
        else:
            break
    data['original_ext_source_id']= data['original_ext_source_id'].astype(str)
    data['designation']= data['ph_qual'].astype(str)
    data['ph_qual']= data['ph_qual'].astype(str)
    # Save
    ascii.write(data,tmass_filename.replace('csv.gz','csv'),delimiter=',')
    try:
        subprocess.check_call(['gzip',tmass_filename.replace('csv.gz','csv')])
    except:
        print("Failed to gzip file {}, removing it ...".format(tmass_filename))
        os.remove(tmass_filename.replace('csv.gz','csv'))
    cnt+= 1
#    if cnt > 1: break
