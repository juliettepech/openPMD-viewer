"""
This file is part of the openPMD-viewer.

It defines functions that can read the fields from an HDF5 file.

Copyright 2015-2016, openPMD-viewer contributors
Author: Remi Lehe
License: 3-Clause-BSD-LBNL
"""

import h5py
import numpy as np
from .utilities import get_shape, get_data, get_bpath, join_infile_path
from .field_metainfo import FieldMetaInformation


def read_field_1d( filename, field_path, axis_labels ):
    """
    Extract a given field from an HDF5 file in the openPMD format,
    when the geometry is 1d cartesian.

    Parameters
    ----------
    filename : string
       The absolute path to the HDF5 file

    field_path : string
       The relative path to the requested field, from the openPMD meshes path
       (e.g. 'rho', 'E/r', 'B/x')

    axis_labels: list of strings
       The name of the dimensions of the array (e.g. ['x', 'y', 'z'])

    Returns
    -------
    A tuple with
       F : a 1darray containing the required field
       info : a FieldMetaInformation object
       (contains information about the grid; see the corresponding docstring)
    """
    # Open the HDF5 file
    dfile = h5py.File( filename, 'r' )
    # Extract the dataset and and corresponding group
    group, dset = find_dataset( dfile, field_path )

    # Extract the data in 1D Cartesian
    F = get_data( dset )

    # Extract the metainformation
    axes = { 0: axis_labels[0]}
    info = FieldMetaInformation( axes, F.shape,
        group.attrs['gridSpacing'], group.attrs['gridGlobalOffset'],
        group.attrs['gridUnitSI'], dset.attrs['position'] )

    # Close the file
    dfile.close()
    return( F, info )


def read_field_2d( filename, field_path, axis_labels,
                   slicing=None, slicing_dir=None ):
    """
    Extract a given field from an HDF5 file in the openPMD format,
    when the geometry is 2d cartesian.

    Parameters
    ----------
    filename : string
       The absolute path to the HDF5 file

    field_path : string
       The relative path to the requested field, from the openPMD meshes path
       (e.g. 'rho', 'E/r', 'B/x')

    axis_labels: list of strings
       The name of the dimensions of the array (e.g. ['x', 'y', 'z'])

    slicing : float or list of float, optional
        Number(s) between -1 and 1 that indicates where to slice the data,
        along directions given in `slicing_dir`
        -1 : lower edge of the simulation box
        0 : middle of the simulation box
        1 : upper edge of the simulation box
        If slicing is None, the full 3D grid is returned.

    slicing_dir : str or list of str, optional
        Direction(s) along which to slice the data
        Elements can be 'x' and/or 'z'

    Returns
    -------
    A tuple with
       F : a 2darray containing the required field
       info : a FieldMetaInformation object
       (contains information about the grid; see the corresponding docstring)
    """
    # Convert slicing and slicing_dir to lists
    if slicing is not None and not isinstance(slicing, list):
        slicing = [slicing]
    if slicing_dir is not None and not isinstance(slicing_dir, list):
        slicing_dir = [slicing_dir]
    # slicing_dir is the intersection of slicing_dir with axis_labels
    if slicing_dir is not None:
        slicing_dir = [value for value in slicing_dir if value in axis_labels]

    # Open the HDF5 file
    dfile = h5py.File( filename, 'r' )
    # Extract the dataset and and corresponding group
    group, dset = find_dataset( dfile, field_path )

    # Dimensions of the grid
    shape = list( get_shape( dset ) )
    grid_spacing = list( group.attrs['gridSpacing'] )
    global_offset = list( group.attrs['gridGlobalOffset'] )
    # Slice selection
    if slicing_dir is not None:
        # Get the integer that correspond to the slicing direction
        list_slicing_index = []
        list_i_cell = []
        new_labels = axis_labels
        for count, slicing_dir_item in enumerate(slicing_dir):
            slicing_index = axis_labels.index(slicing_dir_item)
            list_slicing_index.append(slicing_index)
            # Number of cells along the slicing direction
            n_cells = shape[ slicing_index ]
            # Index of the slice (prevent stepping out of the array)
            i_cell = int( 0.5 * (slicing[count] + 1.) * n_cells )
            i_cell = max( i_cell, 0 )
            i_cell = min( i_cell, n_cells - 1)
            list_i_cell.append(i_cell)

        # Remove metainformation relative to the slicing index
        # Successive pops starting from last coordinate to slice
        list_indices_to_clean = list_slicing_index[:]
        list_indices_to_clean.sort(reverse=True)
        for index_to_clean in list_indices_to_clean:
            shape.pop( index_to_clean )
            grid_spacing.pop( index_to_clean )
            global_offset.pop( index_to_clean )
            new_labels = new_labels[:index_to_clean] + \
                new_labels[index_to_clean + 1:]

        axes = { i: new_labels[i] for i in range(len(new_labels)) }
        # Extraction of the data
        F = get_data( dset, list_i_cell, list_slicing_index )
        info = FieldMetaInformation( axes, shape, grid_spacing, global_offset,
                group.attrs['gridUnitSI'], dset.attrs['position'] )
    else:
        F = get_data( dset )
        axes = { i: axis_labels[i] for i in range(len(axis_labels)) }
        info = FieldMetaInformation( axes, F.shape,
            group.attrs['gridSpacing'], group.attrs['gridGlobalOffset'],
            group.attrs['gridUnitSI'], dset.attrs['position'] )

    # Close the file
    dfile.close()
    return( F, info )


