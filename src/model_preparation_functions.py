


import pandas as pd
import yaml
import os
from otoole.read_strategies import ReadExcel
from otoole.write_strategies import WriteDatafile
import shutil
import sys
import copy
import time
import subprocess

#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

def import_run_preferences(root_dir, input_data_sheet_file):
    """extract the data we want to run the model on using the first sheet in the input data sheet called START. This defines the economy, scenario and years we want to run the model for."""
    df_prefs = pd.read_excel(f'{root_dir}/data/{input_data_sheet_file}', sheet_name='START',usecols="A:B",nrows=3,header=None)

    economy = df_prefs.loc[0][1]
    scenario = df_prefs.loc[1][1]
    years = df_prefs.loc[2][1]

    config_dict = {}
    config_dict['economy'] = economy
    config_dict['years'] = years
    config_dict['scenario'] = scenario

    #print the config_dict details
    print(f'Running model for economy: {economy}, scenario: {scenario}, for years up to and including: {years}')
    return config_dict, economy, scenario, years


def check_indices_in_data_config(data_config, osemosys_cloud):

    #first get names of possible idnices in the data config which are the keys where type: set
    data_config_indices = [key for key in data_config.keys() if data_config[key]['type'] == 'set']
    #now make assumptions about what indices these should be:

    #if indices are not in this list then throw an error
    possible_indices = ['DAILYTIMEBRACKET',
    'DAYTYPE',
    'EMISSION',
    'FUEL',
    'MODE_OF_OPERATION',
    'REGION',
    'SEASON',
    'STORAGE',
    'TECHNOLOGY',
    'TIMESLICE',
    'YEAR']

    if not all([index in possible_indices for index in data_config_indices]):
        raise ValueError('The indices in the data_config are not all in the list of possible indices. Make sure none of them have a spelling mistake. \n The possible indices are: \n {}'.format(possible_indices))

    if osemosys_cloud:
        #we need to make sure the order of some indices is correct because osemosys cloud expects this:
        selected_indices_order = [
            'TECHNOLOGY',
            'FUEL',
            'STORAGE',
            'EMISSION',
            'MODE_OF_OPERATION',
            'YEAR'
            ]
        non_ordered_indices = [index for index in data_config_indices if index not in selected_indices_order]

        #check that every indices list contains their indices in the correct order:
        #note that all the indices will not always be there. So we just nee to check that if they are there then they are in the correct order. i.e. if the indices are ['TECHNOLOGY','FUEL','YEAR'] then we need to check that they are in the correct order (which they are). But, if they were in the order ['FUEL','TECHNOLOGY','YEAR'] then we would need to throw an error.
        #Also not that the non ordered indices should al
        for key in data_config:
            if data_config[key]['type'] == 'param':
                indices = data_config[key]['indices']
                indices_in_selected_indices_order = [index for index in indices if index in selected_indices_order]
                if len(indices_in_selected_indices_order) > 1:
                    #starting from the first indice, check that the indice ahead of ti is also ahead of it in the selected_indices_order list
                    for i in range(len(indices_in_selected_indices_order)-1):
                        if selected_indices_order.index(indices_in_selected_indices_order[i]) > selected_indices_order.index(indices_in_selected_indices_order[i+1]):
                            raise ValueError(f'The indices {indices_in_selected_indices_order} in the data_config are not in the correct order for {data_config[key]}. Make sure that the indices are in the correct order. \n These indices need to have the order: \n {selected_indices_order}')
        
