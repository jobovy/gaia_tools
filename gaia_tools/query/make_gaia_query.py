#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
r"""

    gaia_tools helper functions
    Make constructing SQL queries for gaia_tools easier
    See gaia_tools python package by Jo Bovy for details

#############################################################################

Copyright (c) 2018 - Nathaniel Starkman
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

  Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.
  Redistributions in binary form must reproduce the above copyright notice,
     this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.
  The name of the author may not be used to endorse or promote products
     derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

#############################################################################
"""

#############################################################################
# Imports

import json
import os
import time

# 3rd Party Packages
from astropy.table import Table, QTable
from astropy import units as u

# Custom Packages
from . import query as Query
from . import cache as Cache
from ..util.table_utils import add_units_to_Table

#############################################################################
# Info

__author__ = "Nathaniel Starkman"
__copyright__ = "Copyright 2018, "
__credits__ = ["Jo Bovy"]
__license__ = "MIT"
__version__ = "2.0.0"
__maintainer__ = "Nathaniel Starkman"
__email__ = "n.starkman@mail.utoronto.ca"
__status__ = "Production"


#############################################################################
# Code


def _make_query_defaults(fpath='default'):
    r"""Make default values for query
    loads from file or dictionary

    INPUTS
    ------
    fpath: str or dict
        the filepath of the gaia query defaults
        if
            None: uses 'defaults'
            str: 'default', 'empty', or 'full'
            dict, assumes the dictionary is correct and returns as is
        default file in  '/gaia/defaults.json'

    Dictionary Values
    -----------------
    gaia cols
    gaia mags
    panstarrs cols
    asdict
    units
    """

    # dictionary
    if issubclass(fpath.__class__, dict):  # prefers a dictionary
        return fpath

    elif not isinstance(fpath, str):  # must be a string, if not a dict
        raise ValueError('defaults must be a str')

    # loading file
    elif fpath in ('default', 'empty', 'full'):
        dirname = os.path.dirname(__file__)
        dirpath = os.path.join(dirname, 'defaults/gaia_defaults.json')

        with open(dirpath, 'r') as file:
            df = json.load(file)

        # the dictionary needs to be flattened
        defaults = {
            'asdict': df['asdict'],
            'units': df['units'],
            **df[fpath]  # selecting the particular default option
        }

    # user file
    else:
        with open(fpath, 'r') as file:
            defaults = json.load(file)

    # Checking possible column groups
    if 'gaia cols' in defaults:
        defaults['gaia cols'] = "\n".join(defaults['gaia cols'])

    if 'gaia mags' in defaults:
        defaults['gaia mags'] = "\n".join(defaults['gaia mags'])

    if 'Pan-STARRS1 cols' in defaults:
        defaults['Pan-STARRS1 cols'] = "\n".join(defaults['Pan-STARRS1 cols'])

    if '2MASS cols' in defaults:
        defaults['2MASS cols'] = "\n".join(defaults['2MASS cols'])

    if 'units' in defaults:
        defaults['units'] = {k: eval(v) for k, v in defaults['units'].items()
                             if v[:2] == 'u.'}

    return defaults
# /def


