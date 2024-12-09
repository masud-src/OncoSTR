"""
Definition of auxiliary utils functions.

Functions:
    mkdir_if_not_exist:         Creates a directory if that not exists
    set_out_dir:                Checks if parent path has separator at end and merges the paths.
    split_path:                 Splits Filepath into file and path.
    get_path_file_extension:    Returns path, the filename and the filename without extension.
    cut_area_from_image:        Cuts an area of that image.
    image2array:                Takes a directory of an image and gives a numpy array.
    image2mask:                 Gives deep copy of original image with selected compartments.
    single_segmentation:        runs fast segmentation algorithm in default with variable input files.
"""

import fsl.wrappers.fslmaths
import fsl.wrappers.fast
import numpy as np
import copy
from pathlib import Path
from typing import Union, Any
import nibabel as nib
import os


def mkdir_if_not_exist(directory: str) -> str:
    """
    Makes directory if not exists and returns the string.

    :param directory: String

    :return: String of the directory
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def set_out_dir(parent: str, child: str) -> str:
    """
    Checks if parent path has separator at end and merges the paths.
    
    :param parent: String of parent directory 
    :param child: String of child directory

    :return: String of combined path
    """
    if not parent.endswith(os.sep):
        parent = parent + os.sep
    return parent + child


def split_path(s: str) -> tuple[str, str]:
    """
    Splits Filepath into file and path

    :param s: String

    :return: (file, path)
    """
    import os
    f = os.path.basename(s)
    p = s[:-(len(f)) - 1]
    return str(f), str(p)


def get_path_file_extension(input_file: str) -> tuple[str, str, str]:
    """
    Returns path, the filename and the filename without extension.

    :param input_file: Input path

    :return: (path, filename, file without extension)
    """
    file, path = split_path(input_file)
    file_wo_extension = Path(Path(input_file).stem).stem
    return path, file, file_wo_extension


def cut_area_from_image(input_image: str, area_mask: nib.Nifti1Image,
                        inverse: bool = False) -> Union[None, nib.Nifti1Image]:
    """
    Cuts an area of that image.

    :param input_image: String of path to Nifti image
    :param area_mask: Mask array
    :param inverse: Bool, true for inverse cut

    :return: optionally returns the image or writes it next to the input image
    """
    if inverse:
        area_mask = fsl.wrappers.fslmaths(area_mask).mul(-1).add(1).run()

    return fsl.wrappers.fslmaths(input_image).mul(area_mask).run()


def image2array(image_dir: str) -> tuple[Any, Any, Any]:
    """
    Takes a directory of an image and gives a numpy array.

    :param image_dir: String of a Nifti image directory
    :return: numpy array of image data, shape, affine
    """
    orig_image = nib.load(image_dir)
    return copy.deepcopy(orig_image.get_fdata()), orig_image.shape, orig_image.affine


def image2mask(image_dir: str, compartment: int, inner_compartments: list[int] = None) -> np.ndarray:
    """
    Gives deep copy of original image with selected compartments.

    :param image_dir: String to Nifti image
    :param compartment: Int, identifier of compartment that shall be filtered
    :param inner_compartments: List of inner compartments that also are included in the mask

    :return mask: Numpy array of the binary mask
    """
    mask, _, _ = image2array(image_dir)
    unique = list(np.unique(mask))
    unique.remove(compartment)
    for outer in unique:
        mask[np.isclose(mask, outer)] = 0.0
    mask[np.isclose(mask, compartment)] = 1.0
    if inner_compartments is not None:
        for comp in inner_compartments:
            mask[np.isclose(mask, comp)] = 1.0
            unique.remove(comp)
    return mask


def single_segmentation(basename: str, files_list: list[str], n_classes: int) -> None:
    """
    runs fast segmentation algorithm in default with variable input files.

    :param basename: String for base name of outputfiles
    :param files_list: List of input images
    :param n_classes: Number of segmentation classes

    :return: None
    """
    fsl.wrappers.fast(files_list, basename, n_classes)
