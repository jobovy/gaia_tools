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
    panstarrs1_filename= os.path.join('panstarrs1_best_neighbour','csv',
                                 'panstarrs1_best_neighbour_{}_{}.csv.gz'.format(tmin,tmax))
    if os.path.exists(panstarrs1_filename):
        continue
    print("Working on source_id between {} and {}".format(tmin,tmax))
    sql_query= """SELECT panstarrs1_match.*, panstarrs1.obj_name, panstarrs1.obj_id, panstarrs1.ra, panstarrs1.dec, panstarrs1.epoch_mean, panstarrs1.g_mean_psf_mag, panstarrs1.g_mean_psf_mag_error, panstarrs1.g_flags, panstarrs1.r_mean_psf_mag, panstarrs1.r_mean_psf_mag_error, panstarrs1.r_flags, panstarrs1.i_mean_psf_mag, panstarrs1.i_mean_psf_mag_error, panstarrs1.i_flags, panstarrs1.z_mean_psf_mag, panstarrs1.z_mean_psf_mag_error, panstarrs1.z_flags, panstarrs1.y_mean_psf_mag, panstarrs1.y_mean_psf_mag_error, panstarrs1.y_flags, panstarrs1.n_detections, panstarrs1.obj_info_flag, panstarrs1.quality_flag
FROM gaiadr2.panstarrs1_best_neighbour AS panstarrs1_match
INNER JOIN gaiadr2.panstarrs1_original_valid AS panstarrs1 ON panstarrs1.obj_id = panstarrs1_match.original_ext_source_id
WHERE panstarrs1_match.source_id BETWEEN {} AND {};""".format(tmin,tmax)
    while True:
        try:
            data= query.query(sql_query,use_cache=False,verbose=True)
        except:
            # Wait a while, try again ...
            time.sleep(60)
            continue
        else:
            break
    data['obj_name']= data['obj_name'].astype(str)
    # Save
    ascii.write(data,panstarrs1_filename.replace('csv.gz','csv'),delimiter=',')
    try:
        subprocess.check_call(['gzip',panstarrs1_filename.replace('csv.gz','csv')])
    except:
        print("Failed to gzip file {}, removing it ...".format(panstarrs1_filename))
        os.remove(panstarrs1_filename.replace('csv.gz','csv'))
    cnt+= 1
    #if cnt > 1: break
