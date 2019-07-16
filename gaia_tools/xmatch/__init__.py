# Tools for cross-matching catalogs
import csv
import sys
import os
import os.path
import platform
import shutil
import subprocess
import tempfile
import warnings

WIN32= platform.system() == 'Windows'
import numpy
import astropy.coordinates as acoords
from astropy.table import Table
from astropy import units as u

from ..load.download import _ERASESTR
def xmatch(cat1,cat2,maxdist=2,
           colRA1='RA',colDec1='DEC',epoch1=None,
           colRA2='RA',colDec2='DEC',epoch2=None,
           colpmRA2='pmra',colpmDec2='pmdec',
           swap=False,
           col_field=None):
    """
    NAME:
       xmatch
    PURPOSE:
       cross-match two catalogs (incl. proper motion in cat2 if epochs are different)
    INPUT:
       cat1 - First catalog
       cat2 - Second catalog
       maxdist= (2) maximum distance in arcsec
       colRA1= ('RA') name of the tag in cat1 with the right ascension in degree in cat1 (assumed to be ICRS)
       colDec1= ('DEC') name of the tag in cat1 with the declination in degree in cat1 (assumed to be ICRS)
       epoch1= (2000.) epoch of the coordinates in cat1
       colRA2= ('RA') name of the tag in cat2 with the right ascension in degree in cat2 (assumed to be ICRS)
       colDec2= ('DEC') name of the tag in cat2 with the declination in degree in cat2 (assumed to be ICRS)
       epoch2= (2000.) epoch of the coordinates in cat2
       colpmRA2= ('pmra') name of the tag in cat2 with the proper motion in right ascension in degree in cat2 (assumed to be ICRS; includes cos(Dec)) [only used when epochs are different]
       colpmDec2= ('pmdec') name of the tag in cat2 with the proper motion in declination in degree in cat2 (assumed to be ICRS) [only used when epochs are different]
       swap= (False) if False, find closest matches in cat2 for each cat1 source, if False do the opposite (important when one of the catalogs has duplicates)
       col_field= (None) if None, simply cross-match on RA and Dec; if a string, then cross-match on RA and Dec with additional matching in the data tag specified by the string
    OUTPUT:
       (index into cat1 of matching objects,
        index into cat2 of matching objects,
        angular separation between matching objects)
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
       2016-09-21 - Account for Gaia epoch 2015 - Bovy (UofT)
       2019-07-07 - add additional catalog field matching - Leung (UofT)
    """
    if epoch1 is None:
        if 'ref_epoch' in cat1.dtype.fields:
            epoch1= cat1['ref_epoch']
        else:
            epoch1= 2000.
    if epoch2 is None:
        if 'ref_epoch' in cat2.dtype.fields:
            epoch2= cat2['ref_epoch']
        else:
            epoch2= 2000.
    _check_epoch(cat1,epoch1)
    _check_epoch(cat2,epoch2)
    depoch= epoch2-epoch1
    if numpy.any(depoch != 0.):
        # Use proper motion to get both catalogs at the same time
        dra=cat2[colpmRA2]/numpy.cos(cat2[colDec2]/180.*numpy.pi)\
            /3600000.*depoch
        ddec= cat2[colpmDec2]/3600000.*depoch
        # Don't shift objects with non-existing proper motion
        dra[numpy.isnan(cat2[colpmRA2])]= 0.
        ddec[numpy.isnan(cat2[colpmDec2])]= 0.
    else:
        dra= 0.
        ddec= 0.
    mc1= acoords.SkyCoord(cat1[colRA1],cat1[colDec1],
                          unit=(u.degree, u.degree),frame='icrs')
    mc2= acoords.SkyCoord(cat2[colRA2]-dra,cat2[colDec2]-ddec,
                          unit=(u.degree, u.degree),frame='icrs')
    if col_field is not None:
        try:  # check if the field actually exists in both cat1/cat2
            cat1[col_field]
            cat2[col_field]
        except KeyError:  # python 2/3 format string
            raise KeyError("'%s' does not exist in both catalog" % col_field)

        uniques = numpy.unique(cat1[col_field])
        if swap:  # times neg one to indicate those indices untouch will be noticed at the end and filtered out
            d2d = numpy.ones(len(cat2)) * -1.
            idx = numpy.zeros(len(cat2), dtype=int)
        else:
            d2d = numpy.ones(len(cat1)) * -1.
            idx = numpy.zeros(len(cat1), dtype=int)

        for unique in uniques:  # loop over the class
            idx_1 = numpy.arange(cat1[colRA1].shape[0])[cat1[col_field] == unique]
            idx_2 = numpy.arange(cat2[colRA2].shape[0])[cat2[col_field] == unique]
            if idx_1.shape[0] == 0 or idx_2.shape[0] == 0:  # the case where a class only exists in one but not the other
                continue

            if swap:
                temp_idx, temp_d2d, d3d = mc2[idx_2].match_to_catalog_sky(mc1[idx_1])
                m1 = numpy.arange(len(cat2))
                idx[cat2[col_field] == unique] = idx_1[temp_idx]
                d2d[cat2[col_field] == unique] = temp_d2d
            else:
                temp_idx, temp_d2d, d3d = mc1[idx_1].match_to_catalog_sky(mc2[idx_2])
                m1 = numpy.arange(len(cat1))
                idx[cat1[col_field] == unique] = idx_2[temp_idx]
                d2d[cat1[col_field] == unique] = temp_d2d

        d2d = d2d * temp_d2d.unit  # make sure finally we have an unit on d2d array s.t. "<" operation can complete

    else:
        if swap:
            idx,d2d,d3d = mc2.match_to_catalog_sky(mc1)
            m1= numpy.arange(len(cat2))
        else:
            idx,d2d,d3d = mc1.match_to_catalog_sky(mc2)
            m1= numpy.arange(len(cat1))

    # to make sure filtering out all neg ones which are untouched
    mindx= ((d2d < maxdist*u.arcsec) & (0.*u.arcsec <= d2d))
    m1= m1[mindx]
    m2= idx[mindx]
    if swap:
        return (m2,m1,d2d[mindx])
    else:
        return (m1,m2,d2d[mindx])


