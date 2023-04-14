


import pandas as pd
import yaml
import os
from otoole.read_strategies import ReadExcel
from otoole.write_strategies import WriteDatafile
import shutil
import sys
import copy
import subprocess
import post_processing_functions as post_processing_functions
import logging
logging.getLogger("otoole").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

def setup_logging(FILE_DATE_ID,paths_dict,testing=False):
    if testing:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO
    #set up logging now that we have the paths all set up:
    logging.basicConfig(
        handlers=[
            logging.StreamHandler(sys.stdout),#logging will print things to the console as well as to the log file
            logging.FileHandler(paths_dict['log_file_path'])
        ], encoding='utf-8', level=logging_level, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger()
    logger.info(f"LOGGING STARTED: {FILE_DATE_ID}, being saved to {paths_dict['log_file_path']} and outputted to console")


def set_up_config_dict(root_dir, input_data_sheet_file,run_with_wsl=False, extract_osemosys_cloud_results_using_otoole=False):
    """extract the data we want to run the model on using the first sheet in the input data sheet called START. This defines the economy, scenario and model_end_year we want to run the model for."""
    df_prefs = pd.read_excel(f'{root_dir}/data/{input_data_sheet_file}', sheet_name='START',usecols="A:B",nrows=7,header=None)

    economy = df_prefs.loc[0][1]
    scenario = df_prefs.loc[1][1]
    model_start_year = df_prefs.loc[2][1]
    model_end_year = df_prefs.loc[3][1]
    data_config_file = df_prefs.loc[4][1]
    solving_method = df_prefs.loc[5][1]
    osemosys_model_script = df_prefs.loc[6][1]
    
    #check if osemosys_model_script contains .txt
    if not osemosys_model_script.endswith('.txt'):
        osemosys_model_script = osemosys_model_script + '.txt'

    #corect names:
    names = ('Economy', 'Scenario', 'model_start_year','model_end_year',  'Config file', 'Solver', 'Model file')
    #names in the excel sheet:
    names_in_excel = (df_prefs.loc[0][0], df_prefs.loc[1][0], df_prefs.loc[2][0], df_prefs.loc[3][0], df_prefs.loc[4][0], df_prefs.loc[5][0], df_prefs.loc[6][0])
    if not all([name == name_in_excel for name, name_in_excel in zip(names, names_in_excel)]):
        logger.error(f'The names in the START sheet of the input data sheet are not correct. Please check the names are correct and try again. \n The names in the START sheet are: {names_in_excel} \n The names that should be in the START sheet are: {names}')
        sys.exit()

    config_dict = {}
    config_dict['economy'] = economy
    config_dict['model_end_year'] = model_end_year
    config_dict['model_start_year'] = model_start_year
    config_dict['scenario'] = scenario
    config_dict['solving_method'] = solving_method
    config_dict['data_config_file'] = data_config_file
    config_dict['input_data_sheet_file'] = input_data_sheet_file
    #print the config_dict details
    logger.info(f'Running model for economy: {economy}, scenario: {scenario}, for years between and including {model_start_year} and {model_end_year}')
    
    osemosys_cloud_input = get_osemosys_cloud_stage_from_user(config_dict)

    config_dict['osemosys_cloud_input'] = osemosys_cloud_input
    config_dict['extract_osemosys_cloud_results_using_otoole'] = extract_osemosys_cloud_results_using_otoole
    config_dict['osemosys_model_script'] = osemosys_model_script
    config_dict['run_with_wsl'] = run_with_wsl
    config_dict['missing_results_and_warning_message'] = []#use this to track which results are missing from the osemosys results. this might be a temporary fix as the results arent working properly at the moment

    return config_dict


def check_indices_in_data_config(config_dict):

    #first get names of possible idnices in the data config which are the keys where type: set
    data_config_indices = [key for key in config_dict['data_config'].keys() if config_dict['data_config'][key]['type'] == 'set']
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
        logger.error(f'The indices in the data_config are not all in the list of possible indices. Make sure none of them have a spelling mistake. \n The possible indices are: \n {possible_indices}')
        raise ValueError('The indices in the data_config are not all in the list of possible indices. Make sure none of them have a spelling mistake. \n The possible indices are: \n {}'.format(possible_indices))

    if config_dict['solving_method'] == 'cloud':
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
        for key in config_dict['data_config']:
            if config_dict['data_config'][key]['type'] == 'param':
                indices = config_dict['data_config'][key]['indices']
                indices_in_selected_indices_order = [index for index in indices if index in selected_indices_order]
                if len(indices_in_selected_indices_order) > 1:
                    #starting from the first indice, check that the indice ahead of ti is also ahead of it in the selected_indices_order list
                    for i in range(len(indices_in_selected_indices_order)-1):
                        if selected_indices_order.index(indices_in_selected_indices_order[i]) > selected_indices_order.index(indices_in_selected_indices_order[i+1]):
                            raise ValueError(f"The indices {indices_in_selected_indices_order} in the data_config are not in the correct order for {config_dict['data_config'][key]}. Make sure that the indices are in the correct order. \n These indices need to have the order: \n {selected_indices_order}")
     
def import_data_config(paths_dict,config_dict):
        
    accepted_types = ['param','set','result']
    #import then recreate dataconfig with short_name as key so that its keys can be compared to the name of the corresponding data sheet in our input data
    data_config = yaml.safe_load(open(paths_dict['path_to_data_config']))

    #first check data_config for anything that isnt in accepted_types
    types = [data_config[key]['type'] for key in data_config.keys()]
    if not all([type in accepted_types for type in types]):
        logger.error(f'The data config contains a type that is not expected. Accepted types are: {accepted_types}')
        raise ValueError('Data config contains a type that is not expected. Accepted types are: {}'.format(accepted_types))

    config_dict['data_config'] = data_config
    
    check_indices_in_data_config(config_dict)
    
    return config_dict

def create_data_config_with_short_names_as_keys(config_dict):
    #create an exact copy of the data config but with any short names as keys so we dont need to extract them from the data config each time

    #first make a copy of the data_config to edit
    data_config_short_names = copy.deepcopy(config_dict['data_config'])
    original_keys = list(data_config_short_names.keys())
    #repalce any keys with their short_name if they have one
    for key in original_keys:
        if 'short_name' in data_config_short_names[key].keys():
            short_name = data_config_short_names[key]['short_name']
            data_config_short_names[short_name] = copy.deepcopy(data_config_short_names[key])
            del data_config_short_names[key]
    return data_config_short_names

def raise_error_if_var_name_not_in_dict(x):
    #not sure if this is the best way to do this but it works
    logger.error(f'{x} is not in the long_variable_names_to_short_variable_names dictionary for the column {col}. Please add it to the dictionary or change it in the input data.')
    wb.close()
    sys.exit()

def edit_input_data(data_config_short_names, scenario, economy, model_end_year,model_start_year,sheet,sheet_name,wb,long_variable_names_to_short_variable_names):#123 is config short anmes still going tp have dtuypes and stuff?
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
                        logger.error(f'{sheet_name} sheet has no 4 digit year columns or a YEAR column. Either add 4digit year columns or a year column to the sheet. Or change the code.')
                        wb.close()
                        sys.exit()
                #now filter for model_end_year below the model_end_year 
                sheet = sheet[sheet['YEAR']<=model_end_year]
                #now filter for model_start_year 
                sheet = sheet[sheet['YEAR']>=model_start_year]
            elif col not in sheet.columns:
                logger.error(f'{sheet_name} sheet is missing the column {col}. Either add it to the sheet or remove it from the config/config.yaml file.')
                wb.close()
                sys.exit()
            # elif col in data_config_short_names.keys():
            #     #we have issues with the first character of a string being a number. so for all cols that are dtype: str, if the cols ahs a digit as its first letter, we will change it to have a letter as the first character, we will make that letter 'a'.
            #     if data_config_short_names[col]['dtype'] == 'str':
            #         sheet[col] = sheet[col].apply(lambda x: 'a'+str(x) if str(x)[0].isdigit() else x)"123
            elif col in long_variable_names_to_short_variable_names.keys():
                #we are having issues with the values in our input data being too long for coinc cbc. so we will attempt to decrease their lgnth.
                sheet[col] = sheet[col].apply(lambda x: long_variable_names_to_short_variable_names[col][x] if x in long_variable_names_to_short_variable_names[col].keys() else raise_error_if_var_name_not_in_dict(x))
            else:
                pass
        #check for VALUE col even thogh it is not in the indices list
        if 'VALUE' not in sheet.columns:
            logger.error(f'{sheet_name} sheet is missing the column VALUE. Either add it to the sheet or remove it from the config/config.yaml file.')
            wb.close()
            sys.exit()

        #now check that there are no additional columns
        if len(sheet.columns) != len(data_config_short_names[sheet_name]['indices'])+1:
            #find the additional columns
            additional_cols = [col for col in sheet.columns if col not in data_config_short_names[sheet_name]['indices'] and col != 'VALUE']
            logger.error(f'{sheet_name} sheet has additional columns: \n{additional_cols} \n and these are not in the indices list. Either remove them from the sheet or add them to the indices list in the config/config.yaml file.')
            wb.close()
            sys.exit()
    elif data_config_short_names[sheet_name]['type'] == 'set':
        #check it has a VALUE column only
        if len(sheet.columns) != 1 and sheet.columns[0] != 'VALUE':
            logger.error(f'{sheet_name} sheet should only have the column VALUE.')
            wb.close()
            sys.exit()
        #if the sheet is called 'YEAR' then the YEAR col is called 'VALUE' and we need to filter it:
        if sheet_name == 'YEAR':
            sheet = sheet[sheet['VALUE']<=model_end_year]
            sheet = sheet[sheet['VALUE']>=model_start_year]
        # #if the dtype is str, we need to make sure that the first character is not a digit
        # if data_config_short_names[sheet_name]['dtype'] == 'str':
        #     sheet['VALUE'] = sheet['VALUE'].apply(lambda x: 'a'+str(x) if str(x)[0].isdigit() else x)123

        #we are having issues with the values in our input data being too long for coinc cbc. so we will attempt to decrease their lgnth.
        #if col is 'REGION' then change col to the last three letters of the col123
        if sheet_name == 'REGION':
            sheet['VALUE'] = sheet['VALUE'].apply(lambda x: long_variable_names_to_short_variable_names[sheet_name][x] if x in long_variable_names_to_short_variable_names[sheet_name].keys() else raise_error_if_var_name_not_in_dict(x))
        elif sheet_name in long_variable_names_to_short_variable_names.keys():
            #use the long_variable_names_to_short_variable_names dict to change the values in the sheet
            sheet['VALUE'] = sheet['VALUE'].apply(lambda x: long_variable_names_to_short_variable_names[sheet_name][x] if x in long_variable_names_to_short_variable_names[sheet_name].keys() else raise_error_if_var_name_not_in_dict(x))
        else:
            pass

    else:
        logger.error(f'{sheet_name} sheet has an invalid type. The type should be either param or set.')
        wb.close()
        sys.exit()

    sheet = sheet.loc[(sheet != 0).any(axis=1)] # remove rows if all are zero

    #drop duplicates
    sheet = sheet.drop_duplicates()

    return sheet

def import_long_variable_names_to_short_variable_names():
    #import the conrdocance and create a dict with each sheet as a key, then a nested dict with the long name as the key and the short name as the value. THis will then be used to change all values for those sheets (which represent INDICES or cols) in the input data to the short name.
    wb = pd.ExcelFile('config/long_variable_names_to_short_variable_names.xlsx')
    long_variable_names_to_short_variable_names = dict()
    for sheet_name in wb.sheet_names:
        sheet = pd.read_excel(wb,sheet_name)
        long_variable_names_to_short_variable_names[sheet_name] = dict(zip(sheet['long_name'],sheet['short_name']))
    return long_variable_names_to_short_variable_names


def extract_input_data(paths_dict,config_dict):
    scenario = config_dict['scenario']
    economy = config_dict['economy']
    model_end_year = config_dict['model_end_year']
    model_start_year = config_dict['model_start_year']
    data_config_short_names = create_data_config_with_short_names_as_keys(config_dict)
    long_variable_names_to_short_variable_names = import_long_variable_names_to_short_variable_names()


    #using the data extracted from the data_config.yaml file, extract that data from the excel sheet and save it to a dictionary:
    input_data = dict()
    #open excel workbook:
    wb = pd.ExcelFile(paths_dict['input_data_file_path'])
    #now import data from excel sheet:
    for sheet_name in data_config_short_names:

        #ignore any results sheets
        if data_config_short_names[sheet_name]['type'] == 'result':
            continue

        #check the sheet exists in the excel file:
        if sheet_name not in wb.sheet_names:
            logger.error(f'{sheet_name} is not in the excel sheet. Either add it to the sheet or remove it from the config/config.yaml file.')
            wb.close()
            sys.exit()

        #get the sheet using the sheet_name
        sheet = wb.parse(sheet_name)

        sheet = edit_input_data(data_config_short_names, scenario, economy, model_end_year,model_start_year,sheet,sheet_name,wb,long_variable_names_to_short_variable_names)
        
        input_data[sheet_name] = sheet
    #close excel workbook:
    wb.close()

    return input_data

def write_data_to_temp_workbook(paths_dict, input_data):
    #write the data to a temp workbook before converting to the osemosys format
    
    with pd.ExcelWriter(paths_dict['path_to_combined_input_data_workbook']) as writer:
        for k, v in input_data.items():
            v.to_excel(writer, sheet_name=k, index=False, merge_cells=False)
    logger.info(f"Combined file of Excel input data has been written to the tmp folder.\n")

    return

def write_input_data_as_csvs_to_data_folder(paths_dict, input_data):
    #aim is to create folder so the data can be accessed in convert_csvs_to_datafile()
    for k, v in input_data.items():
        # v.to_excel(writer, sheet_name=k, index=False, merge_cells=False)
        v.to_csv(paths_dict['input_csvs_folder']+'/' + k + '.csv', index=False)
    logger.info(f"Combined file of Excel input data has been written as csvs to {paths_dict['input_csvs_folder']}.\n")
    return

def convert_csvs_to_datafile(paths_dict):
    #convert the csvs in paths_dict['input_csvs_folder'] to a datafile. This is an alternative to prepare_data_for_osemosys()
    command = f"otoole convert csv datafile {paths_dict['input_csvs_folder']} {paths_dict['path_to_input_data_file']} {paths_dict['path_to_new_data_config']}"

    result = subprocess.run(command,shell=True, capture_output=True, text=True)
    logger.info(f"Running the following command to convert the csvs to a datafile:\n{command}")
    logger.info(command+'\n')
    logger.info(result.stdout+'\n')
    logger.info(result.stderr+'\n')

    logger.info(f"Data file in text format has been written and saved in the tmp folder as {paths_dict['path_to_input_data_file']}.\n")
    return

def convert_workbook_to_datafile(paths_dict, config_dict):
    #The data needs to be converted from the Excel format to the text file format. We use otoole for this task.

    command = f"otoole convert excel datafile {paths_dict['path_to_combined_input_data_workbook']} {paths_dict['path_to_input_data_file']} {paths_dict['path_to_new_data_config']}"

    result = subprocess.run(command,shell=True, capture_output=True, text=True)
    logger.info(f"Running the following command to convert the workbook to a datafile:\n{command}")
    logger.info(command+'\n')
    logger.info(result.stdout+'\n')
    logger.info(result.stderr+'\n')



    # reader = ReadExcel(user_config=config_dict['data_config'])#TODO is this going to work as expected?
    # writer = WriteDatafile(user_config=config_dict['data_config'])

    # data, default_values = reader.read(paths_dict['path_to_combined_input_data_workbook'])

    # writer.write(data, paths_dict['path_to_input_data_file'], default_values)

    logger.info(f"Data file in text format has been written and saved in the tmp folder as {paths_dict['path_to_input_data_file']}.\n")

    return 

def replace_long_var_names_in_osemosys_script(paths_dict, config_dict):
    """We need to repalce some long variable names in the osemosys script so that they dont cause an error when using the cbc solver. 
    Honestly I dont get this because it seems like the osemosys cloud server is also having this problem and noone there is doing anything about it? Maybe i am a genius?"""
    #load in new_osemosys_model_script_path
    with open(paths_dict['new_osemosys_model_script_path'], 'r') as t:
        model_text = t.read()
    #update the following variable names:
    long_var_names = ['SC1_LowerLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInFirstWeekConstraint', 'SC1_UpperLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInFirstWeekConstraint', 'SC2_LowerLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInFirstWeekConstraint', 'SC2_UpperLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInFirstWeekConstraint', 'SC3_LowerLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInLastWeekConstraint', 'SC3_UpperLimit_EndOfDailyTimeBracketOfLastInstanceOfDayTypeInLastWeekConstraint', 'SC4_LowerLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInLastWeekConstraint', 'SC4_UpperLimit_BeginningOfDailyTimeBracketOfFirstInstanceOfDayTypeInLastWeekConstraint',
    #begin non_osemosys_fast var names. But note that until we can get non osemosys_fast.txt to work with coin then there is no need for these, except to decrease the logs on a process that doesnt work.
    'EBa1_RateOfFuelProduction1','EBa2_RateOfFuelProduction2','Acc1_FuelProductionByTechnology','Acc2_FuelUseByTechnology']#,
    #these ones are likely to be variables within the data config. we should be careful changing these
    #'RateOfProductionByTechnologyByMode','RateOfProductionByTechnology','ProductionByTechnology','AnnualTechnologyEmissionByMode','AnnualTechnologyEmissionPenaltyByEmission']#im not saaure why productionbytechnologyannual is not ehre? #NOTE THAT THIS WONT WORK WITH RATE OF PRODUCTION BY TECHNOLOGY BECAUSE THAT WILL BE REPEATED
    long_name_to_shortened_name = dict()
    #now replace them with the first 20 characters
    for var_name in long_var_names:
        shortened_name = var_name[:20]
        long_name_to_shortened_name[var_name] = shortened_name
        model_text = model_text.replace(var_name, shortened_name)
    #check the data config for the long var names and replace them with the shortened names
    data_config_copy = copy.deepcopy(config_dict['data_config'])
    for key in data_config_copy.keys():
        if key in long_var_names:
            config_dict['data_config'][long_name_to_shortened_name[key]] = copy.deepcopy(config_dict['data_config'][key])
            del config_dict['data_config'][key]

    #write the new model script to the tmp directory
    with open(paths_dict['new_osemosys_model_script_path'], 'w') as f:
        f.write('%s\n'% model_text)
    return config_dict

def prepare_model_script_for_osemosys(paths_dict, config_dict,replace_long_var_names=True):
    #either modfiy the model script if it is being used locally so the resultsPath is in tmp_directory, or if it is being used in the cloud, then just move the model script to the tmp_directory for ease of access

    if config_dict['solving_method'] != 'cloud':

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
        config_dict = replace_long_var_names_in_osemosys_script(paths_dict, config_dict)

    return config_dict

def write_model_run_specs_to_file(paths_dict, config_dict, FILE_DATE_ID):
    #write the model run specs to a file so we can keep track of what we have run and when
    path_to_data_config = paths_dict['path_to_data_config']
    path_to_new_data_config = paths_dict['path_to_new_data_config']
    results_workbook = paths_dict['results_workbook']
    combined_results_tall_years = paths_dict['combined_results_tall_years']
    combined_results_tall_sheet_names = paths_dict['combined_results_tall_sheet_names']
    input_data_path = paths_dict['input_data_file_path']
    osemosys_model_script_path = paths_dict['osemosys_model_script_path']
    with open(paths_dict['model_run_specifications_file'], 'w') as f:
        f.write(f'Inputs:\n')
        f.write(f'Run Date: {FILE_DATE_ID}\n')
        f.write(f"Run Scenario: {config_dict['scenario']}\n")
        f.write(f"Run Economy: {config_dict['economy']}\n")
        f.write(f"Run model_start_year: {config_dict['model_start_year']}\n")
        f.write(f"Run model_end_year: {config_dict['model_end_year']}\n")
        f.write(f'Original Osemosys Model Script path: {osemosys_model_script_path}\n')
        f.write(f'New Osemosys Model Script path: {paths_dict["new_osemosys_model_script_path"]}\n')
        f.write(f'Original Data Config File path: {path_to_data_config}\n')
        f.write(f'Input Data Config File path: {path_to_new_data_config}\n')
        f.write(f"Solving Method used: {config_dict['solving_method']}\n")
        f.write(f'Input data path: {input_data_path}\n')
        f.write(f"extract_osemosys_cloud_results_using_otoole: {config_dict['extract_osemosys_cloud_results_using_otoole']}\n")

        f.write(f'\nIntermediate inputs (some may not be applicable):\n')
        f.write(f'Combined Input Data workbook path: {paths_dict["path_to_combined_input_data_workbook"]}\n')
        f.write(f'Input Data File path: {paths_dict["path_to_input_data_file"]}\n')
        f.write(f'Log file path: {paths_dict["log_file_path"]}\n')
        if config_dict['solving_method'] == 'coin':
            f.write(f'cbc intermediate data file path: {paths_dict["cbc_intermediate_data_file_path"]}\n')
            f.write(f'cbc results data file path: {paths_dict["cbc_results_data_file_path"]}\n')

        f.write(f'\nResults:\n')
        f.write(f'Results Workbook: {results_workbook}\n')
        f.write(f'Combined Results Tall Years: {combined_results_tall_years}\n')
        f.write(f'Combined Results Tall Sheet Names: {combined_results_tall_sheet_names}\n')  

        f.write(f'\nOther:\n')
        f.write(f'Config Dict: {paths_dict["config_dict_pickle"]}\n')
        f.write(f'Paths Dict: {paths_dict["paths_dict_pickle"]}\n') 
        f.write(f'Tall results df pickle: {paths_dict["tall_results_dfs_pickle"]}\n') 

    return

def create_new_directories(tmp_directory, results_directory,visualisation_directory,input_csvs_folder, FILE_DATE_ID, path_to_input_csvs, config_dict,keep_current_tmp_files,write_to_workbook):
    #create the tmp and results directories if they dont exist. ALso check if there are files in the tmp directory and if so, move them to a new folder with the FILE_DATE_ID in the name. 
    #EXCEPT if osemosys_cloud_input is y, then we dont want to do this because the user will be running main.py to extract results form the cloud output, as tehy ahve already done it once to prepare data now they are doing it once to extract results, and we dont want to move the files in the tmp directory in between those two runs

    #TMP
    if not os.path.exists(tmp_directory):
        os.makedirs(tmp_directory)
    else:
        #if theres already file in the tmp directory then we should move those to a new folder so we dont overwrite them:
        #check if there are files:
        if len(os.listdir(tmp_directory)) > 0 and config_dict['osemosys_cloud_input'] != 'y' and not keep_current_tmp_files:
            new_temp_dir = f"./tmp/{tmp_directory}/{FILE_DATE_ID}"
            #make the new temp directory:
            os.makedirs(new_temp_dir)
            #move all files (BUT NOT FOLDERS!):
            for file in os.listdir(tmp_directory):
                if os.path.isfile(f'{tmp_directory}/{file}'):
                    shutil.move(f'{tmp_directory}/{file}', new_temp_dir)

    #RESULTS
    if not os.path.exists(results_directory):#no need to check if the results dir exists because the data will be saved with FILE_DATE_ID in the name, its just too hard to do that with the tmp directory
        os.makedirs(results_directory)

    #VISUALISATION
    if not os.path.exists(visualisation_directory):
        os.makedirs(visualisation_directory)
    else:
        if len(os.listdir(visualisation_directory)) > 0:
            new_visualisation_dir = f"./{visualisation_directory}/{FILE_DATE_ID}"
            #make the new temp directory:
            os.makedirs(new_visualisation_dir)
            #move all files (BUT NOT FOLDERS!):
            for file in os.listdir(visualisation_directory):
                if os.path.isfile(f'{visualisation_directory}/{file}'):
                    shutil.move(f'{visualisation_directory}/{file}', new_visualisation_dir)
    if not write_to_workbook:   
        if not os.path.exists(f'{path_to_input_csvs}'):
            os.makedirs(f'{path_to_input_csvs}')
        else:
            if len(os.listdir(f'{path_to_input_csvs}')) > 0:
                new_input_csvs_dir = f"{tmp_directory}/{FILE_DATE_ID}/{input_csvs_folder}"
                #make the new temp directory:
                os.makedirs(new_input_csvs_dir)
                #move all files (BUT NOT FOLDERS!):
                for file in os.listdir(f'{path_to_input_csvs}'):
                    if os.path.isfile(f'{path_to_input_csvs}/{file}'):
                        shutil.move(f'{path_to_input_csvs}/{file}', new_input_csvs_dir)
    return


def set_up_paths_dict(root_dir,FILE_DATE_ID,config_dict,keep_current_tmp_files=False,write_to_workbook=False):
    """set up the paths to the various files and folders we will need to run the model. This will create a dictionary for the paths so we dont have to keep passing lots of arguments to functions"""
    solving_method = config_dict['solving_method']
    scenario = config_dict['scenario']
    economy = config_dict['economy']
    data_config_file = config_dict['data_config_file']
    input_data_sheet_file = config_dict['input_data_sheet_file']

    if solving_method == 'cloud':
        scenario_folder=f'cloud_{scenario}'
    else:
        scenario_folder=f'{scenario}'

    
    tmp_directory = f'./tmp/{economy}_{scenario_folder}'
    results_directory = f'./results/{economy}_{scenario_folder}'
    visualisation_directory = f'./visualisations/{economy}_{scenario_folder}'

    input_csvs_folder = f'input_csvs'
    path_to_input_csvs = f'{tmp_directory}/{input_csvs_folder}'
    

    #create path to save copy of outputs to txt file in case of error:
    log_file_path = f'{tmp_directory}/process_log_{economy}_{scenario}_{FILE_DATE_ID}.txt'

    create_new_directories(tmp_directory, results_directory,visualisation_directory,input_csvs_folder, FILE_DATE_ID, path_to_input_csvs, config_dict,keep_current_tmp_files,write_to_workbook)

    #create model run specifications txt file using the input variables as the details and the FILE_DATE_ID as the name:
    model_run_specifications_file = f'{tmp_directory}/specs_{FILE_DATE_ID}.txt'

    path_to_data_config = f'{root_dir}/config/{data_config_file}'
    if not os.path.exists(path_to_data_config):
        logger.warning(f'data config file {path_to_data_config} does not exist')
    
    path_to_new_data_config = f'{tmp_directory}/{economy}_{scenario}_{data_config_file}'
    path_to_combined_input_data_workbook = f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'

    input_data_file_path=f"{root_dir}/data/{input_data_sheet_file}"

    # path_to_combined_input_data_workbook=f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'

    path_to_input_data_file = f'{tmp_directory}/datafile_from_python_{economy}_{scenario}.txt'
     
    

    #check that osemosys_model_script is either 'osemosys.txt' or 'osemosys_fast.txt':
    if config_dict['osemosys_model_script'] not in ['osemosys.txt', 'osemosys_fast.txt']:
        logger.warning(f"WARNING: osemosys_model_script is {config_dict['osemosys_model_script']}. It should be either osemosys.txt or osemosys_fast.txt")
        #sys.exit()
    osemosys_model_script_path = f"{root_dir}/config/{config_dict['osemosys_model_script']}"

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
    paths_dict['visualisation_directory'] = visualisation_directory
    paths_dict['path_to_data_config'] = path_to_data_config
    paths_dict['path_to_combined_input_data_workbook'] = path_to_combined_input_data_workbook
    paths_dict['input_data_file_path'] = input_data_file_path
    paths_dict['path_to_input_data_file'] = path_to_input_data_file
    paths_dict['path_to_input_csvs'] = path_to_input_csvs

    paths_dict['path_to_new_data_config']  = path_to_new_data_config
    paths_dict['log_file_path'] = log_file_path
    paths_dict['cbc_intermediate_data_file_path'] = cbc_intermediate_data_file_path
    paths_dict['cbc_results_data_file_path'] = cbc_results_data_file_path
    paths_dict['new_osemosys_model_script_path'] = new_osemosys_model_script_path
    paths_dict['osemosys_model_script_path'] = osemosys_model_script_path
    paths_dict['results_workbook'] = results_workbook
    paths_dict['combined_results_tall_years'] = combined_results_tall_years
    paths_dict['combined_results_tall_sheet_names'] = combined_results_tall_sheet_names
    paths_dict['model_run_specifications_file'] = model_run_specifications_file
    paths_dict['path_to_validation_config'] = f'{root_dir}/config/validate.yaml'
    paths_dict['tall_results_dfs_pickle'] = f'{tmp_directory}/tall_results_dfs_{economy}_{scenario}_{FILE_DATE_ID}.pickle'
    paths_dict['paths_dict_pickle'] = f'{tmp_directory}/paths_dict_{economy}_{scenario}_{FILE_DATE_ID}.pickle'
    paths_dict['config_dict_pickle'] = f'{tmp_directory}/config_dict_{economy}_{scenario}_{FILE_DATE_ID}.pickle'
    
    aggregated_results_and_inputs_folder_name = f"{FILE_DATE_ID}_{config_dict['economy']}_{config_dict['scenario']}_{config_dict['solving_method']}"
    paths_dict['aggregated_results_and_inputs_folder_name'] = aggregated_results_and_inputs_folder_name
    return paths_dict

def validate_input_data(paths_dict):
    """validate the data using otoole validate function. One day it would be good to create a validation file for the options:
        --validate_config VALIDATE_CONFIG
        Path to a user-defined validation-config file
    This would probably remove the issue with lots of fuels being labelled as invalid names."""
    #otoole validate datafile data.txt config.yaml --validate_config validate.yaml
    command = f"otoole validate datafile {paths_dict['path_to_input_data_file']} {paths_dict['path_to_new_data_config']} --validate_config {paths_dict['path_to_validation_config']}"

    result = subprocess.run(command,shell=True, capture_output=True, text=True)

    logger.info(f"Printing results of validate process \n{command}\n {result.stdout}\n {result.stderr}\n")

    return


def get_osemosys_cloud_stage_from_user(config_dict):
    
    #depdning on whether we are running on osemosys cloud or not, we will run differtent functions:
    if config_dict['solving_method'] == 'cloud':
        osemosys_cloud_input=None
        while osemosys_cloud_input == None:
            try:
                prompt = f"Dear human, have you put the zip files from osemosys-cloud.com into the tmp directory for this run? (y/n): "
                osemosys_cloud_input = input(prompt).lower()
                if osemosys_cloud_input == 'y':
                    logger.info("Great, I will load the data in and spit it back out as results for you. beep boop beep.")
                    return osemosys_cloud_input
                elif osemosys_cloud_input == 'n':
                    logger.info("Please put the zip files from osemosys-cloud.com into the tmp directory and then run the code again. beep boop beep.")
                    return osemosys_cloud_input
                else:
                    logger.info("Please enter y or n")
                    osemosys_cloud_input = None
            except:
                logger.info("Please enter y or n or exit with ctrl+c")
                osemosys_cloud_input = None

def write_data_config_to_new_file(paths_dict,config_dict):
    """write a new data config file to the tmp folder. This may include changes to the original data config file, such as shortened names. the data config will have the same strucutre as the original config/*data_config*.yml, but with different values"""
    new_data_config = config_dict['data_config']
    path_to_new_data_config = paths_dict['path_to_new_data_config']
    with open(path_to_new_data_config, 'w') as outfile:
        yaml.dump(new_data_config, outfile, default_flow_style=False)
    return
    
