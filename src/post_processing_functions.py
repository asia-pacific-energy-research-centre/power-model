import pandas as pd
import numpy as np
import yaml
import os
import subprocess
import zipfile
import sys
import warnings
import logging
logger = logging.getLogger(__name__)
#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

warnings.filterwarnings("ignore", message="In a future version, the Index constructor will not infer numeric dtypes when passed object-dtype sequences (matching Series behavior)")

def remove_apostrophes_from_region_names(paths_dict, config_dict):
    #remove apostrophes from the region names in the results files if they are in there.
    tmp_directory = paths_dict['tmp_directory']#todo is ./tmp/19_THA/Reference/StorageLevelDayTypeStart.csv in results_sheets? and what about AnnualTechnologyEmission. it seems like we are getting all these random values added,
    for sheet in config_dict['results_sheets']:
        fpath = f'{tmp_directory}/{sheet}.csv'
        logger.info('removing apostrophes from',fpath)#todo remove
        _df = pd.read_csv(fpath).reset_index(drop=True)
        #change the region names to remove apostrophes if they are at the start or end of the string
        _df['REGION'] = _df['REGION'].str.strip("'")
        _df.to_csv(fpath,index=False)

    return

def check_for_missing_and_empty_results(paths_dict, config_dict):
    #check if all the results are there or at least not empty. If they are then its probably just because the user forgot to remove it from the config file, so jsut write a wanring and then remove it from the results_sheets list
    logging.info('\n\n##################################\nChecking for missing results:')
    #     tmp_directory = paths_dict['tmp_directory']
    # sheet= 'StorageLevelDayTypeFinish'
    # fpath = f'{tmp_directory}/{sheet}.csv'
    tmp_directory = paths_dict['tmp_directory']
    #create list of results sheets so we arent iterating over the list we are changing!
    results = config_dict['results_sheets'].copy()
    for sheet in results:
        fpath = f'{tmp_directory}/{sheet}.csv'
        if not os.path.exists(fpath):
            logging.warning(f'WARNING: {sheet} does not exist. It will not be in the results. This occured during check_for_missing_results()')
            config_dict['results_sheets'].remove(sheet)
            continue
        else:#chekc if empty
            df = pd.read_csv(fpath)
            if df.empty:
                config_dict['results_sheets'].remove(sheet)
                logging.warning(f'WARNING: {sheet} is empty. Ignoring it and continuing with the rest of the results. This occured during check_for_missing_results().')
                continue
    ######################
    #if we are doing cloud, we will also check for results that are in the tmp folder but not in the results_config file
    #get all csv files in the temp directory
    if config_dict['solving_method'] == 'cloud':
        files = [f for f in os.listdir(tmp_directory) if f.endswith('.csv')]
        for f in files:
            #check if it is in the results_sheets list, if not add it
            if f.split('.')[0] not in config_dict['results_sheets']:
                config_dict['results_sheets'].append(f.split('.')[0])
                logging.warning(f'WARNING: {f.split(".")[0]} is in the tmp folder but not in the results_sheets list. This occured during check_for_missing_results().')
    ######################
    #and check for resutls that soehow got added to the results_sheets list but are not in the data_config as results #todo remove this if it no longer happens
    data_config = config_dict['data_config']
    for sheet in config_dict['results_sheets']:
        if data_config[sheet]['type'] != 'result':
            logger.error(f'ERROR: {sheet} is not a result sheet. Please check the code as this shouldnt happen. This occured during remove_apostrophes_from_region_names(). Exiting')#have a hunch this will occur but one day should remove.
            sys.exit()
    logging.info('Done checking for missing results\n##################################\n\n')
    return config_dict

