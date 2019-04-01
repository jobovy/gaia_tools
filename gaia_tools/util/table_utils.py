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
Planned Features
"""

#############################################################################
# Imports

import json
import os
import itertools
import numpy as np

from astropy.table import Table, QTable

try:
    from util.myastropy.units import units as u
except ImportError:
    from astropy import units as u

#############################################################################
# Info

__author__ = "Nathaniel Starkman"
__copyright__ = "Copyright 2018, "
__credits__ = ["Jo Bovy"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Nathaniel Starkman"
__email__ = "n.starkman@mail.utoronto.ca"
__status__ = "Production"

#############################################################################
# Code


def neg_to_nan(df, col):
    """set negative parallaxes to nan
    This edits  a view
    """
    df[col][df[col] < 0] = np.NaN


def add_units_to_Table(df, udict=None, _subkey=None):
    """takes Table and returns QTable
    dfQ = add_units_to_Table(df, udict)
    udict: unit dictionary
    _subkey key for dictionary if loading from JSON
        str or list of str for nested dict
    """
    def safeget(dct, *keys):
        """https://stackoverflow.com/a/25833661/5041184"""
        for key in keys:
            try:
                dct = dct[key]
            except KeyError:
                return None
        return dct

    # Pre-adjusting for JSON udict
    if udict is None:
        dirname = os.path.dirname(__file__)
        udict = os.path.join(dirname, 'gaia_query_defaults.json')
        _subkey = ['units', ]
        # Now it's a string and will trigger next 'if'

    # JSON udict
    if isinstance(udict, str):
        with open(udict, 'r') as file:
            defaults = json.load(file)
            if _subkey is None:
                pass
            elif isinstance(_subkey, str):
                defaults = defaults[_subkey]
            else:  # nested
                defaults = safeget(defaults, *_subkey)

        udict = {}
        for k, v in defaults.items():
            if v != '':
                udict[k] = eval(v)  # astropy units
            else:
                udict[k] = u.dimensionless_unscaled

    # Adding Units, if corresponding column in Table
    for key, unit in udict.items():
        if key in df.columns and df[key].unit != unit:
            setattr(df[key], 'unit', unit)

    df = QTable(df)
    return df


def add_color_col(df, c1, c2, **kw):
    """
    TODO: make this a function of add_calculated_col
    KW opts:
    color: name of color
    """
    color = kw.get('color', c1 + '-' + c2)
    if color in df.colnames:
        print('{} already in table'.format(color))
        return None

    try:
        c1ind = df.index_column(c1 + '_err')
    except KeyError:
        c1ind = df.index_column(c1)
        noerr = True
    except ValueError:
        c1ind = df.index_column(c1)
        noerr = True
    else:
        noerr = False

    try:
        c2ind = df.index_column(c2 + '_err')
    except KeyError:
        c2ind = df.index_column(c1)
        noerr = True
    except ValueError:
        c2ind = df.index_column(c2)
        noerr = True
    else:
        noerr = False if noerr is False else True

    colindex = max(c1ind, c2ind) + 1
    df.add_column(df[c1] - df[c2], index=colindex, name=color)
    df[color].info.description = color + ' color'

    # Adding Error
    if noerr is False:
        colindex = df.index_column(color) + 1
        df.add_column(np.sqrt(df[c1 + '_err']**2 + df[c2 + '_err']**2),
                      index=colindex, name=color + '_err')
        df[color + '_err'].info.description = 'error in {} color [mag]'


def add_calculated_col(df, func, *cols, funcargs=[], funckw={}, **kw):
    """add a calculated column in two column variables
    # TODO get rid of color stuff

    Parameters
    ----------
    func: function
        function over df cols
        form function(*columns, *extra_arguments, **keyword_argument)
    cols: list of str
        the names of the columns in df
    funcargs: list
        list of extra arguments for func
    funckw: dict
        dictionary of extra keyword arguments for func

    Keyword Parameters
    ------------------
    - name: str
        function name
        defaults to 'func({},{})'
    - c{}err: str
        name of c{} error column
        where {} is the index in *cols list
        defaults to c{}+'_err'
    - index: int
        index to put column at
    - description: str
        column description
    - return: bool
        whether to return modified df

    Returns
    -------
    if kw['return'] is True:
        returns modified df
    else:
        it modifies in place
    """
    def colerrind(c, i, **kw):
        """function for color-error index"""
        cerr = kw.get('c{}err'.format(i), c + '_err')
        try:
            cind = df.index_column(cerr)
        except ValueError:
            cind = df.index_column(c)
        return cind

    name = kw.get('name', 'func{}'.format(str(tuple(cols))))

    if name in df.colnames:
        print('{} already in table'.format(name))
        return None

    cind = [colerrind(c, i, **kw) for i, c, in enumerate(cols)]
    colindex = kw.get('index', max(cind) + 1)

    df.add_column(func(*[df[c] for c in cols], *funcargs, **funckw),
                  index=colindex, name=name)

    df[name].info.description = kw.get('description', name)

    if kw.get('return', False) is True:
        return df


def add_abs_pm_col(df, pm1, pm2):
    """Add sqrt{pm1**2 + pm2**2} col
    also adds error and angle column
              sqrt{delta pmra**2 + delta pmdec**2}
              atan(pmdec/pmra)
    TODO allow name changing
    """
    add_calculated_col(df, lambda x, y: np.sqrt(x**2 + y**2), pm1, pm2,
                       name='pm', description=r'$\sqrt{pmra**2 + pmdec**2}$')

    add_calculated_col(df,
                       lambda x, y: np.sqrt(x**2 + y**2),
                       pm1 + '_err', pm2 + '_err',
                       name='pm_err',
                       description=r'$\sqrt{\delta pmra**2 + \delta pmdec**2}$')

    add_calculated_col(df, lambda x, y: np.arctan2(y, x), pm1, pm2,
                       name='pm_ang', description='atan(pmdec/pmra)')


def rename_columns(df, *args, **kw):
    """
    args: *[(name, rename), (name, rename), ...]
    kw:   **{name: rename, name: rename, name: rename, ...}
    """
    for n, rn in itertools.chain(args, kw.items()):
        df.rename_column(n, rn)


def drop_colnames(colnames, *args):
    """helper function for making a table from another table, dropping some names
    colnames: list
        list of names in the original table
    args: list
        list of strings of names to drop
    """
    names = np.array(colnames[:])  # shallow copy just in case
    inds = ~np.in1d(names, args)
    return list(names[inds])
