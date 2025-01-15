"""
In this structure segmentation module the heterogeneous distributions are identified.

Class:
    StructureSegmentation:      Basically uses fast of FSL for the segmentation. Herein, a mixture of Gaussian
                                distributes the relevant classes of white and grey matter and cerebrospinal fluid in the
                                brain area.
"""
import nibabel as nib
import os
import glob
from . import utils

STRUCTURE_SEGMENTATION_PATH = "structure_segmentation" + os.path.sep
MODES = ["tumor_agnostic", "bias_corrected", "tumor_entity_weighted"]


class StructureSegmentation:
    """
    The StructureSegmentation class holds all options and functions for the segmentation of structural MRI modalities.
    With this entity the organ is split into its basic compartments. Basically, fast of FSL is used for the
    segmentation. Herein, a mixture of Gaussian distributes the relevant classes of white and grey matter and
    cerebrospinal fluid in the brain area.

    *Attributes*:
        work_dir:                   Directory of workspace, can be set as argument or actual workspace is set
        input_files_dir:            List of the input images. It is recommended to only use one image.
        affine:                     Variable for the image affine, every segmentation is mapped
        remove_interim_files:       Bool to remove the created interim files
        mode:                       Selected mode of segmentation
        brain_handling_classes:     List of brain compartment classes, it should be segmented to
        tumor_class_mapping:        Dict of tumor classes with a respective mapping according to brats segmentation

    Methods
        set_input_structure_seg:        Sets the list of input files
        list_modes:                     prints all implemented modes
        set_affine:                     STATIC, sets affine and shape of first measure of included state.
        split_tumor_from_brain:         Splits the tumor area from the brain area and saves the images
        segment_brain_part:             Segments only the healthy brain part
        tumor_agnostic:                 Segmentation by ignoring the distorted tumor area
        bias_corrected:                 Segmentation according the bias corrected approach
        tumor_entity_weighted:          Segmentation according the tumor entity weighted approach
        run:                            Runs the segmentation
    """

    def __init__(self, work_dir=None):
        if work_dir is None:
            work_dir = os.getcwd() + os.sep
        if not work_dir.endswith(os.sep):
            work_dir = work_dir + os.sep
        self.work_dir = work_dir
        self.input_files_dir = None
        self.tumor_seg_dir = None
        self.affine = None
        self.remove_interim_files = True
        self.mode = "bias_corrected"
        self.brain_handling_classes = ["cerebrospinal_fluid", "gray_matter", "white_matter"]
        self.tumor_class_mapping = {"edema": 2, "active": 4, "necrotic": 1}

    def set_input_structure_seg(self, input_files_dir: list, tumor_seg_dir: str = None) -> None:
        """
        Set input files of structure segmentation.

        :param input_files_dir: List, takes all structural input files gathered in a list. Should be in (t1, t1ce, t2,
        flair)
        :param tumor_seg_dir: tumor segmentation file. Corresponds to tumor segmentation file from tumor segmentation
        """
        self.input_files_dir = input_files_dir
        self.tumor_seg_dir = tumor_seg_dir

    @staticmethod
    def list_modes() -> None:
        """
        List all implemented modes of structure segmentation.

        :return: None
        """
        print(MODES)

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
        out_dir = utils.set_out_dir(self.work_dir, STRUCTURE_SEGMENTATION_PATH)
        utils.mkdir_if_not_exist(out_dir)
        seg_id = list(self.tumor_class_mapping.values())
        tumor_mask = utils.image2mask(self.tumor_seg_dir, seg_id[0], seg_id[1:])
        self.set_affine()
        image_tumor_mask = nib.Nifti1Image(tumor_mask, self.affine)
        for modality in self.input_files_dir:
            _, _, file = utils.get_path_file_extension(modality)
            for b in [True, False]:
                if b:
                    image = utils.cut_area_from_image(modality, image_tumor_mask, True)
                    nib.save(image, out_dir + file + "-woTumor.nii.gz")
                else:
                    image = utils.cut_area_from_image(modality, image_tumor_mask, False)
                    nib.save(image, out_dir + file + "-withTumor.nii.gz")

    def segment_brain_part(self) -> None:
        """
        Segments the undistorted brain part. Therefore, function 'split_tumor_from_brain' need to be run before or
        files with the ending '-woTumor.nii.gz' need to be preserved. Segments according to the brain_handling_classes
        and renames the files according to them.

        :return: None
        """
        out_dir = utils.set_out_dir(self.work_dir, STRUCTURE_SEGMENTATION_PATH)
        utils.mkdir_if_not_exist(out_dir)
        brain_files = []
        for modality in self.input_files_dir:
            _, _, file = utils.get_path_file_extension(modality)
            brain_files.append(out_dir + file + "-woTumor.nii.gz")

        utils.single_segmentation(out_dir + "wms_Brain", brain_files,
                                  len(self.brain_handling_classes))
        for i, seg_class in enumerate(self.brain_handling_classes):
            os.rename(out_dir + "wms_Brain_pve_" + str(i) + ".nii.gz", out_dir + seg_class + ".nii.gz")

    def tumor_agnostic(self) -> None:
        """
        Runs tumor agnostic segmentation mode. The files are simply segmented like no tumor is present.

        :return: None
        """
        out_dir = utils.set_out_dir(self.work_dir, STRUCTURE_SEGMENTATION_PATH)
        utils.mkdir_if_not_exist(out_dir)
        utils.single_segmentation(out_dir, self.input_files_dir, len(self.brain_handling_classes))
        for i, seg_class in enumerate(self.brain_handling_classes):
            os.rename(out_dir + "_pve_" + str(i) + ".nii.gz", out_dir + seg_class + ".nii.gz")

    def bias_corrected(self) -> None:
        """
        Sub-routine for the bias corrected approach, where fast is run again on the cut area of the tumor segmentation.

        :return: None
        """
        out_dir = utils.set_out_dir(self.work_dir, STRUCTURE_SEGMENTATION_PATH)
        utils.mkdir_if_not_exist(out_dir)
        self.split_tumor_from_brain()
        self.segment_brain_part()

        tumor_files = []
        # just returns classification based on intensity
        for modality in self.input_files_dir:
            _, _, file = utils.get_path_file_extension(modality)
            tumor_files.append(out_dir + os.sep + file + "-withTumor.nii.gz")
        utils.single_segmentation(out_dir + os.sep + "tumor_class", tumor_files,
                                  len(list(self.tumor_class_mapping.keys())))
        for i, seg_class in enumerate(list(self.tumor_class_mapping.keys())):
            os.rename(out_dir + "tumor_class_pve_" + str(i) + ".nii.gz", out_dir + seg_class + ".nii.gz")

    def tumor_entity_weighted(self) -> None:
        """
        Sub-routine for the tumor entity weighted approach, where the actual tumor segmentation is used to create masks
        for cuts of the original image. The original intensities are normalised, which gives three entities with
        non-binary distribution from 1 to 2 with an offset that allows also 0.

        :return: None
        """
        out_dir = utils.set_out_dir(self.work_dir, STRUCTURE_SEGMENTATION_PATH)
        utils.mkdir_if_not_exist(out_dir)
        self.split_tumor_from_brain()
        self.segment_brain_part()
        tumor_masks = {}
        for key, value in self.tumor_class_mapping.items():
            tumor_mask = utils.image2mask(self.tumor_seg_dir, value)
            tumor_masks[key] = nib.Nifti1Image(tumor_mask, self.affine)
        # get segmentation and separate in three classes, cut class-wise from mri and normalise
        for modality in self.input_files_dir:
            _, _, file = utils.get_path_file_extension(modality)
            for key in tumor_masks:
                image = utils.cut_area_from_image(modality, tumor_masks[key], False)
                array = image.get_fdata()
                array[array == 0] = -1
                array = (array - array[array > 0].min()) / (array.max() - array[array > 0].min())
                array[array < 0] = -1
                array = array + 1
                image = nib.Nifti1Image(array, self.affine)
                nib.save(image, out_dir + os.sep + str(key) + ".nii.gz")

    def run(self) -> None:
        """
        Performs the structure segmentation with the given input files and selected mode. Creates a folder with output
        files.

        :return: None
        """
        if self.mode not in MODES:
            raise ValueError(f"Error: Selected mode: {self.mode} is not implemented. Function 'list_modes()' prints the"
                             f" possible options.")
        if (self.mode is MODES[1] or self.mode is MODES[2]) and self.tumor_seg_dir is None:
            raise ValueError(f"Error: For selected mode '{self.mode}' the tumor_seg_dir should not be None.")

        out_dir = utils.set_out_dir(self.work_dir, STRUCTURE_SEGMENTATION_PATH)
        utils.mkdir_if_not_exist(out_dir)

        if self.mode == "tumor_agnostic":
            self.tumor_agnostic()

        if self.mode == "bias_corrected":
            self.bias_corrected()

        if self.mode == "tumor_entity_weighted":
            self.tumor_entity_weighted()

        if self.remove_interim_files:
            files_to_remove = glob.glob(os.path.join(out_dir, '*Tumor.nii.gz'))
            files_to_remove.extend(glob.glob(os.path.join(out_dir, '*mixeltype.nii.gz')))
            files_to_remove.extend(glob.glob(os.path.join(out_dir, '*_pveseg.nii.gz')))
            files_to_remove.extend(glob.glob(os.path.join(out_dir, '*_seg.nii.gz')))
            for file_path in files_to_remove:
                try:
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
