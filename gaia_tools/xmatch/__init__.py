# Tools for cross-matching catalogs
import os, os.path
import csv
import shutil
import tempfile
import subprocess
import numpy
import astropy.coordinates as acoords
from astropy import units as u
def xmatch(cat1,cat2,maxdist=2,
           colRA1='RA',colDec1='DEC',
           colRA2='RA',colDec2='DEC'):
    """
    NAME:
       xmatch
    PURPOSE:
       cross-match two catalogs
    INPUT:
       cat1 - First catalog
       cat2 - Second catalog
       maxdist= (2) maximum distance in arcsec
       colRA1= ('RA') name of the tag in cat with the right ascension in cat1
       colDec1= ('DEC') name of the tag in cat with the declination in cat1
       colRA2= ('RA') name of the tag in cat with the right ascension in cat2
       colDec2= ('DEC') name of the tag in cat with the declination in cat2
    OUTPUT:
       (index into cat1 of matching objects,
        index into cat2 of matching objects,
        angular separation between matching objects)
    HISTORY:
       2016-09-12 - Written - Bovy (UofT)
    """
    mc1= acoords.ICRS(cat1[colRA1],cat1[colDec1],unit=(u.degree, u.degree))
    mc2= acoords.ICRS(cat2[colRA2],cat2[colDec2],unit=(u.degree, u.degree))
    idx,d2d,d3d = mc1.match_to_catalog_sky(mc2)
    m1= numpy.arange(len(cat1))
    mindx= d2d < maxdist*u.arcsec
    m1= m1[mindx]
    m2= idx[mindx]
    return (m1,m2,d2d[mindx])

def cds(cat,xcat='vizier:Tycho2',maxdist=2,colRA='RA',colDec='DEC',
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
       savefilename= (None) if set, save the output from CDS to this path; can match back using cds_matchback
    OUTPUT:
       (xcat entries for those that match,
       indices into cat of matching sources: index[0] is cat index of xcat[0])
    HISTORY:
       2016-09-12 - Written based on RC catalog code - Bovy (UofT)
    """
    # Write positions
    posfilename= tempfile.mktemp('.csv',dir=os.getcwd())
    resultfilename= tempfile.mktemp('.csv',dir=os.getcwd())
    with open(posfilename,'w') as csvfile:
        wr= csv.writer(csvfile,delimiter=',',quoting=csv.QUOTE_MINIMAL)
        wr.writerow(['RA','DEC'])
        for ii in range(len(cat)):
            wr.writerow([cat[ii][colRA],cat[ii][colDec]])
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
