


import pandas as pd
import yaml
import os
from otoole.read_strategies import ReadExcel
from otoole.write_strategies import WriteDatafile
import shutil

#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

def import_run_preferences(root_dir, input_data_sheet_file):

    df_prefs = pd.read_excel(f'{root_dir}/data/{input_data_sheet_file}', sheet_name='START',usecols="A:B",nrows=3,header=None)

    economy = df_prefs.loc[0][1]
    scenario = df_prefs.loc[1][1]
    years = df_prefs.loc[2][1]

    config_dict = {}
    config_dict['economy'] = economy
    config_dict['years'] = years
    config_dict['scenario'] = scenario

    #print the config_dict details
    print(f'Running model for economy: {economy}, scenario: {scenario}, upto year: {years}')
    return config_dict, economy, scenario, years

def set_up_paths(scenario, economy, root_dir, config_dir, results_config_file,data_config_file, input_data_sheet_file,osemosys_cloud):

    if osemosys_cloud:
        scenario_folder=f'cloud_{scenario}'
    else:
        scenario_folder=f'{scenario}'
    
    tmp_directory = f'./tmp/{economy}/{scenario_folder}'
    results_directory = f'./results/{economy}/{scenario_folder}'

    if not os.path.exists(tmp_directory):
        os.makedirs(tmp_directory)
    if not os.path.exists(results_directory):
        os.makedirs(results_directory)

    path_to_results_config = f'{root_dir}/{config_dir}/{results_config_file}'
    path_to_data_config = f'{root_dir}/{config_dir}/{data_config_file}'

    if not os.path.exists(path_to_results_config):
        print(f'WARNING: results config file {path_to_results_config} does not exist')
    if not os.path.exists(path_to_data_config):
        print(f'WARNING: data config file {path_to_data_config} does not exist')

    
    path_to_data_workbook = f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'

    input_data_file_path=f"{root_dir}/data/{input_data_sheet_file}"

    path_to_combined_data_sheet=f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'

    path_to_input_data_file = f'{tmp_directory}/datafile_from_python_{economy}_{scenario}.txt'
     
    #create path to save copy of outputs to txt file in case of error:
    log_file_path = f'{tmp_directory}/process_log_{economy}_{scenario}.txt'

    #TODO implement something like https://stackoverflow.com/questions/24849998/how-to-catch-exception-output-from-python-subprocess-check-output

    cbc_intermediate_data_file_path = f'{tmp_directory}/cbc_input_{economy}_{scenario}.lp'
    cbc_results_data_file_path=f'{tmp_directory}/cbc_results_{economy}_{scenario}.txt'

    #PUT EVERYTHING IN A DICTIONARY
    paths_dict = {}
    paths_dict['tmp_directory'] = tmp_directory
    paths_dict['results_directory'] = results_directory
    paths_dict['path_to_results_config'] = path_to_results_config
    paths_dict['path_to_data_config'] = path_to_data_config
    paths_dict['path_to_data_workbook'] = path_to_data_workbook
    paths_dict['input_data_file_path'] = input_data_file_path
    paths_dict['path_to_combined_data_sheet'] = path_to_combined_data_sheet
    paths_dict['path_to_input_data_file'] = path_to_input_data_file
    paths_dict['log_file_path'] = log_file_path
    paths_dict['cbc_intermediate_data_file_path'] = cbc_intermediate_data_file_path
    paths_dict['cbc_results_data_file_path'] = cbc_results_data_file_path

    return paths_dict

def import_data_config(paths_dict):

    with open(paths_dict['path_to_data_config']) as f:
        data_config = yaml.safe_load(f)

    ##change to handle v1.0 of otoole:
    #create dataconfig with short_name as key so that its keys can be compared to the keys in the data sheet
    short_to_long_name = {}
    new_dict = data_config.copy()
    for key in data_config.keys():
        #check if there is a short_name
        if 'short_name' not in data_config[key]:
            continue
        short_to_long_name[data_config[key]['short_name']] = key
        new_key = data_config[key]['short_name']
        new_dict[new_key] = new_dict.pop(key)
    #replace data_config with new_dict
    data_config_short_names = new_dict.copy()

    return data_config_short_names, short_to_long_name, data_config


def import_and_clean_data(data_config_short_names, economy,scenario,paths_dict):
    # read in the data file and filter based on the specific scenario and preferences
    subset_of_economies = economy
    input_data_raw = pd.read_excel(paths_dict['input_data_file_path'],sheet_name=None) # creates dict of dataframes
    print("Excel file successfully read.\n")    
    #keep only sheets in dict where we have a key for it in the data_config (although since some sheets have shortened names we need to use data_config_short_names)
    input_data = {}
    for key,value in input_data_raw.items():
        if key in data_config_short_names.keys():
            input_data[key] = value
    #filter based on preferences.
    #also, remove UNIT and NOTES columns since they arent in indices or a year column.
    filtered_data = {}
    for key,value in input_data.items():
        sheet = input_data[key]
        if 'SCENARIO' in sheet.columns:
            sheet = sheet[sheet['SCENARIO']==scenario].drop(['SCENARIO'],axis=1)
        if 'REGION' in sheet.columns:
            sheet = sheet[sheet['REGION']==subset_of_economies]
        if key == 'REGION':
            sheet = sheet[sheet['VALUE']==subset_of_economies]
        if 'UNITS' in sheet.columns:
            sheet = sheet.drop(['UNITS'],axis=1)
        if 'NOTES' in sheet.columns:
            sheet = sheet.drop(['NOTES'],axis=1)

        sheet = sheet.loc[(sheet != 0).any(axis=1)] # remove rows if all are zero
        #drop duplicates
        sheet = sheet.drop_duplicates()
        filtered_data[key] = sheet

    return filtered_data