def cds(cat,xcat='vizier:I/345/gaia2',maxdist=2,colRA='RA',colDec='DEC',
        selection='best',epoch=None,colpmRA='pmra',colpmDec='pmdec',
        savefilename=None,gaia_all_columns=False):
    """
    NAME:
       cds
    PURPOSE:
       Cross-match against a catalog in the CDS archive using the CDS cross-matching service (http://cdsxmatch.u-strasbg.fr/xmatch); uses the curl interface
    INPUT:
       cat - a catalog to cross match, requires 'RA' and 'DEC' keywords (see below)
       xcat= ('vizier:I/345/gaia2') name of the catalog to cross-match against, in a format understood by the CDS cross-matching service (see http://cdsxmatch.u-strasbg.fr/xmatch/doc/available-tables.html; things like 'vizier:Tycho2' or 'vizier:I/345/gaia2')
       maxdist= (2) maximum distance in arcsec
       colRA= ('RA') name of the tag in cat with the right ascension
       colDec= ('DEC') name of the tag in cat with the declination
       selection= ('best') select either all matches or the best match according to CDS (see 'selection' at http://cdsxmatch.u-strasbg.fr/xmatch/doc/API-calls.html)
       epoch= (2000.) epoch of the coordinates in cat
       colpmRA= ('pmra') name of the tag in cat with the proper motion in right ascension in degree in cat (assumed to be ICRS; includes cos(Dec)) [only used when epoch != 2000.]
       colpmDec= ('pmdec') name of the tag in cat with the proper motion in declination in degree in cat (assumed to be ICRS) [only used when epoch != 2000.]
       gaia_all_columns= (False) set to True if you are matching against Gaia DR2 and want *all* columns returned; this runs a query at the Gaia Archive, which may or may not work...
       savefilename= (None) if set, save the output from CDS to this path; can match back using cds_matchback
    OUTPUT:
       (xcat entries for those that match,
       indices into cat of matching sources: index[0] is cat index of xcat[0])
    HISTORY:
       2016-09-12 - Written based on RC catalog code - Bovy (UofT)
       2016-09-21 - Account for Gaia epoch 2015 - Bovy (UofT)
       2018-05-08 - Added gaia_all_columns - Bovy (UofT)
    """
    if epoch is None:
        if 'ref_epoch' in cat.dtype.fields:
            epoch= cat['ref_epoch']
        else:
            epoch= 2000.
    _check_epoch(cat,epoch)
    depoch= epoch-2000.
    if numpy.any(depoch != 0.):
        # Use proper motion to get both catalogs at the same time
        dra=cat[colpmRA]/numpy.cos(cat[colDec]/180.*numpy.pi)\
            /3600000.*depoch
        ddec= cat[colpmDec]/3600000.*depoch
        # Don't shift objects with non-existing proper motion
        dra[numpy.isnan(cat[colpmRA])]= 0.
        ddec[numpy.isnan(cat[colpmDec])]= 0.
    else:
        dra= numpy.zeros(len(cat))
        ddec= numpy.zeros(len(cat))
    if selection != 'all': selection= 'best'
    if selection == 'all':
        raise NotImplementedError("selection='all' CDS cross-match not currently implemented")
    # Write positions
    posfilename= tempfile.mktemp('.csv',dir=os.getcwd())
    resultfilename= tempfile.mktemp('.csv',dir=os.getcwd())
    with open(posfilename,'w') as csvfile:
        wr= csv.writer(csvfile,delimiter=',',quoting=csv.QUOTE_MINIMAL)
        wr.writerow(['RA','DEC'])
        for ii in range(len(cat)):
            wr.writerow([(cat[ii][colRA]-dra[ii]+360.) % 360.,
                          cat[ii][colDec]]-ddec[ii])
    _cds_match_batched(resultfilename,posfilename,maxdist,selection,xcat)
    # Directly match on input RA
    ma= cds_load(resultfilename)
    if gaia_all_columns:
        from astroquery.gaia import Gaia
        # Write another temporary file with the XML output of the cross-match
        tab= Table(numpy.array([ma['source_id'],ma['RA'],ma['DEC']]).T,
                   names=('source_id','RA','DEC'),
                   dtype=('int64','float64','float64'))
        xmlfilename= tempfile.mktemp('.xml',dir=os.getcwd())
        tab.write(xmlfilename,format='votable')
        try:
            job= Gaia.launch_job_async(
                """select g.*, m.RA as mRA, m.DEC as mDEC
from gaiadr2.gaia_source as g 
inner join tap_upload.my_table as m on m.source_id = g.source_id""",
                                       upload_resource=xmlfilename,
                                       upload_table_name="my_table")
            ma= job.get_results()
        except:
            print("gaia_tools.xmath.cds failed to retrieve all gaiadr2 columns, returning just the default returned by the CDS xMatch instead...")
        else:
            ma.rename_column('mra','RA')
            ma.rename_column('mdec','DEC')
        finally:
            os.remove(xmlfilename)
    # Remove temporary files
    os.remove(posfilename)
    if savefilename is None:
        os.remove(resultfilename)
    else:
        shutil.move(resultfilename,savefilename)
    # Match back to the original catalog
    mai= cds_matchback(cat,ma,colRA=colRA,colDec=colDec,epoch=epoch,
                       colpmRA=colpmRA,colpmDec=colpmDec)
    return (ma,mai)