def read_field_circ( filename, field_path, m=0, theta=0. ):
    """
    Extract a given field from an HDF5 file in the openPMD format,
    when the geometry is 2d cartesian.

    Parameters
    ----------
    filename : string
       The absolute path to the HDF5 file

    field_path : string
       The relative path to the requested field, from the openPMD meshes path
       (e.g. 'rho', 'E/r', 'B/x')

    m : int or string, optional
       The azimuthal mode to be extracted

    theta : float, optional
       Angle of the plane of observation with respect to the x axis

    Returns
    -------
    A tuple with
       F : a 2darray containing the required field
       info : a FieldMetaInformation object
       (contains information about the grid; see the corresponding docstring)
    """
    # Open the HDF5 file
    dfile = h5py.File( filename, 'r' )
    # Extract the dataset and and corresponding group
    group, dset = find_dataset( dfile, field_path )

    # Extract the metainformation
    Nm, Nr, Nz = get_shape( dset )
    info = FieldMetaInformation( { 0: 'r', 1: 'z' }, (Nr, Nz),
        group.attrs['gridSpacing'], group.attrs['gridGlobalOffset'],
        group.attrs['gridUnitSI'], dset.attrs['position'], thetaMode=True )

    # Extract the modes and recombine them properly
    F_total = np.zeros( (2 * Nr, Nz ) )
    if m == 'all':
        # Sum of all the modes
        # - Prepare the multiplier arrays
        mult_above_axis = [1]
        mult_below_axis = [1]
        for mode in range(1, int(Nm / 2) + 1):
            cos = np.cos( mode * theta )
            sin = np.sin( mode * theta )
            mult_above_axis += [cos, sin]
            mult_below_axis += [ (-1) ** mode * cos, (-1) ** mode * sin ]
        mult_above_axis = np.array( mult_above_axis )
        mult_below_axis = np.array( mult_below_axis )
        # - Sum the modes
        F = get_data( dset )  # (Extracts all modes)
        F_total[Nr:, :] = np.tensordot( mult_above_axis,
                                        F, axes=(0, 0) )[:, :]
        F_total[:Nr, :] = np.tensordot( mult_below_axis,
                                        F, axes=(0, 0) )[::-1, :]
    elif m == 0:
        # Extract mode 0
        F = get_data( dset, 0, 0 )
        F_total[Nr:, :] = F[:, :]
        F_total[:Nr, :] = F[::-1, :]
    else:
        # Extract higher mode
        cos = np.cos( m * theta )
        sin = np.sin( m * theta )
        F_cos = get_data( dset, 2 * m - 1, 0 )
        F_sin = get_data( dset, 2 * m, 0 )
        F = cos * F_cos + sin * F_sin
        F_total[Nr:, :] = F[:, :]
        F_total[:Nr, :] = (-1) ** m * F[::-1, :]

    # Close the file
    dfile.close()
    return( F_total, info )