def import_data_config(paths_dict,osemosys_cloud):
        
    accepted_types = ['param','set','result']
    #import then recreate dataconfig with short_name as key so that its keys can be compared to the name of the corresponding data sheet in our input data
    data_config = yaml.safe_load(open(paths_dict['path_to_data_config']))

    #first check data_config for anything that isnt in accepted_types
    types = [data_config[key]['type'] for key in data_config.keys()]
    if not all([type in accepted_types for type in types]):
        raise ValueError('Data config contains a type that is not expected. Accepted types are: {}'.format(accepted_types))

    #we want result keys that are calculated to be in the results_keys list. These are the names of the sheets we will create in the output data file.
    results_sheets = [key for key in data_config.keys() if data_config[key]['type'] == 'result' and data_config[key]['calculated'] == True]

    #repalce any keys with their short_name if they have one
    short_name_keys = [key for key in data_config.keys() if 'short_name' in data_config[key].keys()]
    for key in short_name_keys:
        data_config[data_config[key]['short_name']] = copy.deepcopy(data_config[key])
        del data_config[key]

    #reload data config in case it has been changed accidentally
    data_config = yaml.safe_load(open(paths_dict['path_to_data_config']))
    #and load one with shorrt names as keys
    data_config_short_names = yaml.safe_load(open(paths_dict['path_to_data_config']))
    #update the data_config with the short_name keys
    for key in short_name_keys:
        short_name = data_config_short_names[key]['short_name']
        data_config_short_names[short_name] = copy.deepcopy(data_config_short_names[key])
        del data_config_short_names[key]
    
    check_indices_in_data_config(data_config, osemosys_cloud)
    
    return results_sheets, data_config, data_config_short_names

def edit_input_data(data_config_short_names, scenario, economy, model_end_year,sheet,sheet_name):
    """This function is passed sheets from the input data file and edits them based on the data_config_short_names. It then returns the edited sheet."""
    #filter on and drop specifc columns:
    if 'SCENARIO' in sheet.columns:
        sheet = sheet[sheet['SCENARIO']==scenario].drop(['SCENARIO'],axis=1)
    if 'REGION' in sheet.columns:
        sheet = sheet[sheet['REGION']==economy]
    if sheet_name == 'REGION':
        sheet = sheet[sheet['VALUE']==economy]
    if 'UNITS' in sheet.columns:
        sheet = sheet.drop(['UNITS'],axis=1)
    if 'NOTES' in sheet.columns:
        sheet = sheet.drop(['NOTES'],axis=1)

    #Based on the type of sheet, check that the required columns are present and edit values inside the sheet if necessary:
    if data_config_short_names[sheet_name]['type'] == 'param':
        #check the sheet has the required columns which are defined in the data_config indices list
        for col in data_config_short_names[sheet_name]['indices']:
            if col == 'YEAR':
                if col not in sheet.columns:
                    if any([str(col).isdigit() and len(str(col)) == 4 for col in sheet.columns]):
                        #now make the year columns into a single column called YEAR
                        sheet_cols = data_config_short_names[sheet_name]['indices'].copy()
                        sheet_cols.remove('YEAR')
                        sheet = pd.melt(sheet, id_vars=sheet_cols, var_name='YEAR', value_name='VALUE')
                    else:
                        print(f'Error: {sheet_name} sheet has no 4 digit year columns or a YEAR column. Either add 4digit year columns or a year column to the sheet. Or change the code.')
                        sys.exit()
                #now filter for years below the model_end_year + 1
                sheet = sheet[sheet['YEAR']<=model_end_year]
            elif col not in sheet.columns:
                print(f'Error: {sheet_name} sheet is missing the column {col}. Either add it to the sheet or remove it from the config/config.yaml file.')
                sys.exit()
        #check for VALUE col even thogh it is not in the indices list
        if 'VALUE' not in sheet.columns:
            print(f'Error: {sheet_name} sheet is missing the column VALUE.')
            sys.exit()

        #now check that there are no additional columns
        if len(sheet.columns) != len(data_config_short_names[sheet_name]['indices'])+1:
            #find the additional columns
            additional_cols = [col for col in sheet.columns if col not in data_config_short_names[sheet_name]['indices'] and col != 'VALUE']
            print(f'Error: {sheet_name} sheet has additional columns: \n{additional_cols} \n and these are not in the indices list. Either remove them from the sheet or add them to the indices list in the config/config.yaml file.')
            sys.exit()
    elif data_config_short_names[sheet_name]['type'] == 'set':
        #check it has a VALUE column only
        if len(sheet.columns) != 1 and sheet.columns[0] != 'VALUE':
            print(f'Error: {sheet_name} sheet should only have the column VALUE.')
            sys.exit()
        #if the sheet is called 'YEAR' then the YEAR col is called 'VALUE' and we need to filter it:
        if sheet_name == 'YEAR':
            sheet = sheet[sheet['VALUE']<=model_end_year]
    else:
        print(f'Error: {sheet_name} sheet has an invalid type. The type should be either param or set.')
        sys.exit()

    sheet = sheet.loc[(sheet != 0).any(axis=1)] # remove rows if all are zero

    #drop duplicates
    sheet = sheet.drop_duplicates()

    return sheet

