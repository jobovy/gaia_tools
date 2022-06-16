import os
import glob
import tqdm
import numpy as np
import pandas as pd
from astropy.io import ascii
from itertools import compress
import warnings

from .path import _GAIA_TOOLS_DATA


def read_spec_internal(source_ids, assume_unique, base_path, wavelength_grid):
    """
    internal function to read spectra based on a list of source id
    """
    file_paths = glob.glob(os.path.join(base_path, "*.csv.gz"))
    if len(file_paths) == 0:
        raise FileNotFoundError(f"Gaia data does not exist at {base_path}")
    file_names = [os.path.basename(x) for x in file_paths]

    source_ids = np.atleast_1d(source_ids)
    # HEALpix level 8: 8796093022208
    reduced_source_ids = source_ids // 8796093022208
    num_source = len(reduced_source_ids)

    all_spec = np.zeros([num_source, len(wavelength_grid)], dtype=np.float32)
    all_spec_error = np.zeros([num_source, len(wavelength_grid)], dtype=np.float32)
    not_found = np.ones(num_source, dtype=bool)
    
    # Extract HEALPix level-8 from file name
    healpix_8_min = [
        int(file[file.find("_") + 1 : file.rfind("-")]) for file in file_names
    ]
    healpix_8_max = [
        int(file[file.rfind("-") + 1 : file.rfind(".csv")]) for file in file_names
    ]
    reference_file = {
        "file": file_names,
        "healpix8_min": healpix_8_min,
        "healpix8_max": healpix_8_max,
    }

    combo_comparisons = np.asarray(
        [
            (reference_file["healpix8_min"] <= i)
            & (i <= reference_file["healpix8_max"])
            for i in reduced_source_ids
        ]
    )
    files_required = np.unique(
        [list(compress(file_names, i)) for i in combo_comparisons]
    )

    if not np.all(np.any(combo_comparisons, axis=1)):
        raise ValueError("Contain invalid Gaia source id")

    for idx, i in enumerate(tqdm.tqdm(file_names, desc="Working on data file:")):
        if not i in files_required:
            continue
        else:
            spec_f = ascii.read(os.path.join(base_path, i))
            current_source_ids = source_ids[combo_comparisons[:, idx]]
            matches, idx1, idx2 = np.intersect1d(
                current_source_ids,
                spec_f["source_id"].data,
                assume_unique=False,
                return_indices=True,
            )
            if len(matches) > 0:
                current_idx = np.where(combo_comparisons[:, idx])[0][idx1]
                all_spec[current_idx] = np.vstack(spec_f["flux"][idx2])
                all_spec_error[current_idx] = np.vstack(spec_f["flux_error"][idx2])
                not_found[current_idx] = False

    # deal with duplicated source_id
    if not assume_unique:
        uniques = np.unique(source_ids, return_index=True)[1]
        result = np.ones_like(source_ids, dtype=bool)
        result[uniques] = False
        duplicated_idx = np.where(result)[0]
        for i in duplicated_idx:
            first_occurence_idx = np.argmax(source_ids == source_ids[i])
            all_spec[i] = all_spec[first_occurence_idx]
            all_spec_error[i] = all_spec_error[first_occurence_idx]
            not_found[i] = not_found[first_occurence_idx]
            
    if np.any(not_found):
        warnings.warn(f"These source id have no corresponding spectra found: {source_ids[not_found]}")

    return wavelength_grid, all_spec, all_spec_error


def load_rvs_spec(source_ids, assume_unique=False):
    """
    NAME:
        load_rvs_spec
    PURPOSE:
        Read corresponding RVS spectra for a list of source id
    INPUT:
        source_ids (int, list, ndarray): source id
        assume_unique (bool): whether to assume the list of source id is unique
    OUTPUT:
        wavelength grid, RVS spectra flux row matched to source_id, RVS spectra corresponding flux uncertainty
    HISTORY:
        2022-06-16 - Written - Henry Leung (UofT)
    """
    base_path = os.path.join(
        _GAIA_TOOLS_DATA, "Gaia/gdr3/Spectroscopy/rvs_mean_spectrum/"
    )
    wavelength_grid = np.arange(846, 870.01, 0.01)
    return read_spec_internal(
        source_ids=source_ids,
        assume_unique=assume_unique,
        base_path=base_path,
        wavelength_grid=wavelength_grid,
    )


def load_xp_sampled_spec(source_ids, assume_unique=False):
    """
    NAME:
        load_xp_sampled_spec
    PURPOSE:
        Read corresponding XP spectra for a list of source id
    INPUT:
        source_ids (int, list, ndarray): source id
        assume_unique (bool): whether to assume the list of source id is unique
    OUTPUT:
        wavelength grid, XP spectra flux row matched to source_id, XP spectra corresponding flux uncertainty
    HISTORY:
        2022-06-16 - Written - Henry Leung (UofT)
    """
    base_path = os.path.join(
        _GAIA_TOOLS_DATA, "Gaia/gdr3/Spectroscopy/xp_sampled_mean_spectrum/"
    )        
    wavelength_grid = np.arange(336.0, 1022.0, 2.0)
    return read_spec_internal(
        source_ids=source_ids,
        assume_unique=assume_unique,
        base_path=base_path,
        wavelength_grid=wavelength_grid,
    )