def read_field_3d( filename, field_path, axis_labels,
                   slicing=[0.], slicing_dir=['y']):
    """
    Extract a given field from an HDF5 file in the openPMD format,
    when the geometry is 3d cartesian.

    Parameters
    ----------
    filename : string
       The absolute path to the HDF5 file

    field_path : string
       The relative path to the requested field, from the openPMD meshes path
       (e.g. 'rho', 'E/r', 'B/x')

    axis_labels: list of strings
       The name of the dimensions of the array (e.g. ['x', 'y', 'z'])

    slicing : float or list of float, optional
        number(s) between -1 and 1 that indicates where to slice the data,
        along directions given in `slicing_dir`
        -1 : lower edge of the simulation box
        0 : middle of the simulation box
        1 : upper edge of the simulation box
        If slicing is None, the full 3D grid is returned.

    slicing_dir : str or list of str, optional
        Direction(s) along which to slice the data
        Elements can be 'x', 'y' and/or 'z'

    Returns
    -------
    A tuple with
       F : a 2darray containing the required field
       info : a FieldMetaInformation object
       (contains information about the grid; see the corresponding docstring)
    """
    # Convert slicing and slicing_dir to lists
    if slicing is not None and not isinstance(slicing, list):
        slicing = [slicing]
    if slicing_dir is not None and not isinstance(slicing_dir, list):
        slicing_dir = [slicing_dir]
    # slicing_dir is the intersection of slicing_dir with axis_labels
    if slicing_dir is not None:
        slicing_dir = [value for value in slicing_dir if value in axis_labels]
    # Need to:
    # - Do a similar thing for slicing
    # - Test if list is empty, and replace with None
    # Open the HDF5 file
    dfile = h5py.File( filename, 'r' )
    # Extract the dataset and and corresponding group
    group, dset = find_dataset( dfile, field_path )

    # Dimensions of the grid
    shape = list( get_shape( dset ) )
    grid_spacing = list( group.attrs['gridSpacing'] )
    global_offset = list( group.attrs['gridGlobalOffset'] )

    # Slice selection
    if slicing_dir is not None:
        # Get the integer that correspond to the slicing direction
        list_slicing_index = []
        list_i_cell = []
        new_labels = axis_labels
        for count, slicing_dir_item in enumerate(slicing_dir):
            slicing_index = axis_labels.index(slicing_dir_item)
            list_slicing_index.append(slicing_index)
            # Number of cells along the slicing direction
            n_cells = shape[ slicing_index ]
            # Index of the slice (prevent stepping out of the array)
            i_cell = int( 0.5 * (slicing[count] + 1.) * n_cells )
            i_cell = max( i_cell, 0 )
            i_cell = min( i_cell, n_cells - 1)
            list_i_cell.append(i_cell)

        # Remove metainformation relative to the slicing index
        # Successive pops starting from last coordinate to slice
        list_indices_to_clean = list_slicing_index[:]
        list_indices_to_clean.sort(reverse=True)
        for index_to_clean in list_indices_to_clean:
            shape.pop( index_to_clean )
            grid_spacing.pop( index_to_clean )
            global_offset.pop( index_to_clean )
            new_labels = new_labels[:index_to_clean] + \
                new_labels[index_to_clean + 1:]

        axes = { i: new_labels[i] for i in range(len(new_labels)) }
        # Extraction of the data
        F = get_data( dset, list_i_cell, list_slicing_index )
        info = FieldMetaInformation( axes, shape, grid_spacing, global_offset,
                group.attrs['gridUnitSI'], dset.attrs['position'] )
    else:
        F = get_data( dset )
        axes = { i: axis_labels[i] for i in range(len(axis_labels)) }
        info = FieldMetaInformation( axes, F.shape,
            group.attrs['gridSpacing'], group.attrs['gridGlobalOffset'],
            group.attrs['gridUnitSI'], dset.attrs['position'] )

    # Close the file
    dfile.close()
    return( F, info )


