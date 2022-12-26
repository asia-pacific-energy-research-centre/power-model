
#%%

import pandas as pd
import numpy as np
import yaml
import os
from pathlib import Path
from otoole.read_strategies import ReadExcel
from otoole.write_strategies import WriteDatafile
import subprocess
import time
import importlib.resources as resources

#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

#%%

def remove_duplicate_rows_from_datasheet(path_to_data_sheet):
    #intention is to remove duplicate rows from the spreadsheet

    #open the spreadsheet
    df = pd.read_excel(path_to_data_sheet, sheet_name=None)
    #loop through the sheets
    for sheet_name in df.keys():
        #identify the columns that aren't Years
        year_columns = [col for col in df[sheet_name].columns if col in range(1000, 3000)]
        non_year_cols = [col for col in df[sheet_name].columns if col not in range(1000, 3000)]
        
        #find duplicates in all columns first
        columns_to_search = non_year_cols + year_columns
        duplicate_rows = df[sheet_name].duplicated(subset=columns_to_search, keep=False)
        if sum(duplicate_rows) > 0:
            #remove all those duplicate rows except the first
            print('Sheet: ', sheet_name, ' has ', sum(duplicate_rows), ' duplicate rows. We will remove them all except the first occurences of each duplicate row')
            df[sheet_name] = df[sheet_name].drop_duplicates(subset=columns_to_search, keep='first')
        else:
            print('Sheet: ', sheet_name, ' has no completely duplicated rows')
        #Now in the rest of the rows, find duplicates in the non year columns. In these rows, the values in the year cols are different so we will show the user the rows and ask them what one to keep
        #identify the duplicate rows
        duplicate_rows = df[sheet_name].duplicated(subset=non_year_cols, keep=False)
        #if there are duplicate rows, tell the user what ones they are and then remove them (keep the first occurence even if the second occurence is different and could be more accurate)
        if sum(duplicate_rows) == 0:
            print('Sheet: ', sheet_name, ' has no more duplicate rows left in the non year columns')
            continue
        elif sum(duplicate_rows) > 0:
            #extract the duplicate rows
            duplicate_rows_df = df[sheet_name][duplicate_rows]
            #go through each set of duplicate rows and ask the user which one to keep (note that some duplicated rows may have been duplicated more than twice)
            duplicate_row_sets = duplicate_rows_df.groupby(non_year_cols).groups
            duplicate_row_sets_copy = duplicate_row_sets.copy()
            for non_year_cols_values in duplicate_row_sets.keys():

                #extract the duplicate rows
                duplicate_rows_df = df[sheet_name].loc[duplicate_row_sets[non_year_cols_values]]
                #show the user the duplicate rows
                print('\n\nThese are the duplicate rows in sheet: ', sheet_name, ' with values: ', non_year_cols_values, ':\n\n')
                print(duplicate_rows_df)
                ask_user = True
                while ask_user == True:
                    #ask the user which row to keep
                    options = [str(i) for i in duplicate_rows_df.index] + [''] + ['sheet']
                    print('Which row do you want to keep?')
                    for i in options:
                        if i == '':
                            print('Press enter to keep the first row')
                        elif i == 'sheet':
                            print('Type "sheet" to keep only the first row from all the duplicate rows in this sheet')
                        else:
                            print('Type ', i, ' to keep row ', i)

                    keep_row = input('Which row do you want to keep?')

                    if keep_row not in options:
                        print('You entered an invalid row number. Please try again.')
                    else:
                        if keep_row == '':
                            keep_row = duplicate_rows_df.index[0]
                            not_kept_rows = [i for i in duplicate_rows_df.index if i != keep_row]
                            ask_user = False

                        elif keep_row == 'sheet':
                            #keep only the first row from all the duplicate rows in this sheet
                            #first identify the rows to remove using duplicate_row_sets
                            not_kept_rows = []
                            for non_year_cols_values in duplicate_row_sets_copy.keys():
                                not_kept_rows += duplicate_row_sets_copy[non_year_cols_values][1:].tolist()
                            print('Keeping only the first row from all the duplicate rows in this sheet ', sheet_name)
                            ask_user = False

                        else:
                            keep_row = int(keep_row)
                            not_kept_rows = [i for i in duplicate_rows_df.index if i != keep_row]
                            ask_user = False

                #remove the rows we dont want to keep
                df[sheet_name] = df[sheet_name].drop(index=not_kept_rows)
                print('Removed the following rows:\n', not_kept_rows)

                #remove non_year_cols_values from a copy of duplicate_row_sets  since we have already dealt with it
                del duplicate_row_sets_copy[non_year_cols_values]

                if keep_row == 'sheet':
                    break
    ##%%
    #save the changes to the spreadsheet
    writer = pd.ExcelWriter(path_to_data_sheet, engine='openpyxl')
    for sheet_name in df.keys():
        df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
    writer.save()
