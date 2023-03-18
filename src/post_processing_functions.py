import pandas as pd
import numpy as np
import yaml
import os
import time
import subprocess
import zipfile
import sys
import warnings
#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

warnings.filterwarnings("ignore", message="In a future version, the Index constructor will not infer numeric dtypes when passed object-dtype sequences (matching Series behavior)")

def remove_apostrophes_from_region_names(paths_dict, config_dict):
    #remove apostrophes from the region names in the results files if they are in there.

    #if remove_all_in_temp_dir is True, then all csv files in the temp directory will be checked for apostrophes, else only the results files will be checked. This is a way of including files that are not in the results_config file
    data_config = config_dict['data_config']

    if config_dict['solving_method'] == 'cloud':
        tmp_directory = paths_dict['tmp_directory']

        #get all csv files in the temp directory
        files = [f for f in os.listdir(tmp_directory) if f.endswith('.csv')]
        for f in files:
            fpath = f'{tmp_directory}/{f}'
            _df = pd.read_csv(fpath).reset_index(drop=True)
            #change the region names to remove apostrophes if they are at the start or end of the string
            _df['REGION'] = _df['REGION'].str.strip("'")
            _df.to_csv(fpath,index=False)
        return
    else:
        tmp_directory = paths_dict['tmp_directory']
        for sheet in config_dict['results_sheets']:
            if data_config[sheet]['type'] == 'result':
                fpath = f'{tmp_directory}/{sheet}.csv'
                #chekc if file exists
                if not os.path.exists(fpath):
                    print(f'File {fpath} does not exist')#We need to double check we are handling data_config and results_config correctly
                    continue
                #print(fpath)
                _df = pd.read_csv(fpath).reset_index(drop=True)
                #change the region names to remove apostrophes if they are at the start or end of the string
                _df['REGION'] = _df['REGION'].str.strip("'")
                _df.to_csv(fpath,index=False)
        return

def save_results_as_excel(paths_dict, config_dict,sheets_to_ignore_if_error_thrown):
    tmp_directory = paths_dict['tmp_directory']

    # Now we take the CSV files and combine them into an Excel file
    # First we need to make a dataframe from the CSV files
    # Note: if you add any new result parameters to osemosys_fast.txt, you need to update the config.yml you are using        
    results_df={}
    for sheet in config_dict['results_sheets']:
        if sheet in sheets_to_ignore_if_error_thrown:
            
            fpath = f'{tmp_directory}/{sheet}.csv'
            try:
                df = pd.read_csv(fpath).reset_index(drop=True)
                results_df[sheet] = df
            except:
                print(f'WARNING: error thrown when trying to read {fpath} Ignoring it and continuing with the rest of the results')
                continue

        fpath = f'{tmp_directory}/{sheet}.csv'
        #print(fpath)
        try:
            df = pd.read_csv(fpath)
        except:
            print(f'ERROR: error thrown when trying to read {fpath} It is probably not available. Exiting')
            sys.exit()
        df = df.reset_index(drop=True)
        results_df[sheet] = df

    results_dfs = {}
    results_dfs = {k:v for (k,v) in results_df.items() if not v.empty}
    _result_tables = {}

    #I THINK WE CAN JUST TAKE IN THE DATA AND SAVE TI , NONE OF THIS BS
    for sheet in results_dfs.keys():
        df = results_dfs[sheet]
        indices = df.columns.tolist()
        if 'TIMESLICE' in indices:
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            if 'YEAR' in df.columns:
                df = pd.pivot_table(df,index=_indices,columns='YEAR',values='VALUE',aggfunc=np.sum)#why are we summing here?
            df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
            _result_tables[sheet] = df
        elif 'TIMESLICE' not in indices:
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            if 'YEAR' in df.columns:
                df = pd.pivot_table(df,index=_indices,columns='YEAR',values='VALUE')
            df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
            _result_tables[sheet] = df
        
        _result_tables[sheet]=_result_tables[sheet].fillna(0)
    results_tables = {k: v for k, v in _result_tables.items() if not v.empty}

    # We take the dataframe of results and save to an Excel file
    print("Creating the Excel file of results. Results saved in the results folder.")
    config_dict['scenario'] = config_dict['scenario'].lower()
    #if results tables not empty then save to excel
    if results_tables:
        with pd.ExcelWriter(paths_dict['results_workbook']) as writer:
            for k, v in results_tables.items():
                #if the name of the sheet is more than 31 characters, check if there is a short name in the data_config file, else use the first 31 characters of the sheet name
                if len(k) > 31:
                    if k in config_dict['data_config'].keys():
                        if 'short_name' in config_dict['data_config'][k].keys():
                            k = config_dict['data_config'][k]['short_name']
                        else:
                              k = k[:31]
                    else:
                        k = k[:31]
                v.to_excel(writer, sheet_name=k, merge_cells=False)
    return

