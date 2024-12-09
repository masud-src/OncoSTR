"""
This is the base entry point of OncoSTR. OncoSTR splits in a module 'structure_segmentation' that holds all necessary
functions for the user and 'utils.py' file, where sub-ordinate functions are gathered.

Modules:
    structure_segmentation: Its the control file for all functionalities for the user.
    utils                 : Herein, helper functions are hold, in order to keep the other file clean for the user.
"""
from .structure_segmentation import StructureSegmentation