# gaia_tools.query: some helper functions for querying the Gaia database

from . import cache as query_cache

from ._query import query
from .make_gaia_query import make_query, make_simple_query

query_cache.autoclean()
