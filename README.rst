gaia_tools
-----------

Tools for working with the `ESA/Gaia <http://sci.esa.int/gaia/>`__
data and related data sets (`APOGEE
<http://www.sdss.org/surveys/apogee/>`__, `GALAH
<https://galah-survey.org/>`__, and `RAVE
<https://www.rave-survey.org/project/>`__).

.. contents::

AUTHORS
========

 * Jo Bovy - bovy at astro dot utoronto dot ca
 * You!

ACKNOWLEDGING USE OF THIS CODE
==============================

Please refer back to this repository when using this code in your
work.

INSTALLATION
============

Standard python setup.py build/install

Either

``sudo python setup.py install``

or 

``python setup.py install --prefix=/some/directory/``

DEPENDENCIES AND PYTHON VERSIONS
=================================

This package requires `NumPy <http://www.numpy.org/>`__ and `astropy
<http://www.astropy.org/>`__. Some functions require `Scipy
<http://www.scipy.org/>`__ and the `apogee
<https://github.com/jobovy/apogee>`__ package. 

This package should work in both python 2 and 3. Please open an `issue
<https://github.com/jobovy/gaia_tools/issues>`__ if you find a part of the
code that does not support python 3.

DATA FILES AND ENVIRONMENT VARIABLES
=====================================

This code will download and store various data files. The top-level
location of where these are stored is set by the **GAIA_TOOLS_DATA**
environment variable, which is the path of the top-level directory
under which the data will be stored. To use the `apogee
<https://github.com/jobovy/apogee>`__ functionality, you also need to
set the environment variables appropriate for that package.

BASIC USE
==========

Catalog reading and cross-matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The basic use of the code is to read various data files and match them
to each other. For example, to load the data for the `GALAH
<https://galah-survey.org/>`__ survey's DR1, do::

    import gaia_tools.load as gload
    galah_cat= gload.galah()

The first time you use this function, it will download the GALAH data
and return the catalog (the data is stored locally, so downloading
only happens once).

Through an interface to the more detailed `apogee
<https://github.com/jobovy/apogee>`__ package, you can also load
various APOGEE data files, for example::

	apogee_cat= gload.apogee()
	rc_cat= gload.apogeerc()

Similarly, you can load the `RAVE
<https://www.rave-survey.org/project/>`__ data as::

	rave_cat= gload.rave()

To match catalogs to each other, use the tools in
``gaia_tools.xmatch``. For example, to match the GALAH and APOGEE-RC
catalogs loaded above and compare the effective temperatures for the
stars in common, you can do::

	 from gaia_tools import xmatch
	 m1,m2,sep= xmatch.xmatch(rc_cat,galah_cat,colDec2='dec')
	 print(rc_cat[m1]['TEFF']-galah_cat[m2]['Teff'])
	      Teff     
	      K       
	 --------------
	 -12.3999023438
	  0.39990234375

which matches objects using their celestial coordinates using the
default maximum separation of 2 arcsec.

Further, it is possible to cross-match any catalog to the catalogs in
the CDS database using the `CDS cross-matching service
<http://cdsxmatch.u-strasbg.fr/xmatch>`__. For example, to match the
GALAH catalog to the Tycho-2 catalog, do the following::

   tyc2_matches, matches_indx= xmatch.cds(galah_cat,colDec='dec',xcat='vizier:Tycho2')
   print(galah_cat['RA'][matches_indx[0]],tyc2_matches['RA_1'][0],tyc2_matches['pmRA'][matches_indx[0]],tyc2_matches['pmDE'][matches_indx[0]])
   ('209.8838244', 209.88408100000001, -23.100000000000001, -10.699999999999999)

Let's see how these proper motions hold up in Gaia DR1! If you want to
download a catalog from CDS, you can use
``gaia_tools.load.download.vizier``.


API
====

(May or may not be fully up-to-date)

 * ``gaia_tools.load``
     * ``gaia_tools.load.apogee``
     * ``gaia_tools.load.apogeerc``
     * ``gaia_tools.load.galah``
     * ``gaia_tools.load.rave``
         * ``gaia_tools.load.download.vizier``
 * ``gaia_tools.xmatch``
     * ``gaia_tools.xmatch.xmatch``
     * ``gaia_tools.xmatch.cds``
     * ``gaia_tools.xmatch.cds_matchback``
