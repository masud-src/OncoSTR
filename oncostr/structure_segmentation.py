"""
In this white matter segmentation module the heterogeneous distributions are identified.

Class:
    StructureSegmentation:      Basically uses fast of FSL for the segmentation. Herein, a mixture of Gaussian
                                distributes the relevant classes of white and grey matter and cerebrospinal fluid in the
                                brain area.
"""
import fsl.wrappers.fslmaths
import fsl.wrappers.fast
import nibabel as nib
import numpy as np
import copy
import os
import glob
from pathlib import Path
from typing import Union, Any

STRUCTURE_SEGMENTATION_PATH = "structure_segmentation" + os.path.sep

def mkdir_if_not_exist(directory: str) -> str:
    """
    Makes directory if not exists and returns the string

    *Arguments*:
        dir: String

    *Example*:
        dir = mkdir_if_not_exist(dir)
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def split_path(s: str) -> tuple[str, str]:
    """
    Splits Filepath into file and path

    *Arguments:*
        s: String

    *Example:*
        file, path = splitPath(s)
    """
    import os
    f = os.path.basename(s)
    p = s[:-(len(f)) - 1]
    return str(f), str(p)


def get_path_file_extension(input_file: str) -> tuple[str, str, str]:
    """
    Returns path, the filename and the filename without extension.

    *Arguments:*
        input_file: String

    *Example:*
        path, file, file_wo_extension = get_path_file_extension(input_file)
    """
    file, path = split_path(input_file)
    file_wo_extension = Path(Path(input_file).stem).stem
    return path, file, file_wo_extension


class StructureSegmentation:
    """
    The StructureSegmentation class holds all options and functions for the segmentation of structural MRI modalities.
    With this entity the organ is split into its basic compartments. Basically, fast of FSL is used for the
    segmentation. Herein, a mixture of Gaussian distributes the relevant classes of white and grey matter and
    cerebrospinal fluid in the brain area.

    *Attributes*:
        work_dir:                   Directory of workspace, can be set as argument or actual workspace is set
        out_dir:                    Name of the output directory, herein all files are saved.
        input_files_dir:            List of the input images. It is recommended to only use one image.
        affine:                     Variable for the image affine, every segmentation is mapped
        remove_interim_files:       Bool to remove the created interim files
        modes:                      All implemented modes for segmentation
        mode:                       Selected mode of segmentation
        brain_handling_classes:     List of brain compartment classes, it should be segmented to
        tumor_class_mapping:        Dict of tumor classes with a respective mapping according to brats segmentation

    Methods
        set_input_structure_seg:        Sets the list of input files
        list_modes:                     prints all implemented modes
        cut_area_from_image:            STATIC, cuts an area from an image
        image2array:                    STATIC, transforms an image into an array
        image2mask:                     STATIC, creates a mask from an image
        single_segmentation:            STATIC, interface to fsl. Performs segmentation
        set_affine:                     Sets the affine from a given input image path
        split_tumor_from_brain:         Splits the tumor area from the brain area and saves the images
        segment_brain_part:             Segments only the healthy brain part
        tumor_agnostic_mode:            Segmention by ignoring the distorted tumor area
        bias_corrected_approach:        Segmentation according the bias corrected approach
        tumor_entity_weighted_approach: Segmentation according the tumor entity weighted approach
        run:                            Runs the segmentation
    """

    def __init__(self, work_dir=None):
        if work_dir==None:
            work_dir = os.getcwd() + os.sep
        if not work_dir.endswith(os.sep):
            work_dir = work_dir + os.sep
        self.work_dir = work_dir
        self.out_dir = work_dir + STRUCTURE_SEGMENTATION_PATH
        self.input_files_dir = None
        self.tumor_seg_dir = None
        self.affine = None
        self.remove_interim_files = True
        self.modes = ["tumor_agnostic", "bias_corrected", "tumor_entity_weighted"]
        self.mode = "bias_corrected"
        self.brain_handling_classes = ["cerebrospinal_fluid", "gray_matter", "white_matter"]
        self.tumor_class_mapping = {"edema": 2, "active": 4, "necrotic": 1}

    def set_input_structure_seg(self, input_files_dir: list, tumor_seg_dir: str = None) -> None:
        """
        Set input files of structure segmentation.

        :param input_files_dir: List, takes all structural input files gathered in a list. Should be in (t1, t1ce, t2, flair)
        :param tumor_seg_dir: tumor segmentation file. Corresponds to tumor segmentation file from tumor segmentation
        """
        self.input_files_dir = input_files_dir
        self.tumor_seg_dir = tumor_seg_dir

    def list_modes(self) -> None:
        """
        List all implemented modes of structure segmentation.

        :return: None
        """
        print(self.modes)

    @staticmethod
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

    @staticmethod
    def image2array(image_dir: str) -> tuple[Any, Any, Any]:
        """
        Takes a directory of an image and gives a numpy array.

        :param image_dir: String of a Nifti image directory
        :return: numpy array of image data, shape, affine
        """
        orig_image = nib.load(image_dir)
        return copy.deepcopy(orig_image.get_fdata()), orig_image.shape, orig_image.affine

    @staticmethod
    def image2mask(image_dir: str, compartment: int, inner_compartments: list[int] = None) -> np.ndarray:
        """
        Gives deep copy of original image with selected compartments.

        :param image_dir: String to Nifti image
        :param compartment: Int, identifier of compartment that shall be filtered
        :param inner_compartments: List of inner compartments that also are included in the mask

        :return mask: Numpy array of the binary mask
        """
        mask, _, _ = StructureSegmentation.image2array(image_dir)
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

    @staticmethod
    def single_segmentation(basename: str, files_list: list[str], n_classes: int) -> None:
        """
        runs fast segmentation algorithm in default with variable input files.

        :param basename: String for base name of outputfiles
        :param files_list: List of input images
        :param n_classes: Number of segmentation classes

        :return: None
        """
        fsl.wrappers.fast(files_list, basename, n_classes)

    def set_affine(self, image_dir: str = None) -> None:
        """
        Sets affine and shape of first measure of included state. The optional argument takes a nibabel Nifti1Image
        and takes the first measurement of the hold state of the mri entity if no argument is given.

        :param image_dir: Path of chosen input image, Default is input_files_dir[0]

        :return: None
        """
        if image_dir is None:
            image_dir = self.input_files_dir[0]
        self.affine = nib.load(image_dir).affine

    def split_tumor_from_brain(self) -> None:
        """
        Splits the tumor from the brain area and saves them with 'withTumor' and 'woTumor' endings.

        :return:
        """
        seg_id = list(self.tumor_class_mapping.values())
        tumor_mask = StructureSegmentation.image2mask(self.tumor_seg_dir, seg_id[0], seg_id[1:])
        self.set_affine()
        image_tumor_mask = nib.Nifti1Image(tumor_mask, self.affine)
        for modality in self.input_files_dir:
            _, _, file = get_path_file_extension(modality)
            for b in [True, False]:
                if b:
                    image = StructureSegmentation.cut_area_from_image(modality, image_tumor_mask, True)
                    nib.save(image, self.out_dir + file + "-woTumor.nii.gz")
                else:
                    image = StructureSegmentation.cut_area_from_image(modality, image_tumor_mask, False)
                    nib.save(image, self.out_dir + file + "-withTumor.nii.gz")

    def segment_brain_part(self) -> None:
        """
        Segments the undistorted brain part. Therefore, function 'split_tumor_from_brain' need to be run before or
        files with the ending '-woTumor.nii.gz' need to be preserved. Segments according to the brain_handling_classes
        and renames the files according to them.

        :return: None
        """
        brain_files = []
        for modality in self.input_files_dir:
            _, _, file = get_path_file_extension(modality)
            brain_files.append(self.out_dir + file + "-woTumor.nii.gz")

        StructureSegmentation.single_segmentation(self.out_dir + "wms_Brain", brain_files,
                                                  len(self.brain_handling_classes))
        for i, seg_class in enumerate(self.brain_handling_classes):
            os.rename(self.out_dir + "wms_Brain_pve_" + str(i) + ".nii.gz", self.out_dir + seg_class + ".nii.gz")

    def tumor_agnostic_mode(self) -> None:
        """
        Runs tumor agnostic segmentation mode. The files are simply segmented like no tumor is present.

        :return: None
        """
        self.single_segmentation(self.out_dir, self.input_files_dir, len(self.brain_handling_classes))
        for i, seg_class in enumerate(self.brain_handling_classes):
            os.rename(self.out_dir + "_pve_" + str(i) + ".nii.gz", self.out_dir + seg_class + ".nii.gz")

    def bias_corrected_approach(self) -> None:
        """
        Sub-routine for the bias corrected approach, where fast is run again on the cut area of the tumor segmentation.

        :return: None
        """
        tumor_files = []
        # just returns classification based on intensity
        for modality in self.input_files_dir:
            _, _, file = get_path_file_extension(modality)
            tumor_files.append(self.out_dir + os.sep + file + "-withTumor.nii.gz")
        StructureSegmentation.single_segmentation(self.out_dir + os.sep + "tumor_class",
                                                  tumor_files, len(list(self.tumor_class_mapping.keys())))
        for i, seg_class in enumerate(list(self.tumor_class_mapping.keys())):
            os.rename(self.out_dir + "tumor_class_pve_" + str(i) + ".nii.gz", self.out_dir + seg_class + ".nii.gz")

    def tumor_entity_weighted_approach(self) -> None:
        """
        Sub-routine for the tumor entity weighted approach, where the actual tumor segmentation is used to create masks
        for cuts of the original image. The original intensities are normalised, which gives three entities with
        non-binary distribution from 1 to 2 with an offset that allows also 0.

        :return: None
        """
        tumor_masks = {}
        for key, value in self.tumor_class_mapping.items():
            tumor_mask = StructureSegmentation.image2mask(self.tumor_seg_dir, value)
            tumor_masks[key] = nib.Nifti1Image(tumor_mask, self.affine)
        # get segmentation and separate in three classes, cut class-wise from mri and normalise
        for modality in self.input_files_dir:
            _, _, file = get_path_file_extension(modality)
            for key in tumor_masks:
                image = StructureSegmentation.cut_area_from_image(modality, tumor_masks[key], False)
                array = image.get_fdata()
                array[array == 0] = -1
                array = (array - array[array > 0].min()) / (array.max() - array[array > 0].min())
                array[array < 0] = -1
                array = array + 1
                image = nib.Nifti1Image(array, self.affine)
                nib.save(image, self.out_dir + os.sep + str(key) + ".nii.gz")

    def run(self) -> None:
        """
        Performs the structure segmentation with the given input files and selected mode. Creates a folder with output
        files.

        :return: None
        """
        if self.mode not in self.modes:
            raise ValueError(f"Error: Selected mode: {self.mode} is not implemented. Function 'list_modes()' prints the"
                             f" possible options.")
        if (self.mode is self.modes[1] or self.mode is self.modes[2]) and self.tumor_seg_dir is None:
            raise ValueError(f"Error: For selected mode '{self.mode}' the tumor_seg_dir should not be None.")

        mkdir_if_not_exist(self.out_dir)

        if self.mode == "tumor_agnostic":
            self.tumor_agnostic_mode()

        if self.mode in ["bias_corrected", "tumor_entity_weighted"]:
            self.split_tumor_from_brain()

            self.segment_brain_part()

            if self.mode == "bias_corrected":
                self.bias_corrected_approach()

            if self.mode == "tumor_entity_weighted":
                self.tumor_entity_weighted_approach()


        if self.remove_interim_files:
            files_to_remove = glob.glob(os.path.join(self.out_dir, '*Tumor.nii.gz'))
            files_to_remove.extend(glob.glob(os.path.join(self.out_dir, '*mixeltype.nii.gz')))
            files_to_remove.extend(glob.glob(os.path.join(self.out_dir, '*_pveseg.nii.gz')))
            files_to_remove.extend(glob.glob(os.path.join(self.out_dir, '*_seg.nii.gz')))
            for file_path in files_to_remove:
                try:
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
