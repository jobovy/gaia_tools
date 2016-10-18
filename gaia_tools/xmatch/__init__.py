# Tools for cross-matching catalogs
import os, os.path
import csv
import shutil
import tempfile
import warnings
import subprocess
import numpy
import astropy.coordinates as acoords
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

def cds(cat,xcat='vizier:Tycho2',maxdist=2,colRA='RA',colDec='DEC',
        epoch=2000.,colpmRA='pmra',colpmDec='pmdec',
        savefilename=None):
    """
    NAME:
       cds
    PURPOSE:
       Cross-match against a catalog in the CDS archive using the CDS cross-matching service (http://cdsxmatch.u-strasbg.fr/xmatch); uses the curl interface
    INPUT:
       cat - a catalog to cross match, requires 'RA' and 'DEC' keywords (see below)
       xcat= ('vizier:Tycho2') name of the catalog to cross-match against, in a format understood by the CDS cross-matching service (see http://cdsxmatch.u-strasbg.fr/xmatch/doc/available-tables.html)
       maxdist= (2) maximum distance in arcsec
       colRA= ('RA') name of the tag in cat with the right ascension
       colDec= ('DEC') name of the tag in cat with the declination
       epoch= (2000.) epoch of the coordinates in cat
       colpmRA= ('pmra') name of the tag in cat with the proper motion in right ascension in degree in cat (assumed to be ICRS; includes cos(Dec)) [only used when epoch != 2000.]
       colpmDec= ('pmdec') name of the tag in cat with the proper motion in declination in degree in cat (assumed to be ICRS) [only used when epoch != 2000.]
       savefilename= (None) if set, save the output from CDS to this path; can match back using cds_matchback
    OUTPUT:
       (xcat entries for those that match,
       indices into cat of matching sources: index[0] is cat index of xcat[0])
    HISTORY:
       2016-09-12 - Written based on RC catalog code - Bovy (UofT)
       2016-09-21 - Account for Gaia epoch 2015 - Bovy (UofT)
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
        dra= 0.
        ddec= 0.
    # Write positions
    posfilename= tempfile.mktemp('.csv',dir=os.getcwd())
    resultfilename= tempfile.mktemp('.csv',dir=os.getcwd())
    with open(posfilename,'w') as csvfile:
        wr= csv.writer(csvfile,delimiter=',',quoting=csv.QUOTE_MINIMAL)
        wr.writerow(['RA','DEC'])
        for ii in range(len(cat)):
            wr.writerow([cat[ii][colRA]-dra[ii],cat[ii][colDec]]-ddec[ii])
    # Send to CDS for matching
    result= open(resultfilename,'w')
    try:
        subprocess.check_call(['curl',
                               '-X','POST',
                               '-F','request=xmatch',
                               '-F','distMaxArcsec=%i' % maxdist,
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
    # Remove temporary files
    os.remove(posfilename)
    if savefilename is None:
        os.remove(resultfilename)
    else:
        shutil.move(resultfilename,savefilename)
    # Match back to the original catalog
    mai= cds_matchback(cat,ma,colRA=colRA)
    return (ma,mai)

def cds_load(filename):
    return numpy.genfromtxt(filename,delimiter=',',skip_header=0,
                            filling_values=-9999.99,names=True)

def cds_matchback(cat,xcat,colRA='RA'):
    """
    NAME:
       cds_matchback
    PURPOSE:
       Match a matched catalog from xmatch.cds back to the original catalog
    INPUT
       cat - original catalog
       xcat - matched catalog returned by xmatch.cds
       colRA - the column with the RA tag in cat
    OUTPUT:
       Array indices into cat of xcat entries: index[0] is cat index of xcat[0]
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
    """
    iis= numpy.arange(len(cat))
    RAf= cat[colRA].astype('float') # necessary if not float, like for GALAH
    mai= [iis[RAf == xcat[ii]['RA']][0] for ii in range(len(xcat))]
    return mai