def _cds_match_batched(resultfilename,posfilename,maxdist,selection,xcat,
                       nruns_necessary=1):
    """CDS xMatch (sometimes?) fails for large matches, because of a time-out,
    so we recursively split until the batches are small enough to not fail"""
    # Figure out which of the hierarchy we are running
    try:
        runs= ''.join([str(int(r)-1)
                       for r in posfilename.split('csv.')[-1].split('.')])
    except ValueError:
        runs= ''
    nruns= 2**len(runs)
    if nruns >= nruns_necessary:
        # Only run this level's match if we don't already know that we should
        # be using smaller batches
        _cds_basic_match(resultfilename,posfilename,maxdist,selection,xcat)
        try:
            ma= cds_load(resultfilename)
        except ValueError: # Assume this is the time-out failure
            pass
        else:
            return nruns
    # xMatch failed because of time-out, split
    posfilename1= posfilename+'.1'
    posfilename2= posfilename+'.2'
    resultfilename1= resultfilename+'.1'
    resultfilename2= resultfilename+'.2'
    # Figure out which of the hierarchy we are running
    runs= ''.join([str(int(r)-1)
                   for r in posfilename1.split('csv.')[-1].split('.')])
    nruns= 2**len(runs)
    thisrun1= 1+int(runs,2)
    thisrun2= 1+int(''.join([str(int(r)-1)
                   for r in posfilename2.split('csv.')[-1].split('.')]),2)
    # Count the number of objects
    with open(posfilename,'r') as posfile:
        num_lines= sum(1 for line in posfile)
    # Write the header line
    with open(posfilename1,'w') as posfile1:
        with open(posfilename,'r') as posfile:
            posfile1.write(posfile.readline())
    with open(posfilename2,'w') as posfile2:
        with open(posfilename,'r') as posfile:
            posfile2.write(posfile.readline())
    # Cut in half
    cnt= 0
    with open(posfilename,'r') as posfile:
        with open(posfilename1,'a') as posfile1:
            with open(posfilename2,'a') as posfile2:
                for line in posfile:
                    if cnt == 0:
                        cnt+= 1
                        continue
                    if cnt < num_lines//2:
                        posfile1.write(line)
                        cnt+= 1 # Can stop counting once this if is done
                    else:
                        posfile2.write(line)
    # Run each
    sys.stdout.write('\r'+"Working on CDS xMatch batch {} / {} ...\r"\
                     .format(thisrun1,nruns))
    sys.stdout.flush()
    nruns_necessary= _cds_match_batched(resultfilename1,posfilename1,
                                        maxdist,selection,xcat,
                                        nruns_necessary=nruns_necessary)
    sys.stdout.write('\r'+"Working on CDS xMatch batch {} / {} ...\r"\
                     .format(thisrun2,nruns))
    sys.stdout.flush()
    nruns_necessary= _cds_match_batched(resultfilename2,posfilename2,
                                        maxdist,selection,xcat,
                                        nruns_necessary=nruns_necessary)
    sys.stdout.write('\r'+_ERASESTR+'\r')
    sys.stdout.flush()
    # Combine results
    with open(resultfilename,'w') as resultfile:
        with open(resultfilename1,'r') as resultfile1:
            for line in resultfile1:
                resultfile.write(line)
        with open(resultfilename2,'r') as resultfile2:
            for line in resultfile2:
                if line[0] == 'a': continue
                resultfile.write(line)
    # Remove intermediate files
    os.remove(posfilename1)
    os.remove(posfilename2)
    os.remove(resultfilename1)
    os.remove(resultfilename2)
    return nruns_necessary

