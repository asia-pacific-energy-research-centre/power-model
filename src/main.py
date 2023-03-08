# this script takes in the power data sheet and runs the osemosys model
# configure the model run in the START tab of the excel file
# You can run this file from the command line or using jupyter interactive notebook. 

# the following python packages are imported:
#%%
import pandas as pd
import numpy as np
import yaml
import os
from otoole.read_strategies import ReadExcel#had to isntall this pyparsing previously. ist this still necessary?
from otoole.write_strategies import WriteDatafile
import subprocess
import time
from post_processing_functions import compare_combined_data_to_data_config, create_res_visualisation
# the processing script starts from here
# get the time you started the model so the results will have the time in the filename
model_start = time.strftime("%Y-%m-%d-%H%M%S")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
config_dir = 'config'
print(f"Script started at {model_start}...\n")
# model run inputs
#%%
################################################################################
#FOR RUNNING THROUGH JUPYTER INTERACTIVE NOTEBOOK (FINNS SETUP, need to make root of project the cwd)

def is_notebook() -> bool:
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter
    
if is_notebook():
    #make directory the root of the project
    if os.getcwd().split('\\')[-1] == 'src':
        os.chdir('..')
        print("Changed directory to root of project")

################################################################################
#save name of the inputted data sheet here for ease of use:
input_data_sheet_file= "data-sheet-power-finn-test.xlsx"#current data-sheet-power has no data in it
data_config_file = "data_config_copy.yml"
results_config_file = "results_config_copy_test.yml"
#define the model script you will use (one of osemosys_fast.txt, osemosys.txt, osemosys_short.txt)
osemosys_model_script = 'osemosys_fast.txt'
#%%

################################################################################
#PREPARE DATA
#preparation is done to clean up the input data that was manually created in the excel file. This most notably involves filtering for the specific scenario economy and years we want to model, and removing columns that are not needed.
# The output is a txt file that is the input data for OSeMOSYS. This is saved in the tmp folder for the economy and we are running the model for.
#this is like the otoole Convert step but allows for customised use of the data sheet
################################################################################

#start timer
start = time.time()

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

# get the names of parameters to read in the next step
with open(f'{root_dir}/config/{data_config_file}') as f:
    data_config = yaml.safe_load(f)

##change to handle v1.0 of otoole:
#create dataconfig with short_name as key so that its keys can be compared to the keys in the data sheet
short_to_long_name = {}
new_dict = data_config.copy()
for key,value in data_config.items():
    #check if there is a short_name
    if 'short_name' not in data_config[key]:
        continue
    short_to_long_name[data_config[key]['short_name']] = key
    new_key = data_config[key]['short_name']
    new_dict[new_key] = new_dict.pop(key)
#replace data_config with new_dict
data_config_short_names = new_dict.copy()

#print time 
print("Time taken: {}".format(time.time()-start))
#%%
# read in the data file and filter based on the specific scenario and preferences
subset_of_economies = economy
input_data_raw = pd.read_excel(f"{root_dir}/data/{input_data_sheet_file}",sheet_name=None) # creates dict of dataframes
print("Excel file successfully read.\n")

print("Time taken: {}".format(time.time()-start))
#%%
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

print("Time taken: {}".format(time.time()-start))
#%%
# write the data from the last step as an Excel file. This is the input data OSeMOSYS will use.
tmp_directory = f'{root_dir}/tmp/{economy}/{scenario}'
#check if tmp directory, and the economy subdir exists, if not create it
if not os.path.exists(tmp_directory):
    os.makedirs(tmp_directory)

path_to_data_sheet = f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'
with pd.ExcelWriter(path_to_data_sheet) as writer:
    for k, v in filtered_data.items():
        v.to_excel(writer, sheet_name=k, index=False, merge_cells=False)
print("Combined file of Excel input data has been written to the tmp folder.\n")

# The data needs to be converted from the Excel format to the text file format. We use otoole for this task.
subset_of_years = config_dict['years']

print("Time taken: {}".format(time.time()-start))
#%%
_path=f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'
#run testing function to check for issues with the data
compare_combined_data_to_data_config(data_config_short_names,filtered_data)