def check_order_of_indices_in_data_config():#TODO do this using dataconfig and ?the model file?
    #run through the indices in the data_config and check that they are in the correct order:
    #assuming the indices have the names:
    return
def extract_input_data(data_config_short_names,paths_dict,model_end_year,economy,scenario):
    #using the data extracted from the data_config.yaml file, extract that data from the excel sheet and save it to a dictionary:
    input_data = dict()
    #open excel workbook:
    wb = pd.ExcelFile(paths_dict['input_data_file_path'])
    #now import data from excel sheet:
    for sheet_name in data_config_short_names:

        #ignore any results sheets:
        if data_config_short_names[sheet_name]['type'] == 'result':
            continue

        #check the sheet exists in the excel file:
        if sheet_name not in wb.sheet_names:
            print(f'Error: {sheet_name} is not in the excel sheet. Either add it to the sheet or remove it from the config/config.yaml file.')
            sys.exit()

        #get the sheet using the sheet_name
        sheet = wb.parse(sheet_name)

        sheet = edit_input_data(data_config_short_names, scenario, economy, model_end_year,sheet,sheet_name)
        
        input_data[sheet_name] = sheet
    #close excel workbook:
    wb.close()

    return input_data

def write_data_to_temp_workbook(paths_dict, filtered_input_data):
    #write the data to a temp workbook before converting to the osemosys format

    with pd.ExcelWriter(paths_dict['path_to_combined_input_data_workbook']) as writer:
        for k, v in filtered_input_data.items():
            v.to_excel(writer, sheet_name=k, index=False, merge_cells=False)
    print("Combined file of Excel input data has been written to the tmp folder.\n")

    return

def prepare_data_for_osemosys(paths_dict, data_config):
    #The data needs to be converted from the Excel format to the text file format. We use otoole for this task.

    reader = ReadExcel(user_config=data_config)#TODO is this going to work as expected?
    writer = WriteDatafile(user_config=data_config)

    data, default_values = reader.read(paths_dict['path_to_combined_input_data_workbook'])

    writer.write(data, paths_dict['path_to_input_data_file'], default_values)

    print(f"Data file in text format has been written and saved in the tmp folder as {paths_dict['path_to_input_data_file']}. This is the file you would use in OsEMOSYS Cloud as data if you are using that.\n")

    return 

def replace_long_var_names_in_osemosys_script(paths_dict):
    """We need to repalce some long variable names in the osemosys script so that they dont cause an error when using the cbc solver. 
    Honestly I dont get this because it seems like the osemosys cloud server is also having this problem and noone there is doing anything about it? Maybe i am a genius?"""
    #load in new_osemosys_model_script_path
    with open(paths_dict['new_osemosys_model_script_path'], 'r') as t:
        model_text = t.read()
    #update the following variable names:
    long_var_names = ['SC1_LowerLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInFirstWeekConstraint', 'SC1_UpperLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInFirstWeekConstraint', 'SC2_LowerLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInFirstWeekConstraint', 'SC2_UpperLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInFirstWeekConstraint', 'SC3_LowerLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInLastWeekConstraint', 'SC3_UpperLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInLastWeekConstraint', 'SC4_LowerLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInLastWeekConstraint', 'SC4_UpperLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInLastWeekConstraint']
    #now replace them with the first 20 characters
    for var_name in long_var_names:
        model_text = model_text.replace(var_name, var_name[:20])
    #write the new model script to the tmp directory
    with open(paths_dict['new_osemosys_model_script_path'], 'w') as f:
        f.write('%s\n'% model_text)
    return