def _cds_basic_match(resultfilename,posfilename,maxdist,selection,xcat):
    # Send to CDS for matching
    result= open(resultfilename,'w')
    try:
        subprocess.check_call(['curl',
                               '-X','POST',
                               '-F','request=xmatch',
                               '-F','distMaxArcsec=%i' % maxdist,
                               '-F','selection=%s' % selection,
                               '-F','RESPONSEFORMAT=csv',
                               '-F','cat1=@%s' % os.path.basename(posfilename),
                               '-F','colRA1=RA',
                               '-F','colDec1=DEC',
                               '-F','cat2=%s' % xcat,
                               'http://cdsxmatch.u-strasbg.fr/xmatch/api/v1/sync'],
                              stdout=result)
    except subprocess.CalledProcessError:
        os.remove(posfilename)
        if os.path.exists(resultfilename):
            result.close()
            os.remove(resultfilename)
    result.close()
    return None

def cds_load(filename):
    if WIN32:
        # windows do not have float128, but source_id is double
        # get around this by squeezing precision from int64 on source_id as source_id is always integer anyway
        # first read everything as fp64 and then convert source_id to int64 will keep its precision
        data = numpy.genfromtxt(filename, delimiter=',', skip_header=0,
                                filling_values=-9999.99, names=True, max_rows=1,
                                dtype='float64')  # only read the first row max to reduce workload to just get the column name
        to_list = list(data.dtype.names)
        # construct a list where everything is fp64 except 'source_id' being int64
        dtype_list = [('{}'.format(i), numpy.float64) for i in to_list]
        dtype_list[dtype_list.index(('source_id', numpy.float64))] = ('source_id', numpy.uint64)

        return numpy.genfromtxt(filename, delimiter=',', skip_header=0,
                                filling_values=-9999.99, names=True,
                                dtype=dtype_list)
    else:
        return numpy.genfromtxt(filename, delimiter=',', skip_header=0,
                                filling_values=-9999.99, names=True,
                                dtype='float128')