def save_results_as_excel(paths_dict, config_dict):
    tmp_directory = paths_dict['tmp_directory']

    # Now we take the CSV files and combine them into an Excel file
    # First we need to make a dataframe from the CSV files
    # Note: if you add any new result parameters to osemosys_fast.txt, you need to update the config.yml you are using        
    results_df={}
    for sheet in config_dict['results_sheets']:
        fpath = f'{tmp_directory}/{sheet}.csv'
        df = pd.read_csv(fpath)
        df = df.reset_index(drop=True)
        results_df[sheet] = df

    results_dfs = {}
    results_dfs = {k:v for (k,v) in results_df.items() if not v.empty}
    _result_tables = {}

    #I THINK WE CAN JUST TAKE IN THE DATA AND SAVE TI , NONE OF THIS BS
    for sheet in results_dfs.keys():
        df = results_dfs[sheet]
        indices = df.columns.tolist()
        #Please note i commented the below because i wasnt sure if it was needed. If it is needed, please uncomment it to replace the lines below it. It seems to be used in case there are duplicated rows when considering all columns except Value.  But i dont think this will happen, and if it does, we should know via an unexpected error here.
        # if 'TIMESLICE' in indices:
        #     unwanted_members = {'YEAR', 'VALUE'}
        #     _indices = [ele for ele in indices if ele not in unwanted_members]
        #     if 'YEAR' in df.columns:
        #         df = pd.pivot_table(df,index=_indices,columns='YEAR',values='VALUE',aggfunc=np.sum)#why are we summing here?
        #     df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
        #     _result_tables[sheet] = df
        # elif 'TIMESLICE' not in indices:
        #     unwanted_members = {'YEAR', 'VALUE'}
        #     _indices = [ele for ele in indices if ele not in unwanted_members]
        #     if 'YEAR' in df.columns:
        #         df = pd.pivot_table(df,index=_indices,columns='YEAR',values='VALUE')
        #     df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
        #     _result_tables[sheet] = df
        #new lines starting below:
        try:
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            if 'YEAR' in df.columns:
                df = pd.pivot_table(df,index=_indices,columns='YEAR',values='VALUE')
            df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
            _result_tables[sheet] = df
        except:
            logger.error(f'ERROR: error thrown when trying to pivot table {sheet}. Please check the code because some changes were made that might have caused this error. Exiting')
            sys.exit()
        #end of new lines
        _result_tables[sheet]=_result_tables[sheet].fillna(0)
    results_tables = {k: v for k, v in _result_tables.items() if not v.empty}

    # We take the dataframe of results and save to an Excel file
    logger.info("Creating the Excel file of results. Results saved in the results folder.")

    #if results tables not empty then save to excel
    if results_tables:
        with pd.ExcelWriter(paths_dict['results_workbook']) as writer:
            for k, v in results_tables.items():
                #if the name of the sheet is more than 31 characters, check if there is a short name in the data_config file, else use the first 31 characters of the sheet name
                if len(k) > 31:
                    if k in config_dict['data_config'].keys():#sometimes may nto be in data config, so in results sheets only
                        if 'short_name' in config_dict['data_config'][k].keys():
                            k = config_dict['data_config'][k]['short_name']
                        else:
                              k = k[:31]
                    else:
                        k = k[:31]
                v.to_excel(writer, sheet_name=k, merge_cells=False)
    else:
        logger.error('ERROR: No results were found while trying to save them to excel. Exiting')
        sys.exit()
    return config_dict

