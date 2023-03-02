#The intention of this scirpt is to complete the work needed to create a visualisation of the power model using otoole's viz command. 

#instruction for using this script:

#To create a datapackage.json file based on a datasheet:
# Write the path to the datasheet into the variable below (path_to_data_sheet). Then run the create_datapackage(path_to_data_sheet, path_to_data_package):
#it will attempt to convert the datasheet into a datapackage. If it fails, it will fix the error unless the error is unexpected. Some errors will require the user input to choose how to fix the error. It will keep trying to run the otoole convert excel datapackage {} {}'.format(path_to_data_sheet,path_to_data_package) and fixing errors until it succeeds with no error. Then it will print 'no error thrown' and you will have a datapackage.json file, although it will have had changes made to it so its not exactly the same as the original datasheet. 

#Now with the datapackage.json file, you can then use it to:
#create a visualisation of the data using the command: otoole viz res DATAPACKAGE res.png && open res.png

#NOTE THAT IT LOOKS LIKE THE DATAPACKAGE FORMAT HAS BEEN DEPRECATED. SO WE SHOULD UPDATE THIS SCRIPT TO USE THE NEW FORMAT. https://otoole.readthedocs.io/en/latest/functionality.html#otoole-viz

#%%
import pandas as pd
import numpy as np
import yaml
import os
from pathlib import Path
from otoole.read_strategies import ReadExcel
from otoole.write_strategies import WriteDatafile
from utility_functions import remove_duplicate_rows_from_datasheet, create_datapackage
import subprocess
import time
import importlib.resources as resources

#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

RUN_VISUALISATION = True

#%%
###############################################
#CREATE DATA PACKAGE USING create_datapackage function
path_to_data_sheet='./data/data-sheet-power-for-visualisation.xlsx'
path_to_data_package = path_to_data_sheet.replace('.xlsx','-datapackage-folder')
create_datapackage(path_to_data_sheet, path_to_data_package)

###############################################
# %%

if RUN_VISUALISATION:
    #run visualisation tool
    #https://otoole.readthedocs.io/en/latest/

    #PLEASE NOTE THAT THE VIS TOOL REQUIRES THE PACKAGE pydot TO BE INSTALLED. IF IT IS NOT INSTALLED, IT WILL THROW AN ERROR. TO INSTALL IT, RUN THE FOLLOWING COMMAND IN THE TERMINAL: pip install pydot OR conda install pydot
    #first need to load in the original spreadsheet, remove duplicates in all sheets and then convert it as a datapackage again this is because the datapackage created by the datapackage tool may have duplicates in it
    remove_duplicate_rows_from_datasheet(path_to_data_sheet)
    create_datapackage(path_to_data_sheet, path_to_data_package)

    ###############################################

    #For some reason we cannot make the terminal command work in python, so we have to run it in the terminal. The following command will print the command to run in the terminal:

    #otoole viz res DATAPACKAGE res.png && open res.png
    #extract the path to the datapackage so we can put the visualisation in the same folder
    #create name of visualisation file by adding the name datapackage.json to the end and then replaceing the .json with .png
    path_to_data_package_plus_file = path_to_data_package + '/datapackage.json'
    path_to_visualisation = path_to_data_package_plus_file.replace('.json', '.png')
    command = 'otoole viz res {} {} && start {}'.format(path_to_data_package_plus_file, path_to_visualisation, path_to_visualisation)
    print('Please run this command in the terminal in the root directory for this repo (./power-model/): \n', command)
    # process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    # output = process.stdout.readlines()
    # print('output: ', output)

#%%
###############################################
