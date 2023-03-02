# this script takes in the power data sheet and runs the osemosys model
# configure the model run in the START tab of the excel file
# run this file from the command line

# the following python packages are imported:
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
from tests import compare_combined_data_to_data_config
# the processing script starts from here
# get the time you started the model so the results will have the time in the filename
model_start = time.strftime("%Y-%m-%d-%H%M%S")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
print("Script started at {}...\n".format(model_start))
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
data_config_file = "data_config copy.yml"
results_config_file = "results_config_copy_test.yml"
#%%

################################################################################
#PREPARE DATA
################################################################################
#start timer
start = time.time()

df_prefs = pd.read_excel('{}/data/{}'.format(root_dir, input_data_sheet_file), sheet_name='START',usecols="A:B",nrows=3,header=None)

economy = df_prefs.loc[0][1]
scenario = df_prefs.loc[1][1]
years = df_prefs.loc[2][1]

config_dict = {}
config_dict['economy'] = economy
config_dict['years'] = years
config_dict['scenario'] = scenario

# get the names of parameters to read in the next step
with open('{}/src/{}'.format(root_dir, data_config_file)) as f:
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
input_data_raw = pd.read_excel("{}/data/{}".format(root_dir,input_data_sheet_file),sheet_name=None) # creates dict of dataframes
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
tmp_directory = '{}/tmp/{}'.format(root_dir,economy)
try:
    os.mkdir('{}'.format(tmp_directory))
except OSError:
    pass

with pd.ExcelWriter('{}/combined_data_{}.xlsx'.format(tmp_directory,economy)) as writer:
    for k, v in filtered_data.items():
        v.to_excel(writer, sheet_name=k, index=False, merge_cells=False)
print("Combined file of Excel input data has been written to the tmp folder.\n")

# The data needs to be converted from the Excel format to the text file format. We use otoole for this task.
subset_of_years = config_dict['years']

print("Time taken: {}".format(time.time()-start))
#%%
_path='{}/combined_data_{}.xlsx'.format(tmp_directory,economy)
#run testing function to check for issues with the data
compare_combined_data_to_data_config(data_config_short_names,filtered_data)

#%%
# prepare data using otoole
_path='{}/combined_data_{}.xlsx'.format(tmp_directory,economy)
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
output_file = '{}/datafile_from_python_{}.txt'.format(tmp_directory,economy)
writer.write(filtered_data2, output_file, default_values)

print("data file in text format has been written and saved in the tmp folder.\n")
print("Time taken: {}".format(time.time()-start))
#%%
################################################################################
#SOLVE MODEL
################################################################################

# We first make a copy of osemosys_fast.txt so that we can modify where the results are written.
# Results from OSeMOSYS come in csv files. We first save these to the tmp directory for each economy.
# making a copy of the model file in the tmp directory so it can be modified
with open('{}/osemosys_fast.txt'.format(root_dir)) as t:
    model_text = t.read()
f = open('{}/model_{}.txt'.format(tmp_directory,economy),'w')
f.write('%s\n'% model_text)
f.close()
# Read in the file
with open('{}/model_{}.txt'.format(tmp_directory,economy), 'r') as file :
  filedata = file.read()
# Replace the target string
filedata = filedata.replace("param ResultsPath, symbolic default 'results';","param ResultsPath, symbolic default '{}';".format(tmp_directory))
# Write the file out again
with open('{}/model_{}.txt'.format(tmp_directory,economy), 'w') as file:
  file.write(filedata)
  
print("Time taken: {}".format(time.time()-start))
#%%
#previous method:
use_glpsol = False
if use_glpsol:
    result = subprocess.run("glpsol -d {}/datafile_from_python_{}.txt -m {}/model_{}.txt".format(tmp_directory,economy,tmp_directory,economy),shell=True, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)

#new method:
#create a lp file to input into cbc
result = subprocess.run("glpsol -d {}/datafile_from_python_{}.txt -m {}/model_{}.txt --wlp {}/cbc_input_{}.lp".format(tmp_directory,economy,tmp_directory,economy,tmp_directory,economy),shell=True, capture_output=True, text=True)
print("\n Printing command line output from converting to lp file \n")
print(result.stdout)
print(result.stderr)

#input into cbc solver:
result = subprocess.run("cbc {}/cbc_input_{}.lp solve solu {}/cbc_results_{}.txt".format(tmp_directory,economy,tmp_directory,economy),shell=True, capture_output=True, text=True)
print("\n Printing command line output from CBC solver \n")
print(result.stdout)
print(result.stderr)

#convert to csv
result = subprocess.run("otoole results cbc csv {}/cbc_results_{}.txt {}/results_cbc_{}.txt {}/src/{}".format(tmp_directory,economy,tmp_directory,economy,root_dir, results_config_file),shell=True, capture_output=True, text=True)
print("\n Printing command line output from converting cbc output to csv \n")
print(result.stdout)
print(result.stderr)
print('Time taken: {}'.format(time.time()-start))
#  otoole results [-h] [--input_datafile INPUT_DATAFILE] [--input_datapackage INPUT_DATAPACKAGE] [--write_defaults] {cbc,cplex,gurobi} {csv} from_path to_path config

#%%
################################################################################
#Save results as Excel workbook
################################################################################

# Now we take the CSV files and combine them into an Excel file
# First we need to make a dataframe from the CSV files
# Note: if you add any new result parameters to osemosys_fast.txt, you need to update results_config.yml
parent_directory = "{}/results/".format(root_dir)
child_directory = economy
path = os.path.join(parent_directory,child_directory)
try:
    os.mkdir(path)
except OSError:
    #print ("Creation of the directory %s failed" % path)
    pass
with open('{}/src/{}'.format(root_dir,results_config_file)) as f:
    contents_var = yaml.safe_load(f)
results_df={}
for key,value in contents_var.items():
    if contents_var[key]['type'] == 'result':
        fpath = '{}/'.format(tmp_directory)+key+'.csv'
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
if bool(results_tables):
    with pd.ExcelWriter('{}/results/{}/{}_results_{}_{}.xlsx'.format(root_dir,economy,economy,scenario,model_start)) as writer:
        for k, v in results_tables.items():
            v.to_excel(writer, sheet_name=k, merge_cells=False)


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
new_combined_data.to_csv(path + '/tall_{}_results_{}_{}.csv'.format(economy,scenario,model_start), index=False)
#%%

