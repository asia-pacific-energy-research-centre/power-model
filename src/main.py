import pandas as pd
import numpy as np
import yaml
import os
from pathlib import Path
from otoole.read_strategies import ReadExcel
from otoole.write_strategies import WriteDatafile
#import click
import subprocess
import time
import importlib.resources as resources
#import glob
#import shutil

model_start = time.strftime("%Y-%m-%d-%H%M%S")

# model run inputs
economy = '01_AUS'
scenario = 'Reference'
years = 2030

config_dict = {}
config_dict['economy'] = economy
config_dict['years'] = years
config_dict['scenario'] = scenario

# load the data
with open('data_config.yml') as f:
    data_config = yaml.safe_load(f)

keep_dict={}
for key,value in data_config.items():
    new_dict = data_config[key]
    for k,v in new_dict.items():
        if k == 'short':
           _name = v
           keep_dict[key] = _name
keep_list = [x if y == 'None' else y for x,y in keep_dict.items()]

# load and filter

subset_of_economies = economy

_dict = pd.read_excel("../data/data-sheet-power.xlsx",sheet_name=None) # creates dict of dataframes
__dict = {k: _dict[k] for k in keep_list}
filtered_data = {}
list_of_dicts = []
for key,value in __dict.items():
    __df = __dict[key]
    if 'SCENARIO' in __df.columns:
        ___df = __df[__df['SCENARIO']==scenario].drop(['SCENARIO'],axis=1)
        ____df = ___df.loc[(___df != 0).any(1)] # remove rows if all are zero
        filtered_data[key] = ____df
    else:
        filtered_data[key] = __df
for key,value in filtered_data.items():
    __df = filtered_data[key]
    if 'REGION' in __df.columns:
        ___df = __df[__df['REGION']==subset_of_economies]
        ____df = ___df.loc[(___df != 0).any(1)] # remove rows if all are zero
        filtered_data[key] = ____df
    else:
        filtered_data[key] = __df
for key,value in filtered_data.items():
    __df = filtered_data[key]
    if key == 'REGION':
        ___df = __df[__df['VALUE']==subset_of_economies]
        ____df = ___df.loc[(___df != 0).any(1)] # remove rows if all are zero
        filtered_data[key] = ____df
    else:
        filtered_data[key] = __df
for key,value in filtered_data.items():
    __df = filtered_data[key]
    if 'UNITS' in __df.columns:
        ___df = __df.drop(['UNITS'],axis=1)
        ____df = ___df.loc[(___df != 0).any(1)] # remove rows if all are zero
        filtered_data[key] = ____df
for key,value in filtered_data.items():
    __df = filtered_data[key]
    if 'NOTES' in __df.columns:
        ___df = __df.drop(['NOTES'],axis=1)
        ____df = ___df.loc[(___df != 0).any(1)] # remove rows if all are zero
        filtered_data[key] = ____df
__dict = {k: filtered_data[k] for k in keep_list}
list_of_dicts.append(__dict)
#return list_of_dicts

# combine datasets

tmp_directory = '../tmp/{}'.format(economy)
try:
    os.mkdir('../tmp')
except OSError:
    #print ("Creation of the directory %s failed" % path)
    pass
try:
    os.mkdir('../tmp/{}'.format(economy))
except OSError:
    #print ("Creation of the directory failed")
    pass
combined_data = {}
a_dict = list_of_dicts[0]
for key in a_dict.keys():
    list_of_dfs = []
    for _dict in list_of_dicts:
        _df = _dict[key]
        list_of_dfs.append(_df)
    _dfs = pd.concat(list_of_dfs)
    _dfs = _dfs.drop_duplicates()
    combined_data[key] = _dfs


# write inputs

tmp_directory = '../tmp/{}'.format(economy)
with pd.ExcelWriter('./{}/combined_data_{}.xlsx'.format(tmp_directory,economy)) as writer:
    for k, v in combined_data.items():
        v.to_excel(writer, sheet_name=k, index=False, merge_cells=False)


# use otoole
tmp_directory = './tmp/{}'.format(economy)
subset_of_years = config_dict['years']
# prepare using otoole
_path='../{}/combined_data_{}.xlsx'.format(tmp_directory,economy)
reader = ReadExcel()
writer = WriteDatafile()
data, default_values = reader.read(_path)
# edit data (the dict of dataframes)

with open('data_config.yml') as f:
    contents = yaml.safe_load(f)