def prepare_model_script_for_osemosys(paths_dict, osemosys_cloud,replace_long_var_names=True):
    #either modfiy the model script if it is being used locally so the resultsPath is in tmp_directory, or if it is being used in the cloud, then just move the model script to the tmp_directory for ease of access

    if not osemosys_cloud:

        with open(paths_dict['osemosys_model_script_path'], 'r') as t:
            model_text = t.read()

        # Replace the target string
        model_text = model_text.replace("param ResultsPath, symbolic default 'results';",f"param ResultsPath, symbolic default '{paths_dict['tmp_directory']}';")#this makes it so that the results are saved in the tmp directory before we format them

        #write the new model script to the tmp directory
        with open(paths_dict['new_osemosys_model_script_path'], 'w') as f:
            f.write('%s\n'% model_text)

    else:
        shutil.copy(paths_dict['osemosys_model_script_path'], paths_dict['new_osemosys_model_script_path'])

    if replace_long_var_names:
        replace_long_var_names_in_osemosys_script(paths_dict)

    print(f'\n######################## \n Running solve process using {paths_dict["new_osemosys_model_script_path"]} \n########################\n')

    return

def write_model_run_specs_to_file(paths_dict, scenario, economy, model_end_year, osemosys_cloud, FILE_DATE_ID,solving_method):
    #write the model run specs to a file so we can keep track of what we have run and when
    path_to_data_config = paths_dict['path_to_data_config']
    results_workbook = paths_dict['results_workbook']
    combined_results_tall_years = paths_dict['combined_results_tall_years']
    combined_results_tall_sheet_names = paths_dict['combined_results_tall_sheet_names']
    input_data_path = paths_dict['input_data_file_path']
    osemosys_model_script_path = paths_dict['new_osemosys_model_script_path']
    with open(paths_dict['model_run_specifications_file'], 'w') as f:
        f.write(f'Inputs:\n')
        f.write(f'Run Date: {FILE_DATE_ID}\n')
        f.write(f'Run Scenario: {scenario}\n')
        f.write(f'Run Economy: {economy}\n')
        f.write(f'Run End Year: {model_end_year}\n')
        f.write(f'Run Osemosys Cloud: {osemosys_cloud}\n')
        f.write(f'Osemosys Model Script path: {osemosys_model_script_path}\n')
        f.write(f'Input Data Config File path: {path_to_data_config}\n')
        f.write(f'Solving Method used: {solving_method}\n')
        f.write(f'Input data path: {input_data_path}\n')
        f.write(f'\nResults:\n')
        f.write(f'Results Workbook: {results_workbook}\n')
        f.write(f'Combined Results Tall Years: {combined_results_tall_years}\n')
        f.write(f'Combined Results Tall Sheet Names: {combined_results_tall_sheet_names}\n')     
    return

def create_new_directories(tmp_directory, results_directory,osemosys_cloud, FILE_DATE_ID, economy, scenario_folder):
    #create the tmp and results directories if they dont exist. ALso check if there are files in the tmp directory and if so, move them to a new folder with the FILE_DATE_ID in the name. 
    #EXCEPT if osemosys_cloud is True, then we dont want to do this because the user will run main.py twuice, once to prepare data and once to extract results, and we dont want to move the files in the tmp directory in between those two runs

    if not os.path.exists(tmp_directory):
        os.makedirs(tmp_directory)
    else:
        #if theres already file in the tmp directory then we should move those to a new folder so we dont overwrite them:
        #check if there are files:
        if len(os.listdir(tmp_directory)) > 0 and not osemosys_cloud:
            new_temp_dir = f'./tmp/{economy}/{scenario_folder}/{FILE_DATE_ID}'
            #make the new temp directory:
            os.makedirs(new_temp_dir)
            #move all files:
            for file in os.listdir(tmp_directory):
                shutil.move(f'{tmp_directory}/{file}', new_temp_dir)

    if not os.path.exists(results_directory):#no need to check if the results dir exists because the data will be saved with FILE_DATE_ID in the name, its just too hard to do that with the tmp directory
        os.makedirs(results_directory)

    return


