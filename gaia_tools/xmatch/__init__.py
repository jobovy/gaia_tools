# Tools for cross-matching catalogs
import os, os.path
import csv
import shutil
import tempfile
import warnings
import subprocess
import numpy
import astropy.coordinates as acoords
from astropy.table import Table
from astropy import units as u

def xmatch(cat1,cat2,maxdist=2,
           colRA1='RA',colDec1='DEC',epoch1=2000.,
           colRA2='RA',colDec2='DEC',epoch2=2000.,
           colpmRA2='pmra',colpmDec2='pmdec',
           swap=False):
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
    OUTPUT:
       (index into cat1 of matching objects,
        index into cat2 of matching objects,
        angular separation between matching objects)
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
       2016-09-21 - Account for Gaia epoch 2015 - Bovy (UofT)
    """
    if ('ref_epoch' in cat1.dtype.fields and numpy.fabs(epoch1-2015.) > 0.01)\
            or ('ref_epoch' in cat2.dtype.fields and \
                    numpy.fabs(epoch2-2015.) > 0.01):
        warnings.warn("You appear to be using a Gaia catalog, but are not setting the epoch to 2015., which may lead to incorrect matches")
    depoch= epoch2-epoch1
    if depoch != 0.:
        # Use proper motion to get both catalogs at the same time
        dra=cat2[colpmRA2]/numpy.cos(cat2[colDec2]/180.*numpy.pi)\
            /3600000.*depoch
        ddec= cat2[colpmDec2]/3600000.*depoch
    else:
        dra= 0.
        ddec= 0.
    mc1= acoords.SkyCoord(cat1[colRA1],cat1[colDec1],
                          unit=(u.degree, u.degree),frame='icrs')
    mc2= acoords.SkyCoord(cat2[colRA2]-dra,cat2[colDec2]-ddec,
                          unit=(u.degree, u.degree),frame='icrs')
    if swap:
        idx,d2d,d3d = mc2.match_to_catalog_sky(mc1)
        m1= numpy.arange(len(cat2))
    else:
        idx,d2d,d3d = mc1.match_to_catalog_sky(mc2)
        m1= numpy.arange(len(cat1))
    mindx= d2d < maxdist*u.arcsec
    m1= m1[mindx]
    m2= idx[mindx]
    if swap:
        return (m2,m1,d2d[mindx])
    else:
        return (m1,m2,d2d[mindx])

def cds(cat,xcat='vizier:I/345/gaia2',maxdist=2,colRA='RA',colDec='DEC',
        selection='best',epoch=2000.,colpmRA='pmra',colpmDec='pmdec',
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
    if 'ref_epoch' in cat.dtype.fields and numpy.fabs(epoch-2015.) > 0.01:
        warnings.warn("You appear to be using a Gaia catalog, but are not setting the epoch to 2015., which may lead to incorrect matches")
    depoch= epoch-2000.
    if depoch != 0.:
        # Use proper motion to get both catalogs at the same time
        dra=cat[colpmRA]/numpy.cos(cat[colDec]/180.*numpy.pi)\
            /3600000.*depoch
        ddec= cat[colpmDec]/3600000.*depoch
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
            ma.rename_column('mRA','RA')
            ma.rename_column('mDEC','DEC')
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

def cds_load(filename):
    return numpy.genfromtxt(filename,delimiter=',',skip_header=0,
                            filling_values=-9999.99,names=True,
                            dtype='float128')

def cds_matchback(cat,xcat,colRA='RA',colDec='DEC',selection='best',
                  epoch=2000.,colpmRA='pmra',colpmDec='pmdec',):
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
    if 'ref_epoch' in cat.dtype.fields and numpy.fabs(epoch-2015.) > 0.01:
        warnings.warn("You appear to be using a Gaia catalog, but are not setting the epoch to 2015., which may lead to incorrect matches")
    depoch= epoch-2000.
    if depoch != 0.:
        # Use proper motion to get both catalogs at the same time
        dra=cat[colpmRA]/numpy.cos(cat[colDec]/180.*numpy.pi)\
            /3600000.*depoch
        ddec= cat[colpmDec]/3600000.*depoch
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