def _make_query_SELECT(user_cols=None, use_AS=True,
                       all_columns=False, gaia_mags=False,
                       panstarrs1=False, twomass=False,
                       query=None, defaults='default'):
    r"""Makes the SELECT portion of a gaia query

    Inputs
    ------
    user_cols: str (or None)
        Data columns in addition to default columns
        Default: None
        ex: "gaia.L, gaia.B,"
    use_AS: bool
        True will add 'AS __' to the data columns
        This is good for the outer part of the query
        so as to have convenient names in the output data table.
        Default: True
    all_columns: bool
        Whether to include all columns
        via ', *'
        Default: False
    gaia_mags: bool
        Whether to include Gaia magnitudes
        Default: False
    panstarrs1: bool
        to include Pan-STARRS1 magnitudes and INNER JOIN on Gaia
        Default: False
    twomass: bool
        to include 2MASS magnitudes and INNER JOIN on Gaia
        Default: False
    query: str (or None)
        experimental feature
    defaults: str or dict
        the filepath of the gaia query defaults
        if
            None: uses 'defaults'
            str: 'default', 'empty', or 'full'
            dict, assumes the dictionary is correct and returns as is
        default file in  'defaults/gaia_defaults.json'

    Returns
    -------
    query: str
        the SELECT portion of a gaia query

    DEFAULTS
    --------
    In a Json-esque format.
    See defaults/gaia_defaults.json
    """

    ####################
    # Defaults

    defaults = _make_query_defaults(defaults)

    if use_AS is False:  # replace with blank dict with asdict keys
        defaults['asdict'] = {k: '' for k in defaults['asdict']}
    else:
        for k, v in defaults['asdict'].items():
            if not v:  # empty
                defaults['asdict'][k] = ''
            else:
                defaults['asdict'][k] = ' AS ' + v

    # Start new query if one not provided
    if query is None:
        query = ""

    ####################
    # Building Selection

    # SELECT
    query += '--Data Columns:\nSELECT\n--GaiaDR2 Columns:\n'
    query += defaults['gaia cols']

    if gaia_mags is True:
        query += ',\n--GaiaDR2 Magnitudes and Colors:\n'
        query += defaults['gaia mags']

    if all_columns is True:
        query += ",\n--All Columns:\n*"

    if panstarrs1 is True:
        query += ',\n--Adding Pan-STARRS1 Columns:\n'
        query += defaults['Pan-STARRS1 cols']

    if twomass is True:
        query += ',\n--Adding 2MASS Columns:\n'
        query += defaults['2MASS cols']

    ####################
    # (Possible) User Input

    # Replacing {} with _asdict
    query = query.format(**defaults['asdict'])

    if user_cols is None:
        query += '\n'
    elif not isinstance(user_cols, str):
        raise TypeError('user_sel is not a (str)')
    elif user_cols == '':
            query += '\n'
    else:
        query += ',\n\n--Custom Selection & Assignement:'
        if user_cols[:1] != '\n':
            user_cols = '\n' + user_cols
        if user_cols[-1] == ',':
            user_cols = user_cols[:-1]
        query += user_cols

    ####################
    # Return
    if 'units' in defaults:
        return query, defaults['units']
    else:
        return query, None
# /def


def _make_query_FROM(FROM=None, inmostquery=False, _tab='    '):
    r"""Make the FROM portion of a gaia query

    INPUTS
    ------
    FROM: str (or None)
        User input FROM (though should not have FROM in it)
        Default: None
            goes to 'gaiadr2.gaia_source'
        Useful for nesting queries as an inner query can be input here
    inmostquery: bool
        whether the query is the innermost query
    _tab: str
        the tab
        default: 4 spaces

    RETURNS:
    --------
    query: str
        The query, with FROM added
    """
    # FROM
    if FROM is None:
        FROM = 'gaiadr2.gaia_source'
    else:
        # Tab level
        FROM = _tab + FROM
        FROM = FROM.replace('\n', '\n{tab}'.format(tab=_tab))

    if inmostquery is False:
        p1, p2 ='(\n', '\n)'
    else:
        p1, p2 ='', ''

    s = "\n".join((
            "\n",
            "--SOURCE:",
            "FROM {p1}{userfrom}{p2} AS gaia".format(
                userfrom=FROM, p1=p1, p2=p2)))

    return s
# /def


def _query_tab_level(query, tablevel, _tab='    '):
    r"""Add tab level to query
    indents the whoel query by the tab level
    # TODO use textwrap.indent instead

    INPUTS
    ------
    query: str
        the query
    tablevel: int
        tab * tablevel
        tab = _tab
    _tab: str
        the tab
        default: 4 spaces

    RETURNS
    -------
    query
    """
    # Tab level
    query = (_tab * tablevel) + query
    query = query.replace('\n', '\n{tab}'.format(tab=_tab * tablevel))
    return query
# /def


def _make_query_WHERE(WHERE, random_index=False):
    r"""make query WHERE

    INPUTS
    ------
    WHERE: str (or None)
        ADQL `WHERE' argument
    random_index: int or False
        the gaia.random_index for fast querying
    """

    # query = '' if query is None else query
    # Selection
    s = "\n\n--Selections:\nWHERE"
    if WHERE[:1] != '\n':
        WHERE = '\n' + WHERE
    s += WHERE

    if random_index is not False:
        s += '\nAND random_index < ' + str(int(random_index))

    return s
# /def