filtered_data2 = {}
for key,value in contents.items():
    _df = data[key]
    if contents[key]['type'] == 'param':
        if ('YEAR' in contents[key]['indices']):
            #print('parameters with YEAR are.. {}'.format(key))
            _df2 = _df.query('YEAR < @subset_of_years+1')
            filtered_data2[key] = _df2
        else:
            #print('parameters without YEAR are.. {}'.format(key))
            filtered_data2[key] = _df
    elif contents[key]['type'] == 'set':
        if key == 'YEAR':
            _df2 = _df.query('VALUE < @subset_of_years+1')
            filtered_data2[key] = _df2
        else:
            #print('sets are.. {}'.format(key))
            filtered_data2[key] = _df
    else:
        filtered_data2[key] = _df
output_file = '../{}/datafile_from_python_{}.txt'.format(tmp_directory,economy)
writer.write(filtered_data2, output_file, default_values)

# solve the model
#path = "./tmp/"
tmp_directory = 'tmp/{}'.format(economy)
# update OSeMOSYS model file with the tmp directory for results
try:
    os.mkdir(tmp_directory)
except OSError:
    #print ("Creation of the directory %s failed" % path)
    pass

# making a copy of the model file in the tmp directory so it can be modified
with open('../osemosys_fast.txt') as t:
    model_text = t.read()

f = open('../{}/model_{}.txt'.format(tmp_directory,economy),'w')
#f = f.replace("param ResultsPath, symbolic default 'tmp';","param ResultsPath, symbolic default '{}';".format(tmp_directory))
f.write('%s\n'% model_text)
f.close()

# Read in the file
with open('../{}/model_{}.txt'.format(tmp_directory,economy), 'r') as file :
  filedata = file.read()
# Replace the target string
filedata = filedata.replace("param ResultsPath, symbolic default 'results';","param ResultsPath, symbolic default '../{}';".format(tmp_directory))
# Write the file out again
with open('../{}/model_{}.txt'.format(tmp_directory,economy), 'w') as file:
  file.write(filedata)

#subprocess.run("glpsol -d {}/datafile_from_python_{}.txt -m {}/model_{}.txt".format(tmp_directory,economy,tmp_directory,economy),shell=True)

subprocess.run("glpsol -d ../tmp/01_AUS/datafile_from_python_01_AUS.txt -m ../tmp/01_AUS/model_01_AUS.txt",shell=True)

# process results
tmp_directory = 'tmp/{}'.format(economy)
parent_directory = "../results/"
child_directory = economy
path = os.path.join(parent_directory,child_directory)
try:
    os.mkdir(path)
except OSError:
    #print ("Creation of the directory %s failed" % path)
    pass
#with resources.open_text('aperc_osemosys','results_config.yml') as open_file:
#    contents_var = yaml.load(open_file, Loader=yaml.FullLoader)

with open('results_config.yml') as f:
    contents_var = yaml.safe_load(f)

results_df={}
for key,value in contents_var.items():
    if contents_var[key]['type'] == 'var':
        fpath = '../{}/'.format(tmp_directory)+key+'.csv'
        #print(fpath)
        _df = pd.read_csv(fpath).reset_index(drop=True)
        results_df[key] = _df
results_dfs = {}
results_dfs = {k:v for (k,v) in results_df.items() if not v.empty}
_result_tables = {}
for key,value in results_dfs.items():
    indices = contents_var[key]['indices']
    _df = results_dfs[key]
    if 'TIMESLICE' in indices:
        unwanted_members = {'YEAR', 'VALUE'}
        _indices = [ele for ele in indices if ele not in unwanted_members]
        df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE',aggfunc=np.sum)
        df = df.loc[(df != 0).any(1)] # remove rows if all are zero
        _result_tables[key] = df
    elif 'TIMESLICE' not in indices:
        if contents_var[key]['type'] == 'var':
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE')
            df = df.loc[(df != 0).any(1)] # remove rows if all are zero
            _result_tables[key] = df
        elif contents_var[key]['type'] == 'param':
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE')
            df = df.loc[(df != 0).any(1)] # remove rows if all are zero
            _result_tables[key] = df
        elif contents_var[key]['type'] == 'equ':
            unwanted_members = {'YEAR', 'VALUE'}
            _indices = [ele for ele in indices if ele not in unwanted_members]
            df = pd.pivot_table(_df,index=_indices,columns='YEAR',values='VALUE')
            #df = df.loc[(df != 0).any(1)] # remove rows if all are zero
            _result_tables[key] = df
    _result_tables[key]=_result_tables[key].fillna(0)
results_tables = {k: v for k, v in _result_tables.items() if not v.empty}

# write results
scenario = scenario.lower()
if bool(results_tables):
    with pd.ExcelWriter('../results/{}/{}_results_{}_{}.xlsx'.format(economy,economy,scenario,model_start)) as writer:
        for k, v in results_tables.items():
            v.to_excel(writer, sheet_name=k, merge_cells=False)