def save_results_as_long_csv(paths_dict, config_dict):
    tmp_directory = paths_dict['tmp_directory']

    # print('There are probably significant issues with this function because it is also saving the data config files to the long csv')
    
    # #create_lsit of csvs in tmp_directory:
    # csv_list = [x for x in os.listdir(tmp_directory) if x.split('.')[-1] == 'csv']
    combined_data = pd.DataFrame()
    #iterate through sheets in tmp
    if len(config_dict['results_sheets']) == 0:
        logger.error('ERROR: no results sheets found in the data config file. Probably because they were removed earlier. Exiting')
        sys.exit()

    for sheet in config_dict['results_sheets']:
        #load in sheet
        file = sheet+'.csv'
        sheet_data = pd.read_csv(tmp_directory+'/'+file)

        # #The trade file will have two Region columns. Set the second one to be 'REGION_TRADE'
        # if file == 'Trade.csv':
        #     sheet_data.rename(columns={'REGION.1':'REGION_TRADE'}, inplace=True)

        #add sheet as a column 
        sheet_data['SHEET_NAME'] = sheet
        #if this is the first sheet then create a dataframe to hold the data
        if sheet == config_dict['results_sheets'][0]:
            combined_data = sheet_data
        #if this is not the first sheet then append the data to the combined data
        else:
            combined_data = pd.concat([combined_data, sheet_data], ignore_index=True)

    #remove any coluymns with all na's
    combined_data = combined_data.dropna(axis=1, how='all')

    #count number of na's in each column and then order the cols in a list by the number of na's. We'll use this to order the cols in the final dataframe
    na_counts = combined_data.isna().sum().sort_values(ascending=True)
    ordered_cols = list(na_counts.index)

    #reorder the columns so the year cols are at the end, the ordered first cols are at start and the rest of the cols are in the middle
    new_combined_data = combined_data[ordered_cols]

    #CREATE TWO TALL DFS. ONE WHERE THE YEARS ARE COLUMNS AND THE OTHER WHERE THE SHEET_NAME'S ARE COLUMNS:
    #YEAR COLUMNS
    #pivot so each unique vlaue in sheet name is a column and value is the value in the value column
    other_cols = new_combined_data.columns.difference(['YEAR','VALUE']).tolist()
    new_combined_data_year_tall = new_combined_data.pivot(index=other_cols, columns='YEAR', values='VALUE').reset_index()
    #SHEET_NAME COLUMNS
    other_cols = new_combined_data.columns.difference(['SHEET_NAME','VALUE']).tolist()
    new_combined_data_sheet_name_tall = new_combined_data.pivot(index=other_cols, columns='SHEET_NAME', values='VALUE').reset_index()

    #save combined data to csv
    new_combined_data_year_tall.to_csv(paths_dict['combined_results_tall_years'], index=False)
    new_combined_data_sheet_name_tall.to_csv(paths_dict['combined_results_tall_sheet_names'], index=False)

    return


def create_res_visualisation(paths_dict,config_dict):

    results_directory = paths_dict['results_directory']
    path_to_input_data_file = paths_dict['path_to_input_data_file']
    path_to_data_config = paths_dict['path_to_data_config']
    economy = config_dict['economy']
    scenario = config_dict['scenario']
    #run visualisation tool
    #https://otoole.readthedocs.io/en/latest/

    #PLEASE NOTE THAT THE VIS TOOL REQUIRES THE PACKAGE pydot TO BE INSTALLED. IF IT IS NOT INSTALLED, IT WILL THROW AN ERROR. TO INSTALL IT, RUN THE FOLLOWING COMMAND IN THE TERMINAL: pip install pydot OR conda install pydot

    #For some reason we cannot make the terminal command work in python, so we have to run it in the terminal. The following command will print the command to run in the terminal:

    # path_to_data_config = f'{root_dir}/config/{data_config_file}'
    path_to_visualisation = f'{results_directory}/energy_system_visualisation_{scenario}_{economy}.png'

    # path_to_data_config = f'{root_dir}/config/{data_config_file}'
    command = f'otoole viz res datafile {path_to_input_data_file} {path_to_visualisation} {path_to_data_config}'
    logger.info(f'Please run the following command in the terminal to create the visualisation:\n{command}')
    
    return

