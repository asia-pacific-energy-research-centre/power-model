#%%
import time
import os
import sys

import model_preparation_functions
import model_solving_functions
import post_processing_functions
import plotting_functions
import logging
import pickle as pickle
################################################################################
#LESS IMPORTANT VARIABLES TO SET (their default values are fine):
FILE_DATE_ID = time.strftime("%m-%d-%H%M")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
USE_TMP_FILES_FROM_PREVIOUS_RUN = False
DONT_SOLVE = False
plotting = True
SAVE_RESULTS_VIS_AND_INPUTS = True
EMPTY_TMP_FOLDER_BEFORE_RUNNING = True
################################################################################
#%%
print(os.getcwd())
# C:\GitHub\power-model\results\03-18-1613_19_THA_Target_coin_mip_TGT3\results
post_processing_functions.recreate_output_ebt_files('results/03-18-1613_19_THA_Target_coin_mip_TGT3/results/19_THA_results_Target_03-18-1613.xlsx', 'energy.csv', 'capacity.csv', '19_THA', 'Target')
#%%