def cds_matchback(cat,xcat,colRA='RA',colDec='DEC',selection='best',
                  epoch=None,colpmRA='pmra',colpmDec='pmdec',):
    """
    NAME:
       cds_matchback
    PURPOSE:
       Match a matched catalog from xmatch.cds back to the original catalog
    INPUT
       cat - original catalog
       xcat - matched catalog returned by xmatch.cds
       colRA= ('RA') name of the tag in cat with the right ascension
       colDec= ('DEC') name of the tag in cat with the declination
       selection= ('best') select either all matches or the best match according to CDS (see 'selection' at http://cdsxmatch.u-strasbg.fr/xmatch/doc/API-calls.html)
       epoch= (2000.) epoch of the coordinates in cat
       colpmRA= ('pmra') name of the tag in cat with the proper motion in right ascension in degree in cat (assumed to be ICRS; includes cos(Dec)) [only used when epoch != 2000.]
       colpmDec= ('pmdec') name of the tag in cat with the proper motion in declination in degree in cat (assumed to be ICRS) [only used when epoch != 2000.]
    OUTPUT:
       Array indices into cat of xcat entries: index[0] is cat index of xcat[0]
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
       2018-05-04 - Account for non-zero epoch difference - Bovy (UofT)
    """
    if selection != 'all': selection= 'best'
    if selection == 'all':
        raise NotImplementedError("selection='all' CDS cross-match not currently implemented")
    if epoch is None:
        if 'ref_epoch' in cat.dtype.fields:
            epoch= cat['ref_epoch']
        else:
            epoch= 2000.
    _check_epoch(cat,epoch)
    depoch= epoch-2000.
    if numpy.any(depoch != 0.):
        # Use proper motion to get both catalogs at the same time
        dra=cat[colpmRA]/numpy.cos(cat[colDec]/180.*numpy.pi)\
            /3600000.*depoch
        ddec= cat[colpmDec]/3600000.*depoch
        # Don't shift objects with non-existing proper motion
        dra[numpy.isnan(cat[colpmRA])]= 0.
        ddec[numpy.isnan(cat[colpmDec])]= 0.
    else:
        dra= numpy.zeros(len(cat))
        ddec= numpy.zeros(len(cat))
    # xmatch to v. small diff., because match is against *original* coords, 
    # not matched coords in CDS
    mc1= acoords.SkyCoord(cat[colRA]-dra,cat[colDec]-ddec,
                          unit=(u.degree, u.degree),frame='icrs')
    mc2= acoords.SkyCoord(xcat['RA'],xcat['DEC'],
                          unit=(u.degree, u.degree),frame='icrs')
    idx,d2d,d3d = mc2.match_to_catalog_sky(mc1)
    mindx= d2d < 1e-5*u.arcsec
    return idx[mindx]

def _check_epoch(cat,epoch):
    warn_about_epoch= False
    if 'ref_epoch' in cat.dtype.fields:
        if 'designation' not in cat.dtype.fields: # Assume this is DR1
            if numpy.any(numpy.fabs(epoch-2015.) > 0.01):
                warn_about_epoch= True
        elif 'Gaia DR2' in cat['designation'][0].decode('utf-8'):
            if numpy.any(numpy.fabs(epoch-2015.5) > 0.01):
                warn_about_epoch= True
    if warn_about_epoch:
        warnings.warn("You appear to be using a Gaia catalog, but are not setting the epoch to 2015. (DR1) or 2015.5 (DR2), which may lead to incorrect matches")
    return None