def write_data_to_tmp(filtered_data, config_dict, paths_dict):
    with pd.ExcelWriter(paths_dict['path_to_data_workbook']) as writer:
        for k, v in filtered_data.items():
            v.to_excel(writer, sheet_name=k, index=False, merge_cells=False)
    print("Combined file of Excel input data has been written to the tmp folder.\n")

    # The data needs to be converted from the Excel format to the text file format. We use otoole for this task.
    subset_of_years = config_dict['years']

    return subset_of_years


def prepare_data_for_osemosys(data_config_short_names, data_config, paths_dict,subset_of_years):
    reader = ReadExcel(user_config=data_config)
    writer = WriteDatafile(user_config=data_config)
    data, default_values = reader.read(paths_dict['path_to_combined_data_sheet'])
    
    # Filter for the years we want
    filtered_data2 = {}
    for key in data_config.keys():
        _df = data[key]
        if data_config[key]['type'] == 'param':
            if ('YEAR' in data_config[key]['indices']):
                #print('parameters with YEAR are.. {}'.format(key))
                _df2 = _df.query('YEAR < @subset_of_years+1')
                filtered_data2[key] = _df2
            else:
                #print('parameters without YEAR are.. {}'.format(key))
                filtered_data2[key] = _df
        elif data_config_short_names[key]['type'] == 'set':
            if key == 'YEAR':
                _df2 = _df.query('VALUE < @subset_of_years+1')
                filtered_data2[key] = _df2
            else:
                #print('sets are.. {}'.format(key))
                filtered_data2[key] = _df
        else:
            filtered_data2[key] = _df

    writer.write(filtered_data2, paths_dict['path_to_input_data_file'], default_values)
    
    print(f"Data file in text format has been written and saved in the tmp folder as {paths_dict['path_to_input_data_file']}. This is the file you would use in OsEMOSYS Cloud as data if you are using that.\n")
    return 

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
    for key in data_config.keys():
        if data_config[key]['type'] == 'param':#assumption that param is the type of data we check. should double check this
            columns = data_config[key]['indices']
            df = combined_data[key]
            for column in columns:
                if column == 'YEAR':
                    continue
                if column not in df.columns:
                    print('column {} is missing from dataframe {}'.format(column,key))
    #likewise, check if we have any columns in the combined_data file that are not in the data_config file, except the 4 digit year columns and the NOTES and UNIT columns
    for key in combined_data.keys():
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

def prepare_osemosys_model_script_for_cbc():
    #this is a function prepared in case we need to decrease the size of some vraiables in the osemosys model script to make it work with cbc. This is because we get errors like  ### CoinLpIO::is_invalid_name(): Name SC4_UpperLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInLastWeekConstraint('19_THA',BAT,3,2,4,2022) is too long in the output when running cbc ./tmp/19_THA/Reference/cbc_input_19_THA_Reference.lp solve solu ./tmp/19_THA/Reference/cbc_results_19_THA_Reference.txt
    # They variable names in question are stated below, although it is not clear yet that they should be changed:
    long_vars = ['SC4_UpperLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInLastWeekConstraint','SC1_LowerLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInFirstWeekConstraint', 'SC3_LowerLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInFirstWeekConstraint', 'SC2_LowerLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInFirstWeekConstraint']
    return


def prepare_model_script(economy, scenario, root_dir, config_dir, osemosys_model_script, osemosys_cloud,paths_dict):
    #either modfiy the model script if it is being used locally so the resultsPath is in tmp_directory, or if it is being used in the cloud, then just move the model script to the tmp_directory for ease of access
    paths_dict['osemosys_model_script_path'] = f'{root_dir}/{config_dir}/{osemosys_model_script}'

    tmp_directory = paths_dict['tmp_directory']
    paths_dict['new_osemosys_model_script_path'] = f'{tmp_directory}/model_{economy}_{scenario}.txt'
    if not osemosys_cloud:

        with open(paths_dict['osemosys_model_script_path']) as t:
            model_text = t.read()
        f = open(paths_dict['new_osemosys_model_script_path'],'w')
        f.write('%s\n'% model_text)
        f.close()

        # Read in the file again to modify it
        with open(paths_dict['new_osemosys_model_script_path'], 'r') as file:
            filedata = file.read()
        # Replace the target string
        filedata = filedata.replace("param ResultsPath, symbolic default 'results';",f"param ResultsPath, symbolic default '{paths_dict['tmp_directory']}';")#this makes it so that the results are saved in the tmp directory before we format them

        # Write the file out again
        with open(paths_dict['new_osemosys_model_script_path'], 'w') as file:
            file.write(filedata)
    else:
        shutil.copy(paths_dict['osemosys_model_script_path'], paths_dict['new_osemosys_model_script_path'])

    print(f'\n######################## \n Running solve process using {osemosys_model_script}')

    return paths_dict