def _make_query_ORDERBY(ORDERBY):
    r"""make query ORDERBY

    INPUTS
    ------
    ORDERBY: str
        the orderby arguments
    """
    # query = '' if query is None else query
    s ='\n\n--Ordering:\nORDER BY'
    if ORDERBY[:1] != '\n':
        ORDERBY = '\n' + ORDERBY
    s += ORDERBY

    return s
# /def


def make_query(WHERE=None, ORDERBY=None, FROM=None, random_index=False,
               user_cols=None, all_columns=False,
               gaia_mags=False, panstarrs1=False, twomass=False,
               use_AS=False, user_ASdict=None, defaults='default',
               inmostquery=False,
               units=False,
               # doing the query
               do_query=False, local=False, cache=True, timeit=False,
               verbose=False, dbname='catalogs', user='postgres',
               # extra options
               _tab='    ', pprint=False):
    """Makes a whole Gaia query

    INPUTS
    ------
    WHERE: str (or None)
        ADQL `WHERE' argument
    ORDERBY: str (or None)
        ADQL `ORDER BY' argument
    FROM: str (or None)
        ADQL `FFROM' argument
    random_index: int or False
        the gaia.random_index for fast querying
        Default: False
    user_cols: str (or None)
        Data columns in addition to default columns
        Default: None
        ex: "gaia.L, gaia.B,"
    all_columns: bool
        Whether to include all columns
        via ', *'
        Default: False
    gaia_mags: bool
        Whether to include Gaia magnitudes
        Default: False
    panstarrs1: bool
        Whether to include Panstarrs1 g,r,i,z magnitudes and INNER JOIN on Gaia
        Default: False
    use_AS: bool
        True will add 'AS __' to the data columns
        This is good for the outer part of the query
        so as to have convenient names in the output data table.
        Default: True
    user_ASdict: dict (or None)
        dictionary containing `AS' arguments
    defaults: str (or None or dict)
        the filepath (str) of the gaia query defaults
        if None, uses '/defaults/gaia_defaults.json'
        if ''
        if dict, assumes the dictionary is correct and returns
        **SEE DEFAULTS
    inmostquery: bool
        needed if in-most query and not providing a FROM
    units: bool
        adds missing units to a query, if units in defaults['units']
        Default: True
    do_query: bool
        performs a gaia query
        Default: False
    local: bool
        perform gaia query locally (if do_query is True)
        Default: False
    cache: str, bool
        False: does not cache
        str or True: caches
        if str: set as cache.nickname
    _tab: str
        the tab
        default: 4 spaces
    pprint: bool
        print the query

    Returns
    -------
    if do_query is True:
        table: Table
    else:
        query: str

    DEFAULTS
    --------
    In a Json-esque format.
    See defaults/gaia_defaults.json
    """

    # SETUP
    # cache options
    if isinstance(cache, str):
        use_cache = True
    elif isinstance(cache, bool):
        use_cache = cache

    else:
        raise ValueError('cache must be <str> or <bool>')



    # QUERY CONSTRUCTION
    query, udict = _make_query_SELECT(user_cols=user_cols, use_AS=use_AS,
                                      all_columns=all_columns,
                                      gaia_mags=gaia_mags,
                                      panstarrs1=panstarrs1, twomass=twomass,
                                      defaults=defaults)

    query += _make_query_FROM(FROM, inmostquery=inmostquery, _tab=_tab)

    # Joining ON Panstarrs1
    if panstarrs1 is True:
        query += "\n".join((
            "\n",
            "--Comparing to Pan-STARRS1",
            "INNER JOIN gaiadr2.panstarrs1_best_neighbour AS panstarrs1_match "
            "ON panstarrs1_match.source_id = gaia.source_id",
            "INNER JOIN gaiadr2.panstarrs1_original_valid AS panstarrs1 "
            "ON panstarrs1.obj_id = panstarrs1_match.original_ext_source_id"
            ""))

    if twomass is True:
        query += "\n".join((
            "\n",
            "--Comparing to 2MASS",
            "INNER JOIN gaiadr2.tmass_best_neighbour AS tmass_match "
            "ON tmass_match.source_id = gaia.source_id",
            "INNER JOIN gaiadr1.tmass_original_valid AS tmass "
            "ON tmass.tmass_oid = tmass_match.tmass_oid"
            ""))

    # Adding WHERE
    if WHERE is not None:
        query += _make_query_WHERE(WHERE, random_index=random_index)
    elif random_index is not False:
        query += "\n\n--Selections:\nWHERE\nrandom_index <= "
        query += str(int(random_index))

    # Adding ORDERBY
    if ORDERBY is not None:
        query += _make_query_ORDERBY(ORDERBY)

    # user_ASdict
    if user_ASdict is not None:
        query = query.format(**user_ASdict)

    # Query tab level
    # query = _query_tab_level(query, tablevel=tablevel)
    # # Finishing ADQL query
    # query += ";"

    # Returning
    if pprint is True:
        print(query)

    # Query
    if do_query is True:

        print('\n\nstarting query @ {}'.format(time.strftime('m%md%dh%Hs%S')))
        df = Query(query, local=local, timeit=timeit, use_cache=use_cache,
                   verbose=verbose, dbname=dbname, user=user)
        print('query finished @ {}'.format(time.strftime('m%md%dh%Hs%S')))

        # caching
        if isinstance(cache, str):
            Cache.nickname(query, cache)

        # apply units
        if units is False:  # don't use added units
            _return = df
        # use added units
        elif udict is not None:
            # FIXME local queries return incompatible dtypes
            if local is True:
                #         id          everything else
                dtypes = ['int64'] + ['float64'] * (len(df.colnames) - 1)
                df = Table(df, names=df.colnames, dtype=dtypes)
            _return = add_units_to_Table(df, udict)
        # units is true, but there are no units to use
        else:
            _return = df

        return _return

    # don't query
    else:
        # don't use units
        if units is False:
            _return = query
        # use units
        else:
            # there are units
            if udict is not None:
                _return = query, udict
            # there aren't units to use
            else:
                print('no units to use')
                _return = query, {}

        return _return