def save_results_as_long_csv(paths_dict, config_dict,sheets_to_ignore_if_error_thrown):
    tmp_directory = paths_dict['tmp_directory']

    # print('There are probably significant issues with this function because it is also saving the data config files to the long csv')
    
    # #create_lsit of csvs in tmp_directory:
    # csv_list = [x for x in os.listdir(tmp_directory) if x.split('.')[-1] == 'csv']
    combined_data = pd.DataFrame()
    #iterate through sheets in tmp
    for sheet in config_dict['results_sheets']:
        if sheet in sheets_to_ignore_if_error_thrown:
            file = sheet+'.csv'
            try:
                sheet_data = pd.read_csv(tmp_directory+'/'+file)
            except:
                print(f'Error thrown when trying to read {file}')
                continue
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
    print('Please run the following command in the terminal to create the visualisation:\n')
    print(command)
    
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
        print("Error: Expected to find one output zip file in tmp directory but found {}".format(len(zip_files)))
        sys.exit()
    
    zip_files = zip_files[0]
    #now unzip the file. there will be a file called data.txt, metadata.json and result.txt. We only want the result.txt file
    with zipfile.ZipFile(os.path.join(paths_dict['tmp_directory'],zip_files), 'r') as zip_ref:
        zip_ref.extractall(paths_dict['tmp_directory'])#todo double check no eorrrors will occur if there is already a results file in the tmp directory. maybe it jsut replaces file, but it might be worth deleting the file if ti is there first?
    
    #we will just run the file through the f"otoole results cbc csv {tmp_directory}/cbc_results_{economy}_{scenario}.txt {tmp_directory} {path_to_results_config}" script to make the csvs. That script is from the model_solving_functions.solve_model() function

    start = time.time()
    command=f"otoole results cbc csv {tmp_directory}/result.txt {tmp_directory} {path_to_data_config}"
    result = subprocess.run(command,shell=True, capture_output=True, text=True)
    print("\n Printing command line output from converting OsMOSYS CLOUD output to csv \n")#results_cbc_{economy}_{scenario}.txt
    print(command+'\n')
    print(result.stdout+'\n')
    print(result.stderr+'\n')
    print('\n Time taken: {} for converting OsMOSYS CLOUD output to csv \n\n########################\n '.format(time.time()-start))

    #check what files have been extracted and whether they match the ones in config_dict['results_sheets']. These strings must contains .csv at the end. This cannot be done using split 
    extracted_files = [x for x in os.listdir(tmp_directory) if x.endswith('.csv')]

    expected_files = [f"{x}.csv" for x in config_dict['results_sheets']]
    for file in expected_files:
        if file not in extracted_files:
            print(f"WARNING: Expected to find a file called {file} in the tmp directory but did not find it. It will not be in the results.")
            #drop file from config_dict['results_sheets']
            config_dict['results_sheets'].remove(file.split('.')[0])
    for file in extracted_files:
        if file not in expected_files:
            print(f"WARNING: Found a file called {file} in the tmp directory but did not expect it. It will be in the results.")
            #add file to config_dict['results_sheets']
            config_dict['results_sheets'].append(file.split('.')[0])

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
        print("Error: Expected to find one csv zip file in tmp directory but found {}".format(len(csv_zip_file)))
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
            if 'REGION' in csv.columns:
                if config_dict['economy'] not in csv['REGION'].values:
                    #if it is not, then we will not use it
                    print('The csv for {} does not contain the economy {} in the REGION column. This is likely because the coincbc program did not calculate the values for this sheet. This sheet will not be used.'.format(key, config_dict['economy']))
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
        print('\nWARNING: The following csvs were not found in the csv_files list, so their data wont be in the results data: \n{}'.format(list_of_missing_csvs))
    if list_of_keys_not_in_config.__len__() > 0:
        print('\nWARNING: The following keys were not found in the data_config, so their data wont be in the results data: \n{}'.format(list_of_keys_not_in_config))
    if list_of_keys_not_in_results.__len__() > 0:
        print('\nWARNING: The following keys were not found in the results_sheets but are in data config. This could because they have calculated:False, so their data wont be in the results data: \n{}'.format(list_of_keys_not_in_results))

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