def set_up_paths(scenario, economy, root_dir, config_dir,data_config_file, input_data_sheet_file,osemosys_model_script,osemosys_cloud,FILE_DATE_ID):
    """set up the paths to the various files and folders we will need to run the model. This will create a dictionary for the paths so we dont have to keep passing lots of arguments to functions"""
    if osemosys_cloud:
        scenario_folder=f'cloud_{scenario}'
    else:
        scenario_folder=f'{scenario}'

    
    tmp_directory = f'./tmp/{economy}/{scenario_folder}'
    results_directory = f'./results/{economy}/{scenario_folder}'

    create_new_directories(tmp_directory, results_directory,osemosys_cloud, FILE_DATE_ID, economy, scenario_folder)

    #create model run specifications txt file using the input variables as the details and the FILE_DATE_ID as the name:
    model_run_specifications_file = f'{tmp_directory}/model_run_specs_{FILE_DATE_ID}.txt'

    path_to_data_config = f'{root_dir}/{config_dir}/{data_config_file}'
    if not os.path.exists(path_to_data_config):
        print(f'WARNING: data config file {path_to_data_config} does not exist')

    path_to_combined_input_data_workbook = f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'

    input_data_file_path=f"{root_dir}/data/{input_data_sheet_file}"

    # path_to_combined_input_data_workbook=f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'

    path_to_input_data_file = f'{tmp_directory}/datafile_from_python_{economy}_{scenario}.txt'
     
    #create path to save copy of outputs to txt file in case of error:
    log_file_path = f'{tmp_directory}/process_log_{economy}_{scenario}.txt'

    #check that osemosys_model_script is either 'osemosys.txt' or 'osemosys_fast.txt':
    if osemosys_model_script not in ['osemosys.txt', 'osemosys_fast.txt']:
        print(f'ERROR: osemosys_model_script is {osemosys_model_script}. It should be either osemosys.txt or osemosys_fast.txt')
        raise ValueError
    osemosys_model_script_path = f'{root_dir}/{config_dir}/{osemosys_model_script}'

    new_osemosys_model_script_path = f'{tmp_directory}/model_{economy}_{scenario}.txt'
    #TODO implement something like https://stackoverflow.com/questions/24849998/how-to-catch-exception-output-from-python-subprocess-check-output

    cbc_intermediate_data_file_path = f'{tmp_directory}/cbc_input_{economy}_{scenario}.lp'
    cbc_results_data_file_path=f'{tmp_directory}/cbc_results_{economy}_{scenario}.sol'

    results_workbook = f'{results_directory}/{economy}_results_{scenario}_{FILE_DATE_ID}.xlsx'

    combined_results_tall_years = f'{results_directory}/tall_years_{economy}_results_{scenario}_{FILE_DATE_ID}.csv'
    combined_results_tall_sheet_names = f'{results_directory}/tall_sheet_names_{economy}_results_{scenario}_{FILE_DATE_ID}.csv'

    #PUT EVERYTHING IN A DICTIONARY
    paths_dict = {}
    paths_dict['tmp_directory'] = tmp_directory
    paths_dict['results_directory'] = results_directory
    paths_dict['path_to_data_config'] = path_to_data_config
    paths_dict['path_to_combined_input_data_workbook'] = path_to_combined_input_data_workbook
    paths_dict['input_data_file_path'] = input_data_file_path
    paths_dict['path_to_input_data_file'] = path_to_input_data_file
    paths_dict['log_file_path'] = log_file_path
    paths_dict['cbc_intermediate_data_file_path'] = cbc_intermediate_data_file_path
    paths_dict['cbc_results_data_file_path'] = cbc_results_data_file_path
    paths_dict['new_osemosys_model_script_path'] = new_osemosys_model_script_path
    paths_dict['osemosys_model_script_path'] = osemosys_model_script_path
    paths_dict['results_workbook'] = results_workbook
    paths_dict['combined_results_tall_years'] = combined_results_tall_years
    paths_dict['combined_results_tall_sheet_names'] = combined_results_tall_sheet_names
    paths_dict['model_run_specifications_file'] = model_run_specifications_file
    
    return paths_dict

def validate_input_data(paths_dict):
    """validate the data using otoole validate function. One day it would be good to create a validation file for the options:
        --validate_config VALIDATE_CONFIG
        Path to a user-defined validation-config file
    This would probably remove the issue with lots of fuels being labelled as invalid names."""

    command = f"otoole validate datafile {paths_dict['path_to_input_data_file']} {paths_dict['path_to_data_config']}"

    start = time.time()
    result = subprocess.run(command,shell=True, capture_output=True, text=True)

    print("\n Printing results of validate process \n")
    print(command+'\n')
    print(result.stdout+'\n')
    print(result.stderr+'\n')
    print('\n Time taken: {} for validate process'.format(time.time()-start))

    return