# /def


def make_simple_query(WHERE=None, ORDERBY=None, FROM=None,
                      random_index=False,
                      user_cols=None, all_columns=False,
                      gaia_mags=False, panstarrs1=False, twomass=False,
                      user_ASdict=None, defaults='default', units=False,
                      # do query
                      do_query=False, local=False, cache=True, timeit=False,
                      verbose=False, dbname='catalogs', user='postgres',
                      # extra options
                      pprint=False):
    """make_gaia_query wrapper for single-layer queries
    with some defaults changed and options removed
    use_AS and inmostquery are now True.
    _tab is set to default

    INPUTS
    ------
    WHERE: str (or None)
        ADQL `WHERE' argument
    ORDERBY: str (or None)
        ADQL `ORDER BY' argument
    FROM: str (or None)
        ADQL `FFROM' argument
    random_index: int or False
        the gaia.random_index for fast querying
        Default: False
    user_cols: str (or None)
        Data columns in addition to default columns
        Default: None
        ex: "gaia.L, gaia.B,"
    all_columns: bool
        Whether to include all columns
        via ', *'
        Default: False
    gaia_mags: bool
        Whether to include Gaia magnitudes
        Default: False
    panstarrs1: bool
        Whether to include Panstarrs1 g,r,i,z magnitudes and INNER JOIN on Gaia
        Default: False
    user_ASdict: dict (or None)
        dictionary containing `AS' arguments
    defaults: str (or None or dict)
        the filepath (str) of the gaia query defaults
        if None, uses '/defaults/gaia_defaults.json'
        if ''
        if dict, assumes the dictionary is correct and returns
        **SEE DEFAULTS
    units: bool
        adds missing units to a query, if units in defaults['units']
        Default: True
    do_query: bool
        performs a gaia query
        Default: False
    local: bool
        perform gaia query locally (if do_query is True)
        Default: False
    pprint: bool
        print the query

    Returns
    -------
    if do_query is True:
        table: Table
    else:
        query: str

    DEFAULTS
    --------
    In a Json-esque format.
    See defaults/gaia_defaults.json
    """

    return make_query(WHERE=WHERE, ORDERBY=ORDERBY, FROM=FROM,
                      random_index=random_index,
                      user_cols=user_cols, use_AS=True,
                      all_columns=all_columns,
                      gaia_mags=gaia_mags,
                      panstarrs1=panstarrs1, twomass=twomass,
                      user_ASdict=user_ASdict, inmostquery=True,
                      defaults=defaults, units=units,
                      # do_query
                      do_query=do_query, local=local, cache=cache,
                      timeit=timeit, verbose=verbose, dbname=dbname, user=user,
                      # print
                      pprint=pprint)
# /def