#%%
# prepare data using otoole
_path=f'{tmp_directory}/combined_data_{economy}_{scenario}.xlsx'
reader = ReadExcel(user_config=data_config)
writer = WriteDatafile(user_config=data_config)
data, default_values = reader.read(_path)
print("Time taken: {}".format(time.time()-start))
#%%
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

#%%
output_file = f'{tmp_directory}/datafile_from_python_{economy}_{scenario}.txt'
writer.write(filtered_data2, output_file, default_values)

print("data file in text format has been written and saved in the tmp folder.\n")
print("Time taken: {}".format(time.time()-start))
#%%
################################################################################
#SOLVE MODEL
#Pull in the prepared data file and solve the model
################################################################################
#start new timer to time the solving process
start = time.time()
path_to_results_config = f'{root_dir}/{config_dir}/{results_config_file}'
#save copy of outputs to txt file in case of error:
log_file = open(f'{tmp_directory}/process_output_{economy}_{scenario}.txt','w')
# We first make a copy of osemosys_fast.txt so that we can modify where the results are written.
# Results from OSeMOSYS come in csv files. We first save these to the tmp directory for each economy.
# making a copy of the model file in the tmp directory so it can be modified

#testing:
for osemosys_model_script in ['osemosys_fast.txt']:#,'osemosys.txt', 'osemosys_short.txt']:
    print(f'\n######################## \n Running solve process using{osemosys_model_script}')
    with open(f'{root_dir}/{config_dir}/{osemosys_model_script}') as t:
        model_text = t.read()
    f = open(f'{tmp_directory}/model_{economy}_{scenario}.txt','w')
    f.write('%s\n'% model_text)
    f.close()
    # Read in the file
    with open(f'{tmp_directory}/model_{economy}_{scenario}.txt', 'r') as file:
        filedata = file.read()
    # Replace the target string
    filedata = filedata.replace("param ResultsPath, symbolic default 'results';",f"param ResultsPath, symbolic default '{tmp_directory}';")
    # Write the file out again
    with open(f'{tmp_directory}/model_{economy}_{scenario}.txt', 'w') as file:
        file.write(filedata)
  
    print("\nTime taken: {}\n########################\n ".format(time.time()-start))

    #previous solving method:
    use_glpsol = True
    if use_glpsol:
        result = subprocess.run(f"glpsol -d {tmp_directory}/datafile_from_python_{economy}_{scenario}.txt -m {tmp_directory}/model_{economy}_{scenario}.txt",shell=True, capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
        print("Time taken: {} for glpsol\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write(result.stdout)
        log_file.write(result.stderr)
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))

    use_coincbc = True
    if use_coincbc:
        #new solving method (faster apparently):
        #start new timer to time the solving process
        start = time.time()

        #create a lp file to input into cbc
        result = subprocess.run(f"glpsol -d {tmp_directory}/datafile_from_python_{economy}_{scenario}.txt -m {tmp_directory}/model_{economy}_{scenario}.txt --wlp {tmp_directory}/cbc_input_{economy}_{scenario}.lp",shell=True, capture_output=True, text=True)
        print("\n Printing command line output from converting to lp file \n")
        print(result.stdout)
        print(result.stderr)
        print("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write(result.stdout)
        log_file.write(result.stderr)
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))

        #input into cbc solver:
        start = time.time()
        result = subprocess.run(f"cbc {tmp_directory}/cbc_input_{economy}_{scenario}.lp solve solu {tmp_directory}/cbc_results_{economy}_{scenario}.txt",shell=True, capture_output=True, text=True)
        print("\n Printing command line output from CBC solver \n")
        print(result.stdout)
        print(result.stderr)
        print("\n Time taken: {} for CBC solver \n\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write(result.stdout)
        log_file.write(result.stderr)
        #save time taken to log_file
        log_file.write("\n Time taken: {} for CBC solver \n\n########################\n ".format(time.time()-start))

        #convert to csv
        start = time.time()
        result = subprocess.run(f"otoole results cbc csv {tmp_directory}/cbc_results_{economy}_{scenario}.txt {tmp_directory} {path_to_results_config}",shell=True, capture_output=True, text=True)
        print("\n Printing command line output from converting cbc output to csv \n")#results_cbc_{economy}_{scenario}.txt
        print(result.stdout)
        print(result.stderr)
        print('\n Time taken: {} for converting cbc output to csv \n\n########################\n '.format(time.time()-start))
        #save stdout and err to log_file
        log_file.write(result.stdout)
        log_file.write(result.stderr)
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting cbc output to csv \n\n########################\n ".format(time.time()-start))

#close log_file
log_file.close()
    
#%%
################################################################################
#Save results as Excel workbook
################################################################################
#start new timer to tiome the post-processing
start = time.time()

# Now we take the CSV files and combine them into an Excel file
# First we need to make a dataframe from the CSV files
# Note: if you add any new result parameters to osemosys_fast.txt, you need to update results_config.yml
results_directory = f"{root_dir}/results/{economy}/{scenario}"
try:
    os.mkdir(results_directory)
except OSError:
    #print ("Creation of the directory %s failed" % path)
    pass
with open(f'{path_to_results_config}') as f:
    contents_var = yaml.safe_load(f)
results_df={}
for key,value in contents_var.items():
    if contents_var[key]['type'] == 'result':
        fpath = f'{tmp_directory}/{key}.csv'
        #print(fpath)
        _df = pd.read_csv(fpath).reset_index(drop=True)
        results_df[key] = _df
results_dfs = {}
results_dfs = {k:v for (k,v) in results_df.items() if not v.empty}
_result_tables = {}
#%%
for key,value in results_dfs.items():
    indices = contents_var[key]['indices']
    _df = results_dfs[key]
    if 'TIMESLICE' in indices:
        unwanted_members = {'YEAR', 'VALUE'}
        _indices = [ele for ele in indices if ele not in unwanted_members]
        df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE',aggfunc=np.sum)
        df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
        _result_tables[key] = df
    elif 'TIMESLICE' not in indices:
        if contents_var[key]['type'] == 'result':
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE')
            df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
            _result_tables[key] = df
        elif contents_var[key]['type'] == 'param':
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE')
            df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
            _result_tables[key] = df
        elif contents_var[key]['type'] == 'equ':
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE')
            #df = df.loc[(df != 0).any(axis=1)] # remove rows if all are zero
            _result_tables[key] = df
    _result_tables[key]=_result_tables[key].fillna(0)
results_tables = {k: v for k, v in _result_tables.items() if not v.empty}
#%%
# We take the dataframe of results and save to an Excel file
print("Creating the Excel file of results. Results saved in the results folder.")
scenario = scenario.lower()
#if results tables not empty then save to excel
if results_tables:
    with pd.ExcelWriter(f'{results_directory}/{economy}_results_{scenario}_{model_start}.xlsx') as writer:
        for k, v in results_tables.items():
            v.to_excel(writer, sheet_name=k, merge_cells=False)

print("Time taken: {} for creating the Excel file of results.".format(time.time()-start))

################################################################################
#SAVE RESULTS AS LONG CSV HERE
################################################################################

#%%
#iterate through sheets in tmp
for file in os.listdir(tmp_directory):
    #if file is not a csv or is in this list then skip it
    ignored_files = ['SelectedResults.csv']
    if file.split('.')[-1] != 'csv' or file in ignored_files:
        continue
    #load in sheet
    sheet_data = pd.read_csv(tmp_directory+'/'+file)

    #The trade file will have two Region columns. Set the second one to be 'REGION_TRADE'
    if file == 'Trade.csv':
        sheet_data.rename(columns={'REGION.1':'REGION_TRADE'}, inplace=True)

    #add file name as a column (split out .csv)
    sheet_data['SHEET_NAME'] = file.split('\\')[-1].split('.')[0]
    #if this is the first sheet then create a dataframe to hold the data
    if file == os.listdir(tmp_directory)[0]:
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

#save combined data to csv
new_combined_data.to_csv(f'{results_directory}/tall_{economy}_results_{scenario}_{model_start}.csv', index=False)

print("Time taken: {} for creating the tall csv file of results.".format(time.time()-start))
#%%

################################################################################
#create visualisations:
################################################################################
# path_to_results_config
path_to_data_config = f'{root_dir}/config/{data_config_file}'
path_to_visualisation = f'{results_directory}/energy_system_visualisation_{scenario}_{economy}.png'
create_res_visualisation(path_to_data_sheet, path_to_visualisation,path_to_data_config)

#%%