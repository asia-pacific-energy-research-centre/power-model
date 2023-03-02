import pandas as pd
import numpy as np

def compare_combined_data_to_data_config(data_config,combined_data):
    """
    check if the data_config file is correct
    """
    ###########
    #is this one necessary?
    #check if the data_config file has all the keys that are in the combined_data file
    for key in combined_data.keys():
        if key not in data_config.keys():
            print('key {} is missing from data_config file'.format(key))
    #check if the data_config file has all the keys that are in the combined_data file
    for key in data_config.keys():
        if key not in combined_data.keys():
            print('key {} is missing from combined_data file'.format(key))
    ###########
    #check where we are missing columns in the combined_data file by checking for each dataframe in combined_data if it has the columns that are in it's corresponding entry in contents where contents['indices'] are the columns
    #but for now ignore year because the data is wide and i think it is ok to have it this way
    for key,value in data_config.items():
        if data_config[key]['type'] == 'param':#assumption that param is the type of data we check. should double check this
            columns = data_config[key]['indices']
            df = combined_data[key]
            for column in columns:
                if column == 'YEAR':
                    continue
                if column not in df.columns:
                    print('column {} is missing from dataframe {}'.format(column,key))
    #likewise, check if we have any columns in the combined_data file that are not in the data_config file, except the 4 digit year columns and the NOTES and UNIT columns
    for key,value in combined_data.items():
        if data_config[key]['type'] == 'param':#assumption that param is the type of data we check. should double check this
            columns = data_config[key]['indices']
            df = combined_data[key]
            for column in df.columns:
                #if col is 4 digit year, skip
                if str(column).isdigit() and len(str(column)) == 4:
                    continue
                #if col is NOTES or UNIT, skip
                if column == 'NOTES' or column == 'UNIT':
                    continue
                if column not in columns:
                    print('column {} is missing from data_config file from the sheet {}'.format(column,key))
    ########### 

    #finish
    return