def extract_osmosys_cloud_results_txt_to_csv(paths_dict,config_dict):#,remove_results_txt_file):
    """This function will extract the results.txt file from the osmosys cloud and convert it to csvs like we would if we ran osemosys locally. 
    
    The strength of this comapred to aggregate_and_edit_osemosys_cloud_csvs is it is less removed from the process used for local runs as it uses otoole to convert from the results.txt file to csvs. The weakness is also that it relies on otoole, if for some reason otoole is being troublesome. That means that if you are using the cloud because something is not working lcoally, then this may not work either.
    
    Like with aggregate_and_edit_osemosys_cloud_csvs() you will need to make sure to download the correct .zip file and put it in the tmp_directory before usign this function, else it will not work.
     """
    tmp_directory = paths_dict['tmp_directory']
    path_to_data_config = paths_dict['path_to_data_config']

    #load in the result.txt file from the zip file called 'output_30685.zip' where 30685 can be any number. If there are multiple zip files then trhow an error, else load in the result.txt file from the zip file
    zip_files = [x for x in os.listdir(tmp_directory) if x.split('.')[-1] == 'zip' and x.split('_')[0] == 'output']
    if len(zip_files) != 1:
        logger.error("Error: Expected to find one output zip file in tmp directory but found {}".format(len(zip_files)))
        sys.exit()
    
    zip_files = zip_files[0]
    #now unzip the file. there will be a file called data.txt, metadata.json and result.txt. We only want the result.txt file
    with zipfile.ZipFile(os.path.join(paths_dict['tmp_directory'],zip_files), 'r') as zip_ref:
        zip_ref.extractall(paths_dict['tmp_directory'])#todo double check no eorrrors will occur if there is already a results file in the tmp directory. maybe it jsut replaces file, but it might be worth deleting the file if ti is there first?
    
    #we will just run the file through the f"otoole results cbc csv {tmp_directory}/cbc_results_{economy}_{scenario}.txt {tmp_directory} {path_to_results_config}" script to make the csvs. That script is from the model_solving_functions.solve_model() function

    #convert to csv
    #check if old_model_file_path contains osemosys_fast.txt, if so we need to include the input data file.txt in the call, with --input_datafile.
    if 'osemosys_fast.txt' in paths_dict['osemosys_model_script_path']:
        #we have to include the input data file.txt in the call, with --input_datafile. 
        command = f"otoole results --input_datafile {paths_dict['path_to_input_data_file']} cbc csv {tmp_directory}/result.txt {tmp_directory} {path_to_data_config}"
    elif 'osemosys.txt' in paths_dict['osemosys_model_script_path']:
        command = f"otoole results cbc csv {tmp_directory}/result.txt {tmp_directory} {path_to_data_config}"
    else:
        logger.error("Error: Original OseMOSYS model file path does not contain osemosys.txt or osemosys_fast.txt. This will affect the results from osemosys cloud. Please check the path and do the process again.")
        sys.exit()

    result = subprocess.run(command,shell=True, capture_output=True, text=True)
    logger.info(f"Printing command line output from converting OsMOSYS CLOUD output to csv \n{command}\n{result.stdout}\n{result.stderr}")

    #check what files have been extracted and whether they match the ones in config_dict['results_sheets']. These strings must contains .csv at the end. This cannot be done using split 
    extracted_files = [x for x in os.listdir(tmp_directory) if x.endswith('.csv')]

    expected_files = [f"{x}.csv" for x in config_dict['results_sheets']]
    for file in expected_files:
        if file not in extracted_files:
            warning = f"Warning: Expected to find a file called {file} in the tmp directory but did not find it. It will not be in the results."
            #drop file from config_dict['results_sheets']
            config_dict['results_sheets'].remove(file.split('.')[0])
        
            config_dict['missing_results_and_warning_message'].append([file.split('.')[0], warning])
    for file in extracted_files:
        if file not in expected_files:
            logger.warning(f"WARNING: Found a file called {file} in the tmp directory but did not expect it. It will be in the results.")
            #add file to config_dict['results_sheets']
            config_dict['results_sheets'].append(file.split('.')[0])
            

    #remove any csvs which dont have the economy_name in their REGION column
    for file in config_dict['results_sheets']:
        df = pd.read_csv(os.path.join(tmp_directory, f"{file}.csv"))
        if 'REGION' in df.columns and len(df) > 0:
            if df['REGION'].unique()[0] != config_dict['economy']:
                config_dict['results_sheets'].remove(file.split('.')[0])
                warning = f"Warning: Found a file called {file} in the tmp directory but the REGION column does not contain the economy name {config_dict['economy']}. It will not be in the results."
                config_dict['missing_results_and_warning_message'].append([file.split('.')[0], warning])

    return config_dict

