# making changes to the graphing.
import pandas as pd
import numpy as np
import yaml
import os
import subprocess
import zipfile
import sys
import warnings
import logging
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
from collections import OrderedDict
logger = logging.getLogger(__name__)
#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")


#load in technology, emissions and colors mappings from excel file, using the sheet name as the key
mapping = pd.read_excel('config/plotting_config_and_timeslices.xlsx', sheet_name=None)
powerplant_mapping = mapping['POWERPLANT'].set_index('long_name').to_dict()['plotting_name']
fuel_mapping = mapping['FUEL'].set_index('long_name').to_dict()['plotting_name']
emissions_mapping = mapping['EMISSION'].set_index('long_name').to_dict()['plotting_name']
technology_color_dict = mapping['plotting_name_to_color'].set_index('plotting_name').to_dict()['color']
timeslice_dict = OrderedDict(mapping['timeslices'].set_index('timeslice').to_dict(orient='index'))

def plotting_handler(tall_results_dfs=None,paths_dict=None, config_dict=None,load_from_pickle=True,pickle_paths=None):
    """Handler for plotting functions, pickle path is a list of two paths, the first is the path to the pickle of tall_results_dfs, the second is the path to the pickle of paths_dict. You will need to set them manually."""
    if load_from_pickle:
        if pickle_paths is None:
            tall_results_dfs = pd.read_pickle(paths_dict['tall_results_dfs_pickle'])
        else:
            #load from pickle
            tall_results_dfs = pd.read_pickle(pickle_paths[0])
            paths_dict = pd.read_pickle(pickle_paths[1])
            config_dict = pd.read_pickle(pickle_paths[2])

    fig_generation, fig_generation_title = plot_generation_annual(tall_results_dfs, paths_dict)

    fig_emissions, fig_emissions_title = plot_emissions_annual(tall_results_dfs, paths_dict)

    fig_capacity, fig_capacity_title = plot_capacity_annual(tall_results_dfs, paths_dict)

    fig_capacity_factor,fig_capacity_factor_title = plot_capacity_factor_annual(tall_results_dfs, paths_dict)

    figs_list_average_generation_by_timeslice,figs_list_average_generation_by_timeslice_title = plot_average_generation_by_timeslice(tall_results_dfs, paths_dict)
    
    fig_8th_graph_generation, fig_8th_graph_generation_title = plot_8th_graphs(paths_dict,config_dict)

    #put all figs in a list
    figs = [fig_8th_graph_generation,fig_generation, fig_emissions, fig_capacity]#+ figs_list_average_generation_by_timeslice #found timeselices to be too complicated to plot in dashboard so left them out
    # fig_capacity_factor,#we wont plot capacity factor in dashboard
    subplot_titles = [fig_8th_graph_generation_title,fig_generation_title, fig_emissions_title, fig_capacity_title] #+ figs_list_average_generation_by_timeslice_title

    put_all_graphs_in_one_html(figs, paths_dict)
    create_dashboard(figs, paths_dict,subplot_titles)


def extract_storage_charge_and_discharge(tall_results_dfs):
    """Extract storage charge and discharge from ProductionByTechnology sheet. Note that the final data will not have been summed up by technology, timeslice or year yet."""
    try:
        storage_discharge = tall_results_dfs['ProductionByTechnology']
    except KeyError:
        storage_discharge = tall_results_dfs['ProductionByTechnolo']
    storage_charge = tall_results_dfs['UseByTechnology']
    #filter for POW_TBATT in TECHNOLOGY
    storage_charge = storage_charge[storage_charge['TECHNOLOGY'] == 'POW_TBATT']
    storage_discharge = storage_discharge[storage_discharge['TECHNOLOGY'] == 'POW_TBATT']

    #if they are empty raise a warning
    if storage_charge.empty:
        warnings.warn('Storage charge is empty')
    if storage_discharge.empty:
        warnings.warn('Storage discharge is empty')
        
    #rename TECHNOLOGY according to if its charge or discharge
    storage_charge['TECHNOLOGY'] = 'Storage_charge'
    storage_discharge['TECHNOLOGY'] = 'Storage_discharge'

    #make value for charge negative
    storage_charge['VALUE'] = -storage_charge['VALUE']
    return storage_charge,storage_discharge
    
