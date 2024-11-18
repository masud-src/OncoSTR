"""
MRI structure segmentation tutorial

In order to perform the structure segmentation first a study is set in order to generate a workspace and an input state
is initialized that can be handed to the mri object. Before the structure segmentation can be used first the actual
segmentation of the tumor distribution needs to be set via initializing of the tumor segmentation entity. Here, the
segmentation file argument can be set manually and to identify the different zones of the tumor, the compartment masks
are evaluated using 'set_compartment_masks()'.
Again, first the object needs to be initialized and bind to its structural entity. To do so, the command
'set_structure_segmentation' is used and the method about regarding the tumor distributed area can be chosen. Here, the
user has the choice between the 'tumor_entity_weighted' approach from tutorial "tut_01_quickstart" or use the
"bias_corrected" approach. For input of the structure segmentation the user can change the list of the structural input
files. Best results have been with just the t1 modality.

Besides the choice of the handling of the tumor distributed area, the user can set the number of the healthy and tumor
tissue classes with:

mri.structure_segmentation.tumor_handling_classes = 3
mri.structure_segmentation.brain_handling_classes = 3

The default is set to both to 3.
"""
import oncostr as os
########################################################################################################################
# INPUT
struct_images = []
struct_images.append("data/BraTS20_Training_001_t1.nii.gz")
struct_images.append("data/BraTS20_Training_001_t1ce.nii.gz")
struct_images.append("data/BraTS20_Training_001_t2.nii.gz")
struct_images.append("data/BraTS20_Training_001_flair.nii.gz")
seg_image = ("data/BraTS20_Training_001_seg.nii.gz")
########################################################################################################################
# STRUCTURE SEGMENTATION
str_seg = os.StructureSegmentation()

str_seg.work_dir = "tumor_agnostic"
str_seg.set_input_structure_seg(struct_images)
str_seg.mode = "tumor_agnostic"
str_seg.run()

str_seg.work_dir = "bias_corrected"
str_seg.set_input_structure_seg(struct_images, seg_image)
str_seg.mode = "bias_corrected"
str_seg.run()

str_seg.work_dir = "tumor_entity_weighted"
del struct_images[1:]
str_seg.set_input_structure_seg(struct_images, seg_image)
str_seg.mode = "tumor_entity_weighted"
str_seg.run()

