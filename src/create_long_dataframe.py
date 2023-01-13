#intention is to stack all the data in the sheets in one workbook into one dataframe.
#%%
#set working directory to root
import os

#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

import pandas as pd
#laod in workbook
#%%
#load in all csv files in tmp folder
import glob
import re
import datetime
folder = 'tmp/19_THA'

#%%
#iterate through sheets 
for file in os.listdir(folder):
    #if file is not a csv or this list then skip it
    ignored_files = ['SelectedResults.csv']
    if file.split('.')[-1] != 'csv' or file in ignored_files:
        continue
    #load in sheet
    sheet_data = pd.read_csv(folder+'/'+file)

    #The trade file will have two Region columns. Set the second one to be 'REGION_TRADE'
    if file == 'Trade.csv':
        sheet_data.rename(columns={'REGION.1':'REGION_TRADE'}, inplace=True)

    #add file name as a column (split out .csv)
    sheet_data['SHEET_NAME'] = file.split('\\')[-1].split('.')[0]
    #if this is the first sheet then create a dataframe to hold the data
    if file == os.listdir(folder)[0]:
        combined_data = sheet_data
    #if this is not the first sheet then append the data to the combined data
    else:
        combined_data = pd.concat([combined_data, sheet_data], ignore_index=True)

#%%
#remove any coluymns with all na's
combined_data = combined_data.dropna(axis=1, how='all')

#count number of na's in each column and then order the cols in a list by the number of na's. We'll use this to order the cols in the final dataframe
na_counts = combined_data.isna().sum().sort_values(ascending=True)
ordered_cols = list(na_counts.index)

#reorder the columns so the year cols are at the end, the ordered first cols are at start and the rest of the cols are in the middle
new_combined_data = combined_data[ordered_cols]

#%%

#now do a tree plot of the data to get an idea of how it is structured
try:
    import plotly.express as px
    columns_to_plot =['REGION','SHEET_NAME', 'TECHNOLOGY','FUEL']#ordered_first_cols
    #set any na's to 'NA'
    new_combined_data = new_combined_data.fillna('NA')
    #remove where Region is NA
    new_combined_data_vis = new_combined_data[new_combined_data['REGION'] != 'NA']
    fig = px.treemap(new_combined_data_vis, path=columns_to_plot)#, values='Value')
    #make it bigger
    fig.update_layout(width=1000, height=1000)
    #show it in browser rather than in the notebook
    fig.show()
    fig.write_html("./visualisations/all_data_tree{}.html".format(filename.split('.')[0]))

    #and make one that can fit on my home screen which will be 1.3 times taller and 3 times wider
    fig = px.treemap(new_combined_data_vis, path=columns_to_plot)
    #make it bigger
    fig.update_layout(width=2500, height=1300)
    #show it in browser rather than in the notebook
    fig.write_html("./visualisations/all_data_tree_big{}.html".format(filename.split('.')[0]))
except:
    print('plotly not installed, skipping plot')

#%%
#save combined data to csv
new_combined_data.to_csv(folder + '/ALL_OUTPUT_CSVS.csv', index=False)
#%%