def extract_ProductionByTechnology(tall_results_dfs):
    """Extract generation (and other) data from ProductionByTechnology sheet. But also extract storage charge and discharge and handle it separately then append them generation. Also convert to GWh. Note that the final data will not have been summed up by technology, timeslice or year yet."""
    generation = tall_results_dfs['ProductionByTechnology']
    
    generation = drop_categories_not_in_mapping(generation, powerplant_mapping)
    #map TECHNOLOGY to readable names:
    generation['TECHNOLOGY'] = generation['TECHNOLOGY'].apply(lambda x: extract_readable_name_from_mapping(x, powerplant_mapping))

    #drop storage as it is handled separately
    generation = generation[generation['TECHNOLOGY'] != 'POW_TBATT']
    storage_charge,storage_discharge = extract_storage_charge_and_discharge(tall_results_dfs)
    #append storage charge and discharge to generation
    generation = pd.concat([generation,storage_charge,storage_discharge])
    #convert to GWh by /3.6
    generation['VALUE'] = generation['VALUE']/3.6
    return generation

def plot_generation_annual(tall_results_dfs, paths_dict):
    """Using data from ProductionByTechnology sheet , plot generation by technology. Also plot total demand as a line on the same graph"""
    generation = extract_ProductionByTechnology(tall_results_dfs)
    #sum generation by technology and year
    generation = generation.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()

    #drop Storage_charge and Storage_discharge as they are not forms of generation
    generation = generation[generation['TECHNOLOGY'] != 'Storage_charge']
    generation = generation[generation['TECHNOLOGY'] != 'Storage_discharge']
    generation = generation[generation['TECHNOLOGY'] != 'Transmission']
    generation = generation[generation['TECHNOLOGY'] != 'Storage']

    demand = tall_results_dfs['Demand']
    #sum demand by year
    demand = demand.groupby(['YEAR']).sum().reset_index()
    #convert to GWh by /3.6
    demand['VALUE'] = demand['VALUE']/3.6
    #create a column called TECHNOLOGY with value 'Demand'
    demand['TECHNOLOGY'] = 'Demand'
    
    #order by value
    generation = generation.sort_values(by=['YEAR','VALUE'],ascending=False)
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the YEAR
    title = 'Generation by technology GWh'
    fig = px.area(generation, x="YEAR", y="VALUE", color='TECHNOLOGY',title=title,color_discrete_map=create_color_dict(generation['TECHNOLOGY']))
    #and add line with points for demand
    fig.add_scatter(x=demand['YEAR'], y=demand['VALUE'], mode='lines+markers', name='Demand', line=dict(color=technology_color_dict['Demand']), marker=dict(color=technology_color_dict['Demand']))
    
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_generation.html', auto_open=False)

    return fig,title