#%%
def create_datapackage(path_to_data_sheet, path_to_data_package):
    #Run the script to create the datapackage.json file. If there are errors send the output to the function to fix the errors (fix_errors_in_datasheet()). Else this function will create the datapackage.json file
    error_thrown= True
    i= 0
    while error_thrown == True:
        i+=1
        print('\n\nAttempting to convert to datapackage. Attempt number: ', i)

        command = 'otoole convert excel datapackage {} {}'.format(path_to_data_sheet,path_to_data_package)

        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output, x= process.communicate()

        print('This is the output:\n', output)
        #check for errors
        if 'Error' in str(output):
            print('Error thrown. Fixing errors in data sheet')
            error_thrown = fix_errors_in_datasheet(str(output), path_to_data_sheet, path_to_data_package)
        elif 'Error' not in str(output):
            print('no error thrown, datapackage created')
            error_thrown = False

def fix_errors_in_datasheet(error_message, path_to_data_sheet):
    #this function will create a datapackage.json file in a folder of the same name, based on the data in the spreadsheet
    #Most of this function though will deal with fixing errors that are thrown when trying to create the datapackage.json file.
    #The errors are fixed by changing the spreadsheet and then trying to create the datapackage.json file again.
    #This will keep happening until the datapackage.json file is created without any errors.
    #Some errors will require the user to input a choice of how to fix the error.

        ############################################################################

        #if a column for the power model has been created where it is not part of the otoole standard, then remove it by searching for the string 'b"ValueError: invalid literal for int() with base 10: ' in the output. If it is there, then remove the column and save the spreadsheet again
        if 'b"ValueError: invalid literal for int() with base 10: ' in error_message:
            #extract the col from all sheets
            error_str = error_message
            col_name = error_str.split("'")[1]
            print('Removing col: ', col_name)
            df = pd.read_excel(path_to_data_sheet,sheet_name=None)
            for sheet_name in df.keys():
                if col_name in df[sheet_name].columns:
                    df[sheet_name] = df[sheet_name].drop(columns=[col_name])
            writer = pd.ExcelWriter(path_to_data_sheet, engine='openpyxl')
            for sheet_name in df.keys():
                df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
            writer.save()
            #save the spreadsheet again

        elif 'KeyError' in error_message:
            error_str = error_message
            sheet_name = error_str.split("'")[1]
            print('Removing sheet: ', sheet_name)
            #remove that sheet from the spreadsheet
            df = pd.read_excel(path_to_data_sheet,sheet_name=None)
            del df[sheet_name]
            writer = pd.ExcelWriter(path_to_data_sheet, engine='openpyxl')
            for sheet_name in df.keys():
                df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
            writer.save()
            #save the spreadsheet again

        ############################################################################
        #LONG Script to deal with na's in the data sheet:
        elif error_message == "b'IntCastingNaNError: Cannot convert non-finite values (NA or inf) to integer\\r\\n'":
            #na's in the data sheet (or inf but unlikely) are causing an error. #find the sheet that has the na's, name it and ask user what to do with them
            df = pd.read_excel(path_to_data_sheet,sheet_name=None)

            sheet_name_dict = {}
            for sheet_name in df.keys():
                if df[sheet_name].isna().values.any():
                    #find the row number and col name of the na's so that the user can easily find them
                    row_num_list = df[sheet_name].index[df[sheet_name].isna().any(axis=1)].to_list()
                    #create entry in dict which we will fill with tuples of the row number and the col name
                    sheet_name_dict[sheet_name] = []
                    for row_num in row_num_list:
                        na_cols = df[sheet_name].columns[df[sheet_name].isna().iloc[row_num]].to_list()
                        #for each col name, add a tuple of the row number and the col name to the list
                        for na_col in na_cols:
                            sheet_name_dict[sheet_name].append(('Row num: {}'.format(row_num),'Col name: {}'.format(na_col)))
            print('Sheets: ', list(sheet_name_dict.keys()), ' have na values')
            #looping through the sheets, ask the user if they would like to 0. print the row number and column name tuples and then choose an option  1. replace the na's with 0's, 2. remove the rows with na's, 3. remove the sheet or 4. break the script and fix the na's manually

            for sheet_name in sheet_name_dict.keys():
                print('Sheet: ', sheet_name, ' has {} na values'.format(len(sheet_name_dict[sheet_name])))
                options_list = ['0: print the row number and column name tuples', '1: replace the na values with 0', '2: remove the rows with na values', '3: remove the sheet', '4: break the script and fix the na values manually']
                option_0 = True
                while option_0 == True:
                    print('What would you like to do with the na values?')
                    for option in options_list:
                        print(option)
                    option = input('Choose an option: ')
                    if option == '0':
                        print(sheet_name_dict[sheet_name])
                    elif option == '1':
                        print('Replacing na values with 0')
                        df[sheet_name] = df[sheet_name].fillna(0)
                        option_0 = False
                    elif option == '2':
                        print('Removing rows with na values')
                        df[sheet_name] = df[sheet_name].dropna()
                        option_0 = False
                    elif option == '3':
                        print('Removing sheet: ', sheet_name)
                        del df[sheet_name]
                        option_0 = False
                    elif option == '4':
                        print('Breaking the script')
                        break
                    else:
                        print('Option not recognised, please try again')
                if option == '4': 
                    #save what changes have been made so far
                    writer = pd.ExcelWriter(path_to_data_sheet, engine='openpyxl')
                    for sheet_name in df.keys():
                        df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
                    writer.save()
                    break
            if option != '4':
                print('All na values have been dealt with. Saving the changes to the spreadsheet')
                writer = pd.ExcelWriter(path_to_data_sheet, engine='openpyxl')
                for sheet_name in df.keys():
                    df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
                writer.save()

        ############################################################################
        elif 'b"ValueError: could not convert string to float: ' in error_message:
            #Words in cells where there should be numbers are causing an error. #find the sheet that has the issue and ask user what to do with it
            df = pd.read_excel(path_to_data_sheet,sheet_name=None)

            #extract the word from the error message
            error_str = error_message
            bad_word = error_str.split("'")[1]
            print('The word: ', bad_word, ' is causing an error')

            #find the word in the spreadsheet
            sheet_name_dict = {}
            for sheet_name in df.keys():
                if df[sheet_name].isin([bad_word]).values.any():
                    #find the row number and col name of word so that the user can easily find it
                    row_num_list = df[sheet_name].index[df[sheet_name].isin([bad_word]).any(axis=1)].to_list()
                    #create entry in dict which we will fill with tuples of the row number and the col name
                    sheet_name_dict[sheet_name] = []
                    for row_num in row_num_list:
                        na_cols = df[sheet_name].columns[df[sheet_name].isin([bad_word]).iloc[row_num]].to_list()
                        #for each col name, add a tuple of the row number and the col name to the list
                        for na_col in na_cols:
                            sheet_name_dict[sheet_name].append(('Row num: {}'.format(row_num),'Col name: {}'.format(na_col)))
            print('Sheets: ', list(sheet_name_dict.keys()), ' have the word')
            #looping through the sheets, ask the user if they would like to 0. print the row number and column name tuples and then choose an option  

            for sheet_name in sheet_name_dict.keys():
                print('Sheet: ', sheet_name, ' has {} instances of the word'.format(len(sheet_name_dict[sheet_name])))
                options_list = ['0: print the row number and column name tuples', '1: replace the word with 0', '2: remove the rows with the word', '3: remove the sheet', '4: break the script and fix the word manually']
                option_0 = True
                while option_0 == True:
                    print('What would you like to do with the word?')
                    for option in options_list:
                        print(option)
                    option = input('Choose an option: ')
                    if option == '0':
                        print(sheet_name_dict[sheet_name])
                    elif option == '1':
                        print('Replacing word with 0')
                        df[sheet_name] = df[sheet_name].replace(bad_word, 0)
                        option_0 = False
                    elif option == '2':
                        print('Removing rows with the word')
                        df[sheet_name] = df[sheet_name].replace(bad_word, np.nan)
                        df[sheet_name] = df[sheet_name].dropna()
                        option_0 = False
                    elif option == '3':
                        print('Removing sheet: ', sheet_name)
                        del df[sheet_name]
                        option_0 = False
                    elif option == '4':
                        print('Breaking the script')
                        break
                    else:
                        print('Option not recognised, please try again')
                if option == '4': 
                    #save what changes have been made so far
                    writer = pd.ExcelWriter(path_to_data_sheet, engine='openpyxl')
                    for sheet_name in df.keys():
                        df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
                    writer.save()
                    break
            if option != '4':
                print('All instances of the word have been dealt with. Saving the changes to the spreadsheet')
                writer = pd.ExcelWriter(path_to_data_sheet, engine='openpyxl')
                for sheet_name in df.keys():
                    df[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)
                writer.save()
        else:
            print('error thrown but not sure what it is, please check the output')
            print('output: ', output)
            return False
        return True
        ############################################################################



# %%