def aggregate_and_edit_osemosys_cloud_csvs(paths_dict, config_dict):
    """Osemosys cloud gives you a zip file of csvs which contain the results of the model. This function will aggregate the csvs into one csv and then edit the csv so it is in the same format as the csvs we get when we run osemosys locally. This means we can use the same functions to analyse the results from both osemosys cloud and osemosys locally. 
    A major part of this will jsut be renaming columns from single letters to the column names used in the data config file. 

    The strenght of using this function compared to extract_osmosys_cloud_results_txt_to_csv is that it is doesnt rely on otoole to extract the results and so if something is not working with the way otoole extracts the results, then this function will still work. However, it will not extract any extra information besides what is instructed to be extracted in the data config file.

    Like with extract_osmosys_cloud_results_txt_to_csv() you will need to make sure to download the correct .zip file and put it in the tmp_directory before usign this function, else it will not work.
    """
    #take in csvs from the zip file from osemosys cloud and then the data config file and convert the column names from what they are in the csvs to what they are in the data config file. We can do this using the code from the osemosys cloud server which is hosted on github here https://github.com/ClimateCompatibleGrowth/osemosys-cloud

    #first find the csv files in the tmp_directory. They will be in a zip file with the naming convention: csv_30685.zip where 30685 could be any number.
    csv_zip_file = [f for f in os.listdir(paths_dict['tmp_directory']) if f.endswith('.zip') and f.startswith('csv_')]
    if len(csv_zip_file) != 1:
        logger.error("Error: Expected to find one csv zip file in tmp directory but found {}".format(len(csv_zip_file)))
        sys.exit()
    csv_zip_file = csv_zip_file[0]
    #now unzip the file. there will be the csvs in a folder called csv
    with zipfile.ZipFile(os.path.join(paths_dict['tmp_directory'],csv_zip_file), 'r') as zip_ref:
        zip_ref.extractall(paths_dict['tmp_directory'])#todo double check no eorrrors will occur if there is already a csv folder in the tmp directory. maybe it jsut replaces file, but it might be worth deleting the folder if ti is there first?

    #now find the csvs in the csv folder
    csv_files = [f for f in os.listdir(os.path.join(paths_dict['tmp_directory'],'csv')) if f.endswith('.csv')]

    #now we need to rename the columns in the csvs to match the data config file. We can do this by using the dictionary below.
    #the dictionary below is the set of indices used for each possible output csv from the cloud. It might change in the future so it could be worth checking this if you are having problems with the osemosys server. You can find it here https://github.com/ClimateCompatibleGrowth/osemosys-cloud/blob/e0f110235811e6f860a97c9f5e223b6126e3e6f9/scripts/postprocess_results.py#L238
    osemosys_cols = {'NewCapacity':['r','t','y'],
        'AccumulatedNewCapacity':['r','t','y'],
        'TotalCapacityAnnual':['r','t','y'],
        'CapitalInvestment':['r','t','y'],
        'AnnualVariableOperatingCost':['r','t','y'],
        'AnnualFixedOperatingCost':['r','t','y'],
        'SalvageValue':['r','t','y'],
        'DiscountedSalvageValue':['r','t','y'],
        'TotalTechnologyAnnualActivity':['r','t','y'],
        'RateOfActivity':['r','l','t','m','y'],
        'RateOfTotalActivity':['r','t','l','y'],
        'Demand':['r','l','f','y'],
        'TotalAnnualTechnologyActivityByMode':['r','t','m','y'],
        'TotalTechnologyModelPeriodActivity':['r','t'],
        'ProductionByTechnology':['r','l','t','f','y'],
        'ProductionByTechnologyAnnual':['r','t','f','y'],
        'AnnualTechnologyEmissionByMode':['r','t','e','m','y'],
        'AnnualTechnologyEmission':['r','t','e','y'],
        'AnnualEmissions':['r','e','y'],
        'DiscountedTechnologyEmissionsPenalty':['r','t','y'],
        'RateOfProductionByTechnology':['r','l','t','f','y'],
        'RateOfUseByTechnology':['r','l','t','f','y'],
        'UseByTechnology':['r','l','t','f','y'],
        'RateOfProductionByTechnologyByMode':['r','l','t','f','m','y'],
        'RateOfUseByTechnologyByMode':['r','l','t','f','m','y'],
        'TechnologyActivityChangeByMode':['r','t','m','y'],
        'TechnologyActivityChangeByModeCostTotal':['r','t','m','y'],
        'InputToNewCapacity':['r','t','f','y'],
        'InputToTotalCapacity':['r','t','f','y'],
        'DiscountedCapitalInvestment':['r','t','y'],
        'DiscountedOperatingCost':['r','t','y'],
        'TotalDiscountedCostByTechnology':['r','t','y'],
        'NumberOfNewTechnologyUnits':['r','t','y'],
        'NewStorageCapacity':['r','s','y'],
        'SalvageValueStorage':['r','s','y'],
        'StorageLevelYearStart':['r','s','y'],
        'StorageLevelYearFinish':['r','s','y'],
        'StorageLevelSeasonStart':['r','s','ls','y'],
        'StorageLevelDayTypeStart':['r','s','ls','ld','y'],
        'StorageLevelDayTypeFinish':['r','s','ls','ld','y'],
        'DiscountedSalvageValueStorage':['r','s','y'],
        'Charging':['r','s','f','l','y'],
        'Discharging':['r','s','f','l','y'],
        'RateOfNetStorageActivity':['r','s','ls','ld','lh','y'],
        'NetChargeWithinYear':['r','s','ls','ld','lh','y'],
        'NetChargeWithinDay':['r','s','ls','ld','lh','y'],
        'StorageLowerLimit':['r','s','y'],
        'StorageUpperLimit':['r','s','y'],
        'AccumulatedNewStorageCapacity':['r','s','y'],
        'CapitalInvestmentStorage':['r','s','y'],
        'DiscountedCapitalInvestmentStorage':['r','s','y'],
        'DiscountedSalvageValueStorage':['r','s','y'],
        'TotalDiscountedStorageCost':['r','s','y'],
        'RateOfNetStorageActivity':['r','s','ls','ld','lh','y'],
    }
    cloud_region_column = 'r'#change this if the cloud changes the name of the region column

    #for each key in the dictionary above:
    # check if there is a csv of the same name and load it
    # find it in the config file
    #and then, making the assumption that the orders are the same, (they have to be unless you have cahnged the order of columns within the osemosys model file (eg. osemosys_fast.txt)) convert the column names in the csv from the single letter names in the dictionary and csv to the names in the config file.

    #HOWEVER, although i cant find out why its happening, if the coincbc program being run in osemosys cloud doesnt calculate the actual values for that sheet, the osemosys cloud server will still create a csv with the correct column names, but with what seems like default values, such as REGION=RE1(i guess it stands for region 1), and then all manner of odd TECHNOLOGY values. So we will check if the csv is correct by checking if the REGION is = to the economy. If it is not, we will not use it.

    list_of_missing_csvs = []
    list_of_keys_not_in_config = []
    list_of_keys_not_in_results = []

    for key in osemosys_cols.keys():
        #load csv
        if key + '.csv' in csv_files:
            csv = pd.read_csv(os.path.join(paths_dict['tmp_directory'],'csv',key+'.csv'))

            #check if economy is in the csvs REGION column
            if cloud_region_column in csv.columns:
                if config_dict['economy'] not in csv[cloud_region_column].values:
                    logger.info('The csv for {} does not contain the economy {} in the REGION column. This is likely because the coincbc program did not calculate the values for this sheet. This sheet will not be used.'.format(key, config_dict['economy']))
                    if key in config_dict['results_sheets']:
                        config_dict['results_sheets'].remove(key)
                        warning = 'The csv for {} does not contain the economy {} in the REGION column. This is likely because the coincbc program did not calculate the values for this sheet. This sheet will not be used.'.format(key, config_dict['economy'])
                        config_dict['missing_results_and_warning_message'].append([key,warning])
                    continue
                    
            if (key in config_dict['data_config'].keys()) and (key in config_dict['results_sheets']):
                #rename the columns
                for i, col in enumerate(osemosys_cols[key]):
                    data_config_col = config_dict['data_config'][key]['indices'][i] 
                    csv.rename(columns={col:data_config_col}, inplace=True)
                #convert the col which is the same as the key to a VALUE column
                csv.rename(columns={key:'VALUE'}, inplace=True)

                #save the csv to tmp_directory
                csv.to_csv(os.path.join(paths_dict['tmp_directory'],key+'.csv'), index=False)

                # #add the csv to a results_dict
                # results_dict[key] = csv
            else:
                if key in config_dict['data_config'].keys():
                    list_of_keys_not_in_results.append(key)
                else:
                    list_of_keys_not_in_config.append(key)
        else:
            list_of_missing_csvs.append(key)

    if list_of_missing_csvs.__len__() > 0:
        logger.info('The following csvs were not found in the csv_files list, so their data wont be in the results data: \n{}'.format(list_of_missing_csvs))
    if list_of_keys_not_in_config.__len__() > 0:
        logger.info('The following keys were not found in the data_config, so their data wont be in the results data: \n{}'.format(list_of_keys_not_in_config))
    if list_of_keys_not_in_results.__len__() > 0:
        logger.info('The following keys were not found in the results_sheets but are in data config. This could because they have calculated:False, so their data wont be in the results data: \n{}'.format(list_of_keys_not_in_results))
    #check if the csvs are in the results_sheets list, if they are, remove them
    for key in list_of_missing_csvs+list_of_keys_not_in_config+list_of_keys_not_in_results:
        if key in config_dict['results_sheets']:
            config_dict['results_sheets'].remove(key)
            warning = 'The csv for {} was not found in the csv_files list, so its data wont be in the results data.'.format(key)
            config_dict['missing_results_and_warning_message'].append([key,warning])

    return config_dict


def process_osemosys_cloud_results(paths_dict, config_dict):

    #do this to extract results form the zip files you get from the cloud. Will only occur if we are running the function using osemosys_cloud_input=y
    if config_dict['osemosys_cloud_input'] == 'y':
        if config_dict['extract_osemosys_cloud_results_using_otoole']:
            config_dict = extract_osmosys_cloud_results_txt_to_csv(paths_dict,config_dict)
            #to do why does this only extract a few of the files we want to extract? i expect its a problem related to the general way we extract results, even with non cloud results.
        else:
            config_dict = aggregate_and_edit_osemosys_cloud_csvs(paths_dict,config_dict)
    return config_dict

def print_missing_results_sheets_and_warnings(config_dict):
    #print the missing results sheets and warnings to a txt file
    logger.info('\n\n########################################\nThe following sheets were not found in the results:')
    for sheet,warning in config_dict['missing_results_and_warning_message']:
        logger.info('Sheet: {}\nWarning: {}\n'.format(sheet,warning))
    