def find_dataset( dfile, field_path ):
    """
    Extract the dataset that corresponds to field_path,
    and the corresponding group

    (In the case of scalar records, the group and the dataset are identical.
    In the case of vector records, the group contains all the components
    and the dataset corresponds to one given component.)

    Parameters
    ----------
    dfile: an h5Py.File object
       The file from which to extract the dataset

    field_path : string
       The relative path to the requested field, from the openPMD meshes path
       (e.g. 'rho', 'E/r', 'B/x')

    Returns
    -------
    A tuple with:
    - an h5py.Group object
    - an h5py.Dataset object
    """
    # Find the meshes path
    base_path = get_bpath( dfile )
    relative_meshes_path = dfile.attrs["meshesPath"].decode()

    # Get the proper dataset
    full_field_path = join_infile_path(
        base_path, relative_meshes_path, field_path )
    dset = dfile[ full_field_path ]
    # Get the proper group
    group_path = field_path.split('/')[0]
    full_group_path = join_infile_path(
        base_path, relative_meshes_path, group_path )
    group = dfile[ full_group_path ]

    return( group, dset )


def get_grid_parameters( dfile, avail_fields, metadata ):
    """
    Return the parameters of the spatial grid (grid size and grid range)
    in two dictionaries

    Parameters:
    -----------
    dfile: an h5Py.File object
       The file from which to extract the information

    avail_fields: list
       A list of the available fields
       e.g. ['B', 'E', 'rho']

    metadata: dictionary
      A dictionary whose keys are the fields of `avail_fields` and
      whose values are dictionaries that contain metadata (e.g. geometry)

    Returns:
    --------
    A tuple with `grid_size_dict` and `grid_range_dict`
    Both objects are dictionaries, with their keys being the labels of the axis
    of the grid (e.g. 'x', 'y', 'z')
    The values of `grid_size_dict` are the number of gridpoints along each axis
    The values of `grid_range_dict` are lists of two floats, which correspond
    to the min and max of the grid, along each axis.
    """
    # Pick field with the highest dimensionality ('3d'>'thetaMode'>'2d')
    # (This function is for the purpose of histogramming the particles;
    # in this case, the highest dimensionality ensures that more particle
    # quantities can be properly histogrammed.)
    geometry_ranking = {'1dcartesian': 0, '2dcartesian': 1,
                        'thetaMode': 2, '3dcartesian': 3}
    fields_ranking = [ geometry_ranking[ metadata[field]['geometry'] ]
                        for field in avail_fields ]
    index_best_field = fields_ranking.index( max(fields_ranking) )
    field_name = avail_fields[ index_best_field ]

    # Get the corresponding field data
    group, dset = find_dataset( dfile, field_name )
    if metadata[field_name]['type'] == 'vector':
        # For field vector, extract the first coordinate, to get the dataset
        first_coord = next(iter(group.keys()))
        dset = group[first_coord]

    # Extract relevant quantities
    labels = group.attrs['axisLabels']
    grid_spacing = group.attrs['gridSpacing'] * group.attrs['gridUnitSI']
    grid_offset = group.attrs['gridGlobalOffset'] * group.attrs['gridUnitSI']
    grid_size = dset.shape
    if metadata[field_name]['geometry'] == 'thetaMode':
        # In thetaMode: skip the first number of dset.shape, as this
        # corresponds to the number of modes
        grid_size = dset.shape[1:]

    # Build the dictionaries grid_size_dict and grid_range_dict
    grid_size_dict = {}
    grid_range_dict = {}
    for i in range(len(labels)):
        coord = labels[i].decode()
        grid_size_dict[coord] = grid_size[i]
        grid_range_dict[coord] = \
            [ grid_offset[i], grid_offset[i] + grid_size[i] * grid_spacing[i] ]

    return( grid_size_dict, grid_range_dict )