def plot_emissions_annual(tall_results_dfs, paths_dict):
    """Plot emissions by year by technology"""
    #load emissions
    emissions = tall_results_dfs['AnnualTechnologyEmission']
    
    #drop technologies not in powerplant_mapping
    emissions = drop_categories_not_in_mapping(emissions, emissions_mapping, column='EMISSION')
    #map EMISSION to readable names:
    emissions['FUEL'] = emissions['EMISSION'].apply(lambda x: extract_readable_name_from_mapping(x, emissions_mapping))

    # sum emissions by technology and year
    emissions = emissions.groupby(['FUEL','YEAR']).sum().reset_index()
    #order the FUEL by value
    emissions = emissions.sort_values(by=['YEAR','VALUE'], ascending=False)
    
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time
    title = 'Emissions by fuel MTC02'
    fig = px.area(emissions, x="YEAR", y="VALUE", color='FUEL', title=title,color_discrete_map=create_color_dict(emissions['FUEL']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_emissions.html', auto_open=False)

    return fig,title

def plot_capacity_annual(tall_results_dfs, paths_dict):
    """Plot capacity by technology"""
    #load capacity
    capacity = tall_results_dfs['TotalCapacityAnnual']#'CapacityByTechnology']#couldnt find CapacityByTechnology in the results but TotalCapacityAnnual is there and it seemed to be the same

    #drop technologies not in powerplant_mapping
    capacity = drop_categories_not_in_mapping(capacity, powerplant_mapping)
    #map TECHNOLOGY to readable names:
    capacity['TECHNOLOGY'] = capacity['TECHNOLOGY'].apply(lambda x: extract_readable_name_from_mapping(x, powerplant_mapping))
    # #convert imports to GW
    # capacity.loc[capacity['TECHNOLOGY'] == 'Imports', 'VALUE'] = capacity.loc[capacity['TECHNOLOGY'] == 'Imports', 'VALUE']/3.6
    
    #remove transmission from technology
    capacity = capacity.loc[capacity['TECHNOLOGY'] != 'Transmission']

    #sum capacity by technology and year
    capacity = capacity.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time

    #order the technologies by capacity
    capacity = capacity.sort_values(by=['YEAR','VALUE'], ascending=False)
    title = 'Capacity by technology GW'
    fig = px.area(capacity, x="YEAR", y="VALUE", color='TECHNOLOGY', title=title,color_discrete_map=create_color_dict(capacity['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_capacity.html', auto_open=False)

    return fig,title

def plot_capacity_factor_annual(tall_results_dfs, paths_dict):
    
    generation = extract_ProductionByTechnology(tall_results_dfs)

    #extract capcity data
    capacity = tall_results_dfs['TotalCapacityAnnual']#'CapacityByTechnology']
    
    
    capacity = drop_categories_not_in_mapping(capacity, powerplant_mapping)
    #couldnt find CapacityByTechnology in the results but TotalCapacityAnnual is there and it seemed to be the same
    capacity['TECHNOLOGY'] = capacity['TECHNOLOGY'].apply(lambda x: extract_readable_name_from_mapping(x, powerplant_mapping))

    #sum generation and capacity by technology and year
    capacity = capacity.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    generation = generation.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()

    #join both dataframes on technology and year
    generation_capacity = generation.merge(capacity, on=['TECHNOLOGY','YEAR'], suffixes=('_gen_gwh','_cap_gw'))

    #calculate capacity factor as generation/capacity/8760 > since gen is in GWh and cap in GW, divide by 8760 hours to get 1 (or less than 1)
    generation_capacity['VALUE'] = (generation_capacity['VALUE_gen_gwh']/generation_capacity['VALUE_cap_gw'])/87.60#im not sure why but it seems 87.6 is the best number to put here?

    #order the technologies by capacity
    generation_capacity = generation_capacity.sort_values(by=['YEAR','VALUE'], ascending=False)

    #plot a historgram chart with color and facets determined by the TECHNOLOGY column. The chart will have the time on x axis and the value on y. Make faint lines between the bars so it is clear which year it is
    title = 'Capacity Factor (%)'
    fig = px.histogram(generation_capacity, x="YEAR", y='VALUE',color='TECHNOLOGY', facet_col='TECHNOLOGY', title=title,facet_col_wrap=7,color_discrete_map=create_color_dict(generation_capacity['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_capacity_factor.html', auto_open=False)
    return fig,title

def plot_average_generation_by_timeslice(tall_results_dfs, paths_dict):
    """Calculate average generation by timeslice for each technology and year. Also calculate average generation by technology and year for power plants, to Storage, from Storage and  demand"""
    generation = extract_ProductionByTechnology(tall_results_dfs)
    #sum generation by technology, timeslice and year
    generation = generation.groupby(['TECHNOLOGY','YEAR','TIMESLICE']).sum().reset_index()

    demand = tall_results_dfs['Demand']
    #sum demand by year, timeslice
    demand = demand.groupby(['YEAR','TIMESLICE']).sum().reset_index()#todo havent checked that demand by timeselice ends up alright
    #convert to GWh by /3.6
    demand['VALUE'] = demand['VALUE']/3.6
    #create a column called TECHNOLOGY with value 'Demand'
    demand['TECHNOLOGY'] = 'Demand'

    #concat generation and demand
    generation = pd.concat([generation,demand])  

    double_check_timeslice_details(timeslice_dict)
    #extract details about timeslice and put them into a column called TOTAL_HOURS
    generation['TOTAL_HOURS'] = generation['TIMESLICE'].apply(lambda x: timeslice_dict[x]['hours'])
    #calculate average generation by dividing by total hours times 1000
    generation['VALUE'] = generation['VALUE']/generation['TOTAL_HOURS'] * 1000
    generation = generation[generation['TECHNOLOGY'] != 'Transmission']

    #get total capacity by technology and year
    capacity = tall_results_dfs['TotalCapacityAnnual']#'CapacityByTechnology']
    
    
    capacity = drop_categories_not_in_mapping(capacity, powerplant_mapping)
    #couldnt find CapacityByTechnology in the results but TotalCapacityAnnual is there and it seemed to be the same
    capacity['TECHNOLOGY'] = capacity['TECHNOLOGY'].apply(lambda x: extract_readable_name_from_mapping(x, powerplant_mapping))

    capacity = capacity.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    
    capacity = capacity[capacity['TECHNOLOGY'] != 'Transmission']
    #make a TIMESLICE col and call it 'CAPACITY'
    capacity['TIMESLICE'] = 'CAPACITY'

    #sort the timeslice and technology columns
    generation = generation.sort_values(by=['TIMESLICE','TECHNOLOGY'])
    capacity = capacity.sort_values(by=['TIMESLICE','TECHNOLOGY'])
    #add capacity to the bottom of generation
    generation = pd.concat([generation,capacity])
    #set Storage to 0 in generation (normally would drop but it helps with the dashboard)
    generation.loc[generation['TECHNOLOGY'] == 'Storage','VALUE'] = 0

    #create a bar chart for a single year with the time slices on the x axis and the average generation on the y axis. We can plot the bar chart for every 10th year.
    #also filter out demand as we will plot that using scatter on the same graph
    max_year = generation['YEAR'].max()
    min_year = generation['YEAR'].min()

    #create a dictionary with the technology as key and the color as value using create_color_dict(technology_or_fuel_column) to get the colors
    color_dict = create_color_dict(generation['TECHNOLOGY'])
    #sort the df by TIMESLICE to have the same order as the the keys in timeslice_dict
    order = list(timeslice_dict.keys()) + ['CAPACITY']
    order_nocapacity = list(timeslice_dict.keys())
    subplot_years = [year for year in range(min_year,max_year+1,10)]
    for year in range(min_year,max_year+1,10):
        title = 'Average generation by timeslice for year '+str(year) + ' (GW)'
        df =  generation.copy()
        df = df[(df['YEAR'] == year) & (df['TECHNOLOGY'] != 'Demand')]

        fig = px.bar(df, x="TIMESLICE", y="VALUE", color='TECHNOLOGY', title=title,color_discrete_map=color_dict, barmode='stack', category_orders={"TIMESLICE": order})

        demand = generation.copy()
        demand = demand[(demand['TECHNOLOGY'] == 'Demand') & (demand['YEAR'] == year)]
        #one day it would be nice to learn to use plotly graph objects so we have more control over the layout and therforecan enforce order for this scatter and thefroe include lines. But for now we will just use add_scatter with markers only #sort demand timeslice col according to order_nocapacity # demand['TIMESLICE'] = pd.Categorical(demand['TIMESLICE'], categories=order_nocapacity, ordered=True)
        fig.add_scatter(x=demand['TIMESLICE'], y=demand['VALUE'], mode='markers', name='Demand', line=dict(color=color_dict['Demand']), marker=dict(color=color_dict['Demand']))#todo how to set orderof scatter.123

        #save as html
        fig.write_html(paths_dict['visualisation_directory']+'/generation_by_timeslice_'+str(year)+'.html')

    #MAKE THE DASHBOARD VERSION WHICH DOESNT CONTAIN THE CAPACITY TIMESLICE:
    #remove capacity timeslice
    generation = generation[generation['TIMESLICE'] != 'CAPACITY']
    figs_list = []
    title_list = []
    for year in range(min_year,max_year+1,10):
        title = 'Average generation by timeslice for year '+str(year) + ' (GW)'
        df =  generation.copy()
        df = df[(df['YEAR'] == year) & (df['TECHNOLOGY'] != 'Demand')]

        fig = px.bar(df, x="TIMESLICE", y="VALUE", color='TECHNOLOGY', title=title,color_discrete_map=color_dict, barmode='stack', category_orders={"TIMESLICE": order_nocapacity})

        demand = generation.copy()
        demand = demand[(demand['TECHNOLOGY'] == 'Demand') & (demand['YEAR'] == year)]

        fig.add_scatter(x=demand['TIMESLICE'], y=demand['VALUE'], mode='markers', name='Demand', line=dict(color=color_dict['Demand']), marker=dict(color=color_dict['Demand']))

        figs_list.append(fig)
        title_list.append(title)
    #DROP ALL EXCEPT FIRST AND LAST FORM THE LIST. THIS IS DONE BECAUSE WE CANT FIND OUT HOW TO FIX THE ORDER OF THE TIMESLICES FOR THE MID YEARS. wEIRD.
    figs_list = figs_list[0:1] + figs_list[-1:]
    title_list = title_list[0:1] + title_list[-1:]
    return figs_list,title_list


def plot_8th_graphs(paths_dict, config_dict):
    #load in data from data/8th_output.xlsx
    data_8th = {}
    with pd.ExcelFile('data/8th_output.xlsx') as xls:
        for sheet in xls.sheet_names:
            data_8th[sheet] = pd.read_excel(xls,sheet_name=sheet)
    
    expected_sheet_names = ['generation_by_tech']#,'Demand','emissions']

    #extract data based on the config file
    #NOTEHTAT THIS WILL USE THE SAME SETTINGS AS THE 9TH OUTPUT FOR ECONOMY AND SCENARIO. it might be useful later to have a different config file for the 8th output
    for sheet in expected_sheet_names:
        data_8th[sheet] = data_8th[sheet][data_8th[sheet]['REGION'] == config_dict['economy']]
        data_8th[sheet] = data_8th[sheet][data_8th[sheet]['SCENARIO'] == config_dict['scenario']]
        #now drop the columns we dont need
        data_8th[sheet] = data_8th[sheet].drop(columns=['REGION','SCENARIO'])

    #first print any differences betwen expected and actual
    if set(expected_sheet_names) != set(data_8th.keys()):
        logging.warning("The expected sheets in data/8th_output.xlsx are not the same as the actual sheets")
        logging.warning("Expected sheets: ", expected_sheet_names)
        logging.warning("Actual sheets: ", data_8th.keys())
    
    #NOW PLOT A DIFFERENT GRAPH FOR EACH SHEET WE EXPECT. YOU WILL AHVE TO CREATE A NEW FUNCTION FOR EACH GRAPH
    #plot generation by technology
    fig_generation,title_generation = plot_8th_generation_by_tech(data_8th,paths_dict)
    return fig_generation,title_generation

def plot_8th_generation_by_tech(data_8th,paths_dict):
    generation = data_8th['generation_by_tech']
    #drop total TECHNOLOGY
    generation = generation[generation['TECHNOLOGY'] != 'Total']
    #make the data into tall format
    generation = generation.melt(id_vars='TECHNOLOGY', var_name='YEAR', value_name='VALUE')
    
    #make year a int
    generation['YEAR'] = generation['YEAR'].astype(int)
    
    generation = generation.sort_values(by=['VALUE'], ascending=False)
    title = 'Generation GWh in 8th edition power model reference scenario'
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time
    fig = px.area(generation, x="YEAR", y="VALUE", color='TECHNOLOGY', title=title, color_discrete_map=create_color_dict(generation['TECHNOLOGY']))

    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/8th_generation_by_tech.html', auto_open=False)
    return fig,title

#########################DASHBOARD###############################

def put_all_graphs_in_one_html(figs, paths_dict):
    with open(paths_dict['visualisation_directory']+"/graph_aggregation.html", 'w') as dashboard:
        dashboard.write("<html><head></head><body>" + "\n")
        for fig in figs:
            inner_html = fig.to_html().split('<body>')[1].split('</body>')[0]
            dashboard.write(inner_html)
        dashboard.write("</body></html>" + "\n")

def create_dashboard(figs, paths_dict,subplot_titles):
    #create name of folder where you can find the dashboard
    base_folder = os.path.join('results', paths_dict['aggregated_results_and_inputs_folder_name'])
    #Note that we use the legend from the avg gen by timeslice graph because it contains all the categories used in the other graphs. If we showed the legend for other graphs we would get double ups 
    #find the length of figs and create a value for rows and cols that are as close to a square as possible
    rows = int(np.ceil(np.sqrt(len(figs))))
    cols = int(np.ceil(len(figs)/rows))

    fig = make_subplots(
        rows=rows, cols=cols,
        #specs types will all be xy
        specs=[[{"type": "xy"} for col in range(cols)] for row in range(rows)],
        subplot_titles=subplot_titles
    )
    
    #now add traces to the fig iteratively, using the row and col values to determine where to add the trace
    for i, fig_i in enumerate(figs):
        #get the row and col values
        row = int(i/cols)+1
        col = i%cols+1

        #add the traceas for entire fig_i to the fig. This is because we are suing plotly express which returns a fig with multiple traces, however, plotly subplots only accepts one trace per subplot
        for trace in fig_i['data']:
            fig.add_trace(trace, row=row, col=col) 

    #this is a great function to remove duplicate legend items
    names = set()
    fig.for_each_trace(
        lambda trace:
            trace.update(showlegend=False)
            if (trace.name in names) else names.add(trace.name))

    use_bar_charts = False
    if use_bar_charts:
        # if fig_i['layout']['barmode'] == 'stack':
        #make sure the barmode is stack for all graphs where it is in the layout
        #PLEASE NOTE THAT I COULDNT FIND A WAY TO SELECT TRACES THAT WERE APPLICABLE OTHER THAN FOR TYPE=BAR. (ROW AND COL ARENT IN THE TRACES). sO IF YOU NEED NON STACKED BARS IN THIS DASHBOARD YOU WILL HAVE TO CHANGE THIS SOMEHOW
        fig.update_traces(offset=0 ,selector = dict(type='bar'))#for some reasonteh legends for the bar charts are beoing wierd and all being the same color
        #showlegend=False

    #create title which is the folder where you can find the dashboard (base_folder)
    fig.update_layout(title_text=f"Dashboard for {base_folder}")
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/dashboard.html', auto_open=True)

#########################UTILITY FUNCTIONS#######################
def drop_categories_not_in_mapping(df, mapping, column='TECHNOLOGY'):
    #drop technologies not in powerplant_mapping
    df = df[df[column].isin(mapping.keys())]
    #if empty raise a warning
    if df.empty:
        warnings.warn(f'Filtering data in {column} caused the dataframe to become empty')
    return df

def extract_readable_name_from_mapping(long_name,mapping):
    """Use the mappings of what categories we expect in the power model and map them to readable names"""
    if long_name not in mapping.keys():
        logging.warning(f"Category {long_name} is not in the expected set of long_names in the mapping. This occured during extract_readable_name_from_mapping()")
        raise ValueError("long_name is not in the expected set of long_names")
        return long_name
    return mapping[long_name]
    
# def extract_readable_name_from_emissions_technology(technology):
#     """Use the set of fuels we expect in the power model, which have emission factors and map them to readable names"""
#     if technology not in emissions_mapping.keys():
#         logging.warning(f"Technology {technology} is not in the expected set of technologies during extract_readable_name_from_emissions_technology()")
#         raise ValueError("Technology is not in the expected set of technologies")
#         return technology
#     return emissions_mapping[technology]

def create_color_dict(technology_or_fuel_column):
    """Using the set of technologies, create a dictionary of colors for each. The colors for similar fuels and technologies should be similar. The color should also portray the vibe of the technology or fuel, for example coal should be dark and nuclear should be bright. Hydro should be blue, solar should be yellow, wind should be light blue? etc."""
    for technology_or_fuel in technology_or_fuel_column.unique():
        try:
            color = technology_color_dict[technology_or_fuel]
        except:
            logging.warning(f"Technology {technology_or_fuel} is not in the expected set of technologies during create_color_dict()")
            #raise ValueError("Technology is not in the expected set of technologies")
            #supply random color
            color = '#%06X' % random.randint(0, 0xFFFFFF)
        technology_color_dict[technology_or_fuel] = color
    return technology_color_dict


def double_check_timeslice_details(timeslice_dict):
    """timeslice_dict is a dictionary of the different details by timeslice. It was created using code by copy pasting the details from Alex's spreadhseet. The first entry is the key, the second is the proportion of the year that the timeslice makes up (all summing to 1), and the third is the number of hours in the timeslice (all summing to 8760)."""

    # #double check that the sum of the proportions is 1 or close to 1
    assert sum([x['proportion_of_total'] for x in timeslice_dict.values()]) > 0.999
    #double check that the sum of the hours is 8760
    assert sum([x['hours'] for x in timeslice_dict.values()]) == 8760
    

# ##########################################################################################
# #load the data
# pickle_paths = ['./results/2023-04-12-113500_19_THA_Reference_coin_mip/tmp/tall_results_dfs_19_THA_Reference_2023-04-12-113500.pickle','./results/2023-04-12-113500_19_THA_Reference_coin_mip/tmp/paths_dict_19_THA_Reference_2023-04-12-113500.pickle', './results/2023-04-12-113500_19_THA_Reference_coin_mip/tmp_config_dict_19_THA_Reference_2023-04-12-113500.pickle']
# plotting_handler(load_from_pickle=True, pickle_paths=pickle_paths)


