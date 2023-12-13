#%%
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
import shutil
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

#ignore warning for The default value of numeric_only in DataFrameGroupBy.sum is deprecated. In a future version, numeric_only will default to False. Either specify numeric_only or select only columns which should be valid for the function.
warnings.filterwarnings("ignore", message="The default value of numeric_only in DataFrameGroupBy.sum is deprecated. In a future version, numeric_only will default to False. Either specify numeric_only or select only columns which should be valid for the function.")

#load in technology, emissions and colors mappings from excel file, using the sheet name as the key
mapping = pd.read_excel('config/plotting_config_and_timeslices.xlsx', sheet_name=None)
powerplant_mapping = mapping['POWERPLANT']
input_fuel_mapping = mapping['INPUT_FUEL']
fuel_mapping = mapping['FUEL']
technology_color_dict = mapping['plotting_name_to_color'].set_index('plotting_name').to_dict()['color']
timeslice_dict = OrderedDict(mapping['timeslices'].set_index('timeslice').to_dict(orient='index'))

CREATE_COSTS_DASHBOARD=False

def plotting_handler(tall_results_dfs=None,paths_dict={}, config_dict=None,load_from_pickle=True,pickle_paths=None):
    """Handler for plotting functions, pickle path is a list of two paths, the first is the path to the pickle of tall_results_dfs, the second is the path to the pickle of paths_dict. You will need to set them manually."""
    if load_from_pickle:
        if pickle_paths is None:
            tall_results_dfs = pd.read_pickle(paths_dict['tall_results_dfs_pickle'])
        else:
            #load from pickle
            tall_results_dfs = pd.read_pickle(pickle_paths[0])
            paths_dict = pd.read_pickle(pickle_paths[1])
            config_dict = pd.read_pickle(pickle_paths[2])

    #save mapping in 'config/plotting_config_and_timeslices.xlsx' to the paths_dict['visualisation_directory']
    shutil.copy('config/plotting_config_and_timeslices.xlsx', paths_dict['visualisation_directory'])

    #begin plotting:
    fig_gen,title_gen, fig_heat,title_heat, HEAT_DATA_AVAILABLE = plot_generation_and_heat_annual(tall_results_dfs, paths_dict)
    
    fig_use_fuel,title_use_fuel, fig_use_tech,title_use_tech = plot_input_use_by_fuel_and_technology(tall_results_dfs, paths_dict)
    
    fig_emissions, fig_emissions_title = plot_emissions_annual(tall_results_dfs, paths_dict)

    fig_capacity, fig_capacity_title = plot_capacity_annual(tall_results_dfs, paths_dict)

    fig_capacity_factor,fig_capacity_factor_title = plot_capacity_factor_annual(tall_results_dfs, paths_dict)

    figs_list_average_generation_by_timeslice,figs_list_average_generation_by_timeslice_title = plot_average_generation_by_timeslice(tall_results_dfs, paths_dict)
    
    fig_8th_graph_generation, fig_8th_graph_generation_title = plot_8th_graphs(paths_dict,config_dict)

    fig_cost_per_unit_production,title_cost_per_unit_production, fig_fixed_and_variable,title_fixed_and_variable = plot_cost_per_unit_production(tall_results_dfs, paths_dict, config_dict, CREATE_COSTS_DASHBOARD=CREATE_COSTS_DASHBOARD)
    #put all figs in a list
    figs = [fig_8th_graph_generation,fig_gen, fig_emissions, fig_capacity, fig_heat, fig_use_tech]#, fig_cost_per_unit_production, fig_fixed_and_variable]#, fig_use_fuel]#+ figs_list_average_generation_by_timeslice #found timeselices to be too complicated to plot in dashboard so left them out
    # fig_capacity_factor,#we wont plot capacity factor in dashboard
    subplot_titles = [fig_8th_graph_generation_title,title_gen, fig_emissions_title, fig_capacity_title, title_heat, title_use_tech]#, title_cost_per_unit_production, title_fixed_and_variable]#, title_use_fuel] #+ figs_list_average_generation_by_timeslice_title
    
    if not HEAT_DATA_AVAILABLE:
        figs.remove(fig_heat)
        subplot_titles.remove(title_heat)

    put_all_graphs_in_one_html(figs, paths_dict)
    create_dashboard(figs, paths_dict,subplot_titles, dashboard_title='all_graphs')
    

def format_costs(fixed_cost_df, variable_cost_df):     
    #sum costs by technology and year
    fixed_cost_df = fixed_cost_df.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    variable_cost_df = variable_cost_df.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    #drop unnecessary techs
    fixed_cost_df = fixed_cost_df[fixed_cost_df['TECHNOLOGY'].str.contains('Storage') == False]
    variable_cost_df = variable_cost_df[variable_cost_df['TECHNOLOGY'].str.contains('Storage') == False]
    
    #order by value
    fixed_cost_df = fixed_cost_df.sort_values(by=['YEAR','VALUE'],ascending=False)
    variable_cost_df = variable_cost_df.sort_values(by=['YEAR','VALUE'],ascending=False)
    return fixed_cost_df, variable_cost_df

def plot_cost_per_unit_production(tall_results_dfs, paths_dict, config_dict, CREATE_COSTS_DASHBOARD=True):

    generation, heat = extract_and_map_ProductionByTechnology(tall_results_dfs)
    fixed_cost_df, variable_cost_df = extract_and_map_Costs(tall_results_dfs, powerplant_mapping)
    generation, heat = format_generation_and_heat_df(generation, heat)
    fixed_cost_df, variable_cost_df = format_costs(fixed_cost_df, variable_cost_df)
    #concat then sum together heat and generation:
    output = pd.concat([generation,heat]).groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    
    # Join fixed, variable, and production dataframes on 'Technology','YEAR'
    total_cost_df = pd.merge(pd.merge(fixed_cost_df, variable_cost_df, on=['TECHNOLOGY','YEAR'], suffixes=('_fixed', '_variable')), output, on=['TECHNOLOGY','YEAR'])
    #reanme VALUE_variable and VALUE_fixed to Variable Cost and Fixed Cost
    total_cost_df = total_cost_df.rename(columns={'VALUE_variable':'Variable Cost','VALUE_fixed':'Fixed Cost'})
    total_cost_df['Total Variable Cost'] = total_cost_df['Fixed Cost'] + (total_cost_df['Variable Cost']*total_cost_df['VALUE'])
    total_cost_df['Total Cost'] = total_cost_df['Fixed Cost'] + total_cost_df['Total Variable Cost']
    # Use production data to calculate the cost per unit of production
    total_cost_df['Cost Per Unit Production'] = total_cost_df['Total Cost'] / total_cost_df['VALUE']

    # Create a graph with the total cost per unit of production as a line over time
    title_cost_per_unit_production = f"Total cost per unit of Production"
    fig_cost_per_unit_production = px.line(total_cost_df, x='YEAR', y='Cost Per Unit Production', title=title_cost_per_unit_production, color='TECHNOLOGY', color_discrete_map=create_color_dict(total_cost_df['TECHNOLOGY']))

    # Save as HTML
    fig_cost_per_unit_production.write_html(paths_dict['visualisation_directory'] + '/total_cost_per_unit_production.html', auto_open=False)
    
    #then create a graph with a line for variable cost and a line for fixed cost, with different colors foreach technology
    fixed_and_variable = total_cost_df[['YEAR','TECHNOLOGY','Fixed Cost','Variable Cost']].copy()
    fixed_and_variable = fixed_and_variable.melt(id_vars=['YEAR','TECHNOLOGY'], value_vars=['Fixed Cost','Variable Cost'], var_name='Cost Type', value_name='Cost')
    title_fixed_and_variable = f"Fixed and variable Cost"
    fig_fixed_and_variable = px.line(fixed_and_variable, x='YEAR', y='Cost', title=title_fixed_and_variable, color='TECHNOLOGY', line_dash='Cost Type', color_discrete_map=create_color_dict(fixed_and_variable['TECHNOLOGY']))
    
    # Save as HTML
    fig_fixed_and_variable.write_html(paths_dict['visualisation_directory'] + '/fixed_and_variable_cost.html', auto_open=False)
    
    # #now create a graph for each technology which will show the fixed and  variable costs over time. we will need to use two y axes for this as the values are very different
    # for technology in total_cost_df['TECHNOLOGY'].unique():
    #     technology_df = total_cost_df[total_cost_df['TECHNOLOGY'] == technology].copy()
    #     # technology_df = technology_df.melt(id_vars=['YEAR','TECHNOLOGY'], value_vars=['VALUE_fixed','VALUE_variable'], var_name='Cost Type', value_name='Cost')
    #     title = f"Fixed and Variable Cost for {technology}"
    #     fig =  make_subplots(specs=[[{"secondary_y": True}]])
    #     fig.add_trace(go.Scatter(x=technology_df['YEAR'], y=technology_df['VALUE_fixed'], name='Fixed Cost', line=dict(color='red')), secondary_y=False)
    #     fig.add_trace(go.Scatter(x=technology_df['YEAR'], y=technology_df['VALUE_variable'], name='Variable Cost', line=dict(color='blue')), secondary_y=True)
    #     fig.update_layout(title=title)
    #     fig.update_xaxes(title_text="Year")
    #     fig.update_yaxes(title_text="Fixed Cost", secondary_y=False)
    #     fig.update_yaxes(title_text="Variable Cost", secondary_y=True)
    #     fig.write_html(paths_dict['visualisation_directory'] + f'/fixed_and_variable_cost_{technology}.html', auto_open=False)
    if CREATE_COSTS_DASHBOARD:
        create_costs_by_tech_dashboard(fixed_cost_df, variable_cost_df, paths_dict, config_dict)
        
    return fig_cost_per_unit_production,title_cost_per_unit_production, fig_fixed_and_variable,title_fixed_and_variable


def create_costs_by_tech_dashboard(fixed_costs, variable_costs, paths_dict, subplot_titles):
    figs = []
    subplot_titles = []

    # Generate cost plots for each technology
    for technology in fixed_costs['TECHNOLOGY'].unique():
        technology_fixed = fixed_costs[fixed_costs['TECHNOLOGY'] == technology].copy()
        technology_variable = variable_costs[variable_costs['TECHNOLOGY'] == technology].copy()
        
        title = f"Fixed and Variable Cost for {technology}"
        subplot_titles.append(title)
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=technology_fixed['YEAR'], y=technology_fixed['VALUE'], name='Fixed Cost', line=dict(color='red')), secondary_y=False)
        fig.add_trace(go.Scatter(x=technology_variable['YEAR'], y=technology_variable['VALUE'], name='Variable Cost', line=dict(color='blue')), secondary_y=True)
        fig.update_layout(title=title)
        fig.update_xaxes(title_text="Year")
        fig.update_yaxes(title_text="Fixed Cost", secondary_y=False)
        fig.update_yaxes(title_text="Variable Cost", secondary_y=True)
        
        figs.append(fig)

    # Create the dashboard HTML
    create_dashboard(figs, paths_dict, subplot_titles, dashboard_title='costs_by_tech')

        
def extract_and_map_ProductionByTechnology(tall_results_dfs):
    """Extract generation (and other) data from ProductionByTechnology sheet. But also extract storage charge and discharge and handle it separately then append them generation. Also convert to TWh. Note that the final data will not have been summed up by technology, timeslice or year yet.
    """
    ###GENERATION and STORAGE DISCHARGE###
    production = tall_results_dfs['ProductionByTechnology'].copy()
        
    #merge with powerplant_mapping to get the readable name and drop any rows that have the column DROP. then identify any nissing technologies
    production = map_to_readable_names(production, powerplant_mapping, 'TECHNOLOGY', 'powerplant_mapping', 'extract_and_map_ProductionByTechnology', ignore_missing_mappings=False, print_warning_messages=False)
        
    # #map TECHNOLOGY to readable names:
    # production['TECHNOLOGY'] = production['TECHNOLOGY'].apply(lambda x: extract_readable_name_from_mapping(x, powerplant_mapping,'powerplant_mapping', 'extract_and_map_ProductionByTechnology'))
    
    heat = production[production['FUEL'].str.contains('heat') == True]
    generation = production[production['FUEL'].str.contains('heat') == False]

    ###STORAGE CHARGE###
    storage_charge = tall_results_dfs['UseByTechnology'].copy()
        
    #merge with powerplant_mapping to get the readable name and drop any rows that have the column DROP. then identify any nissing technologies
    storage_charge = map_to_readable_names(storage_charge, powerplant_mapping, 'TECHNOLOGY', 'powerplant_mapping', 'extract_and_map_ProductionByTechnology', ignore_missing_mappings=False, print_warning_messages=False)
        
    storage_charge = storage_charge[storage_charge['TECHNOLOGY'].str.contains('Storage') == True]
    
    #filter for only techs with storage in name in storage_charge (nothing needs to be done for generation as that also contains storage)
    storage_charge_elec = storage_charge[storage_charge['FUEL'].str.contains('heat') == False] 
    storage_charge_heat  = storage_charge[storage_charge['FUEL'].str.contains('heat') == True]
    
    # #if they are empty raise a warning
    # if storage_charge_elec.empty:
    #     warnings.warn('Storage charge is empty')
    # if storage_charge_heat.empty:
    #     warnings.warn('Storage charge is empty')#potetnailly we dont have storage of heat
        
    #make negative
    storage_charge_elec['VALUE'] = -storage_charge_elec['VALUE']
    storage_charge_heat['VALUE'] = -storage_charge_heat['VALUE']

    #append storage charge and discharge to generation
    generation = pd.concat([generation,storage_charge_elec])
    heat = pd.concat([heat,storage_charge_heat])
    
    #convert generation to TWh by /3.6
    generation['VALUE'] = generation['VALUE']/3.6
    
    return generation, heat

def extract_and_map_Costs(tall_results_dfs, powerplant_mapping):
    """Extract costs from the AnnualFixedOperatingCost and AnnualVariableOperatingCost sheets.
       Also map TECHNOLOGY to readable names and handle potential issues like missing sheets or columns.
    """
    fixed_cost_df = tall_results_dfs['AnnualFixedOperatingCost'].copy()  
    variable_cost_df = tall_results_dfs['AnnualVariableOperatingCost'].copy()
    
    #merge 
    fixed_cost_df = map_to_readable_names(fixed_cost_df, powerplant_mapping, 'TECHNOLOGY', 'powerplant_mapping', 'extract_and_map_Costs', ignore_missing_mappings=False, print_warning_messages=False)
    
    variable_cost_df = map_to_readable_names(variable_cost_df, powerplant_mapping, 'TECHNOLOGY', 'powerplant_mapping', 'extract_and_map_Costs', ignore_missing_mappings=False, print_warning_messages=False)

    return fixed_cost_df, variable_cost_df


def extract_and_map_UseByTechnology(tall_results_dfs):
    """Extract generation (and other) data from UseByTechnology sheet. But also extract storage charge and discharge and handle it separately then append them generation. Also convert to TWh. Note that the final data will not have been summed up by technology, timeslice or year yet.
    
    """
    ###GENERATION and STORAGE DISCHARGE###
    input_use = tall_results_dfs['UseByTechnology'].copy()
        
    input_use = map_to_readable_names(input_use, powerplant_mapping, 'TECHNOLOGY', 'powerplant_mapping', 'extract_and_map_UseByTechnology', ignore_missing_mappings=False, print_warning_messages=False)
    input_use = map_to_readable_names(input_use, fuel_mapping, 'FUEL', 'fuel_mapping', 'extract_and_map_UseByTechnology', ignore_missing_mappings=False, print_warning_messages=False)
    
    # ###STORAGE CHARGE###
    # storage_charge = tall_results_dfs['UseByTechnology'].copy() #TODO IS STORAGE A THING FOR INPUT? also might it be dischagrge?
        
    # #filter for only techs with storage in name in storage_charge (nothing needs to be done for generation as that also contains storage)
    # storage_charge = storage_charge[storage_charge['TECHNOLOGY'].str.contains('Storage') == True]
    # #if they are empty raise a warning
    # if storage_charge.empty:
    #     warnings.warn('Storage charge is empty')
    # #make negative
    # storage_charge['VALUE'] = -storage_charge['VALUE']#TODO IS STORAGE A THING FOR INPUT? also might it be dischagrge?

    # #append storage charge and discharge to generation
    # input_use = pd.concat([input_use,storage_charge])
    
    # #convert to TWh by /3.6
    # input_use['VALUE'] = input_use['VALUE']/3.6#any need to convert elec to pj or anyhting?
    return input_use


def format_input_use(input_use):
    #sum input_use by technology and year
    input_use = input_use.groupby(['FUEL', 'TECHNOLOGY', 'YEAR']).sum().reset_index()

    #drop anything with storage in the name as they are not forms of input_use#TODO IS STORAGE A THING FOR INPUT? also might it be dischagrge?
    input_use = input_use[input_use['TECHNOLOGY'].str.contains('Storage') == False]
    input_use = input_use[input_use['TECHNOLOGY'] != 'Transmission']

    # demand = tall_results_dfs['Demand'].copy()#TODO
    # #sum demand by year
    # demand = demand.groupby(['YEAR']).sum().reset_index()
    # #convert to TWh by /3.6
    # demand['VALUE'] = demand['VALUE']/3.6
    # #create a column called TECHNOLOGY with value 'Demand'
    # demand['TECHNOLOGY'] = 'Demand'
    
    #order by value
    input_use = input_use.sort_values(by=['YEAR','VALUE'],ascending=False)
    
    #sum input_use by technology and year
    input_use_fuel = input_use.groupby(['FUEL','YEAR']).sum().reset_index()
    input_use_tech = input_use.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    return input_use_fuel, input_use_tech
    
def plot_input_use_by_fuel_and_technology(tall_results_dfs, paths_dict):
    """REGION	TIMESLICE	TECHNOLOGY	FUEL
    Plot the UseByTechnology sheet from output by the technology and fuel cols. will need to drop the timeselice col. Think it will be in pj.
    tall_results_dfs['UseByTechnology']
    """
    input_use = extract_and_map_UseByTechnology(tall_results_dfs)#TODO DO OMTHING WITH HEAT
    input_use_fuel, input_use_tech = format_input_use(input_use)
        
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the YEAR
    title_use_tech = 'Input use by technology PJ'
    fig_use_tech = px.area(input_use_tech, x="YEAR", y="VALUE", color='TECHNOLOGY',title=title_use_tech,color_discrete_map=create_color_dict(input_use['TECHNOLOGY']))
    #save as html
    fig_use_tech.write_html(paths_dict['visualisation_directory']+'/annual_use_by_tech.html', auto_open=False)
    
    title_use_fuel = 'Input use by fuel PJ'
    fig_use_fuel = px.area(input_use_fuel, x="YEAR", y="VALUE", color='FUEL',title=title_use_fuel,color_discrete_map=create_color_dict(input_use['FUEL']))
    #save as html
    fig_use_fuel.write_html(paths_dict['visualisation_directory']+'/annual_use_by_fuel.html', auto_open=False)

    return fig_use_fuel,title_use_fuel, fig_use_tech,title_use_tech

def format_generation_and_heat_df(generation, heat, keep_timeslice_col=False):
    if keep_timeslice_col:
        group_cols = ['TECHNOLOGY','TIMESLICE','YEAR']
        sort_cols = ['TIMESLICE','YEAR','VALUE']
    else:
        group_cols = ['TECHNOLOGY','YEAR']
        sort_cols = ['YEAR','VALUE']
    #sum generation by technology and year
    generation = generation.groupby(group_cols).sum().reset_index()
    heat = heat.groupby(group_cols).sum().reset_index()
    
    #drop anything with storage in the name as they are not forms of generation
    generation = generation[generation['TECHNOLOGY'].str.contains('Storage') == False]
    heat = heat[heat['TECHNOLOGY'].str.contains('Storage') == False]#dont know if this matters for heat tbh
    generation = generation[generation['TECHNOLOGY'] != 'Transmission']
    heat = heat[heat['TECHNOLOGY'] != 'Transmission']
    
    #order by value
    generation = generation.sort_values(by=sort_cols,ascending=False)
    heat = heat.sort_values(by=sort_cols,ascending=False)
    return generation, heat

def extract_and_format_elec_demand(tall_results_dfs,keep_timeslice_col=False):
    if keep_timeslice_col:
        group_cols = ['TIMESLICE','YEAR']
        sort_cols = ['TIMESLICE','YEAR','VALUE']
    else:
        group_cols = ['YEAR']
        sort_cols = ['YEAR','VALUE']
    elec_demand = tall_results_dfs['Demand'].loc[tall_results_dfs['Demand']['FUEL'].str.contains('heat') == False].copy()
    #sum elec_demand by year
    elec_demand = elec_demand.groupby(group_cols).sum().reset_index()
    #convert to TWh by /3.6
    elec_demand['VALUE'] = elec_demand['VALUE']/3.6
    #create a column called TECHNOLOGY with value 'Demand'
    elec_demand['TECHNOLOGY'] = 'Demand'
    #sort
    elec_demand = elec_demand.sort_values(by=sort_cols,ascending=False)
    return elec_demand

def plot_generation_and_heat_annual(tall_results_dfs, paths_dict):
    """Using data from ProductionByTechnology sheet , plot generation and heat by technology. Also plot total demand as a line on the same graph. gen and heart are done at same time because they come from same spreadsheet
    
    
    tall_results_dfs - tall_results_dfs contains all the data from the output files. It is a dictionary with the sheet name as the key and the dataframe as the value.
    paths_dict - paths_dict contains all the paths to the input and output files. It is a dictionary with the path name as the key and the path as the value.
    """
    generation, heat = extract_and_map_ProductionByTechnology(tall_results_dfs)
    elec_demand = extract_and_format_elec_demand(tall_results_dfs)
    generation, heat = format_generation_and_heat_df(generation, heat)
    #NB we found that we werent gettig any heat from the demand sheet so we dont need this. but leaving it here just in case
    # heat_demand = tall_results_dfs['Demand'].loc[tall_results_dfs['Demand']['FUEL'].str.contains('heat') == True].copy()
    # #sum heat_demand by year
    # heat_demand = heat_demand.groupby(['YEAR']).sum().reset_index()
    # #convert to TWh by /3.6
    # heat_demand['VALUE'] = heat_demand['VALUE']/3.6
    # #create a column called TECHNOLOGY with value 'Demand'
    # heat_demand['TECHNOLOGY'] = 'Demand'#
    

    #PLOT GENERATION
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the YEAR
    title_gen = 'Generation by technology TWh'
    fig_gen = px.area(generation, x="YEAR", y="VALUE", color='TECHNOLOGY',title=title_gen,color_discrete_map=create_color_dict(generation['TECHNOLOGY']))
    #and add line with points for elec_demand
    fig_gen.add_scatter(x=elec_demand['YEAR'], y=elec_demand['VALUE'], mode='lines+markers', name='Demand', line=dict(color=technology_color_dict['Demand']), marker=dict(color=technology_color_dict['Demand']))
    
    #save as html
    fig_gen.write_html(paths_dict['visualisation_directory']+'/annual_generation.html', auto_open=False)

    #PLOT HEAT
    title_heat = 'Heat by technology PJ'
    fig_heat = px.area(heat, x="YEAR", y="VALUE", color='TECHNOLOGY',title=title_heat,color_discrete_map=create_color_dict(heat['TECHNOLOGY']))
    
    #and add line with points for heat_demand
    # fig_heat.add_scatter(x=heat_demand['YEAR'], y=heat_demand['VALUE'], mode='lines+markers', name='Demand', line=dict(color=technology_color_dict['Demand']), marker=dict(color=technology_color_dict['Demand']))
    
    #save as html
    fig_heat.write_html(paths_dict['visualisation_directory']+'/annual_heat_production.html', auto_open=False)    
    
    if len(heat) == 0:
        HEAT_DATA_AVAILABLE = False
    else:
        HEAT_DATA_AVAILABLE = True
        
    return fig_gen,title_gen, fig_heat,title_heat, HEAT_DATA_AVAILABLE

def format_emissions_df(emissions):
    emissions = map_to_readable_names(emissions, input_fuel_mapping, 'TECHNOLOGY', 'input_fuel_mapping', 'format_emissions_df', ignore_missing_mappings=False, print_warning_messages=False)
    
    # sum emissions by technology and year
    emissions = emissions.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    #order the FUEL by value
    emissions = emissions.sort_values(by=['YEAR','VALUE'], ascending=False)
    return emissions

def plot_emissions_annual(tall_results_dfs, paths_dict):
    """Plot emissions by year by technology
    #note that we could change the nane in legend from technology to input fuel or something"""
    #load emissions
    emissions = tall_results_dfs['AnnualTechnologyEmission'].copy()
    emissions = format_emissions_df(emissions)
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time
    title = 'Emissions by technology MTC02'
    fig = px.area(emissions, x="YEAR", y="VALUE", color='TECHNOLOGY', title=title,color_discrete_map=create_color_dict(emissions['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_emissions.html', auto_open=False)

    return fig,title

def format_capacity(capacity):
    capacity = map_to_readable_names(capacity, powerplant_mapping, 'TECHNOLOGY', 'powerplant_mapping', 'format_capacity', ignore_missing_mappings=False, print_warning_messages=False)
    
    #remove transmission from technology
    capacity = capacity.loc[capacity['TECHNOLOGY'] != 'Transmission']

    #sum capacity by technology and year
    capacity = capacity.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time

    #order the technologies by capacity
    capacity = capacity.sort_values(by=['YEAR','VALUE'], ascending=False)
    return capacity

def plot_capacity_annual(tall_results_dfs, paths_dict):
    """Plot capacity by technology"""
    #load capacity
    capacity = tall_results_dfs['TotalCapacityAnnual'].copy()
    #'CapacityByTechnology']#couldnt find CapacityByTechnology in the results but TotalCapacityAnnual is there and it seemed to be the same
    capacity = format_capacity(capacity)
    title = 'Capacity by technology GW'
    fig = px.area(capacity, x="YEAR", y="VALUE", color='TECHNOLOGY', title=title,color_discrete_map=create_color_dict(capacity['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_capacity.html', auto_open=False)

    return fig,title

def plot_capacity_factor_annual(tall_results_dfs, paths_dict):
    """plots generation/capacity/8760/1000 > since gen is in TWh and cap in GW, divide by 8760 hours to get 1 (or less than 1)

    Args:
        tall_results_dfs (_type_): _description_
        paths_dict (_type_): _description_

    Returns:
        _type_: _description_
    """
    generation, heat = extract_and_map_ProductionByTechnology(tall_results_dfs)
    generation, heat = format_generation_and_heat_df(generation, heat)
    
    capacity = tall_results_dfs['TotalCapacityAnnual'].copy()
    capacity = format_capacity(capacity)

    #join both dataframes on technology and year
    generation_capacity = generation.merge(capacity, on=['TECHNOLOGY','YEAR'], suffixes=('_gen_TWh','_cap_gw'))

    #calculate capacity factor as generation/capacity/8760/1000 > since gen is in TWh and cap in GW, divide by 8760 hours to get 1 (or less than 1)
    generation_capacity['VALUE'] = (generation_capacity['VALUE_gen_TWh']/generation_capacity['VALUE_cap_gw'])/8.760

    #order the technologies by capacity
    generation_capacity = generation_capacity.sort_values(by=['YEAR','VALUE'], ascending=False)

    #plot a historgram chart with color and facets determined by the TECHNOLOGY column. The chart will have the time on x axis and the value on y. Make faint lines between the bars so it is clear which year it is
    title = 'Capacity Factor (%)'
    fig = px.bar(generation_capacity, x="YEAR", y='VALUE',color='TECHNOLOGY', facet_col='TECHNOLOGY', title=title,facet_col_wrap=7,color_discrete_map=create_color_dict(generation_capacity['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_capacity_factor.html', auto_open=False)
    return fig,title

def plot_average_generation_by_timeslice(tall_results_dfs, paths_dict):
    """Calculate average generation by timeslice for each technology and year. Also calculate average generation by technology and year for power plants, to Storage, from Storage and  demand"""
    ###GENERATION###
    generation, heat = extract_and_map_ProductionByTechnology(tall_results_dfs)
    elec_demand = extract_and_format_elec_demand(tall_results_dfs, keep_timeslice_col=True)
    generation, heat = format_generation_and_heat_df(generation, heat, keep_timeslice_col=True)
    capacity = format_capacity(tall_results_dfs['TotalCapacityAnnual'].copy())
    #concat generation and demand
    generation = pd.concat([generation,elec_demand])  
    # heat = pd.concat([heat,heat_demand])

    double_check_timeslice_details(timeslice_dict)
    #extract details about timeslice and put them into a column called TOTAL_HOURS
    generation['TOTAL_HOURS'] = generation['TIMESLICE'].apply(lambda x: timeslice_dict[x]['hours'])
    #calculate average generation by dividing by total hours times 1000
    generation['VALUE'] = generation['VALUE']/generation['TOTAL_HOURS'] * 1000
    generation = generation[generation['TECHNOLOGY'] != 'Transmission']

    #make a TIMESLICE col and call it 'CAPACITY'
    capacity['TIMESLICE'] = 'CAPACITY'

    #sort the timeslice and technology columns
    generation = generation.sort_values(by=['TIMESLICE','TECHNOLOGY'])
    capacity = capacity.sort_values(by=['TIMESLICE','TECHNOLOGY'])
    #add capacity to the bottom of generation
    generation = pd.concat([generation,capacity])

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

        fig = px.bar(df, x="TIMESLICE", y="VALUE", color='TECHNOLOGY', title=title,color_discrete_map=color_dict, barmode='relative', category_orders={"TIMESLICE": order})

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

        fig = px.bar(df, x="TIMESLICE", y="VALUE", color='TECHNOLOGY', title=title,color_discrete_map=color_dict,  barmode='relative', category_orders={"TIMESLICE": order_nocapacity})

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
    scenario = config_dict['scenario']
   # if scenario == 'Target':
   #     # scenario='Carbon Neutral'
   #     scenario='Reference'#TODO CHANGE THIS BACK TO TARGET WHEN YOU HAVE THE DATA
    economy = config_dict['economy']
    
    for sheet in expected_sheet_names:
        data_8th[sheet] = data_8th[sheet][data_8th[sheet]['REGION'] == economy]
        data_8th[sheet] = data_8th[sheet][data_8th[sheet]['SCENARIO'] == scenario]
        #now drop the columns we dont need
        data_8th[sheet] = data_8th[sheet].drop(columns=['REGION','SCENARIO'])

    #first print any differences betwen expected and actual
    if set(expected_sheet_names) != set(data_8th.keys()):
        logging.warning("The expected sheets in data/8th_output.xlsx are not the same as the actual sheets")
        logging.warning("Expected sheets: ", expected_sheet_names)
        logging.warning("Actual sheets: ", data_8th.keys())
    
    #NOW PLOT A DIFFERENT GRAPH FOR EACH SHEET WE EXPECT. YOU WILL AHVE TO CREATE A NEW FUNCTION FOR EACH GRAPH
    #plot generation by technology
    fig_generation,title_generation = plot_8th_generation_by_tech(data_8th,paths_dict,economy,scenario)
    return fig_generation,title_generation

def plot_8th_generation_by_tech(data_8th,paths_dict,economy,scenario):
    generation = data_8th['generation_by_tech']
    #drop total TECHNOLOGY
    generation = generation[generation['TECHNOLOGY'] != 'Total']
    #make the data into tall format
    generation = generation.melt(id_vars='TECHNOLOGY', var_name='YEAR', value_name='VALUE')
    
    #make year a int
    generation['YEAR'] = generation['YEAR'].astype(int)
    
    generation = generation.sort_values(by=['VALUE'], ascending=False)
    title = f'Generation TWh in 8th edition power model {economy} {scenario}'
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

def create_dashboard(figs, paths_dict,subplot_titles, dashboard_title):
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
    fig.write_html(paths_dict['visualisation_directory']+f'/{dashboard_title}.html', auto_open=True)

#########################UTILITY FUNCTIONS#######################

def map_to_readable_names(df, mapping, left_join_col, mapping_name, function_name, ignore_missing_mappings=False, print_warning_messages=True):
    #merge with mapping to get the readable names and drop any rows that have the column DROP. then identify any nissing technologies using the join_cols and raise aerror if there are any
    df = df.merge(mapping, left_on=left_join_col, right_on='long_name', how='left', indicator=True)
    missing = df[df['_merge'] == 'left_only']
    # drop merge col
    df = df.drop(columns=['_merge'])
    if not missing.empty and not ignore_missing_mappings:
        if not print_warning_messages:
            raise ValueError(f'The following categories are not in the expected set of long_names in the mapping {mapping_name}. This occured during {function_name}: {missing[left_join_col].unique()}')
        else:
            logging.warning(f'The following categories are not in the expected set of long_names in the mapping {mapping_name}. This occured during {function_name}: {missing[left_join_col].unique()}')
            # print(f'The following categories are not in the expected set of long_names in the mapping {mapping_name}. This occured during {function_name}: {missing[left_join_col].unique()}')
    #drop any rows that have the column DROP
    df = df[df['DROP'] != True]
    #drop cosl
    df = df.drop(columns=[left_join_col, 'long_name','DROP'])
    #reaplce the plotting_name col with the left_join_col col name
    df.rename(columns={'plotting_name':left_join_col}, inplace=True)
    return df
    

def create_color_dict(technology_or_fuel_column):
    """Using the set of technologies, create a dictionary of colors for each. The colors for similar fuels and technologies should be similar. The color should also portray the vibe of the technology or fuel, for example coal should be dark and nuclear should be bright. Hydro should be blue, solar should be yellow, wind should be light blue? etc."""
    for technology_or_fuel in technology_or_fuel_column.unique():
        try:
            color = technology_color_dict[technology_or_fuel]
        except:
            logging.warning(f"{technology_or_fuel_column} {technology_or_fuel} is not in the expected set of technologies during create_color_dict()")
            #raise ValueError("Technology is not in the expected set of technologies")
            # print(f"Technology {technology_or_fuel} is not in the expected set of technologies during create_color_dict()")
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
    

#%%
# # ##########################################################################################
# # # #load the data
# pickle_paths = ['./results/10-31-1642_20_USA_Reference_coin_mip/tmp/tall_results_dfs_20_USA_Reference_10-31-1642.pickle','./results/10-31-1642_20_USA_Reference_coin_mip/tmp/paths_dict_20_USA_Reference_10-31-1642.pickle', './results/10-31-1642_20_USA_Reference_coin_mip/tmp/config_dict_20_USA_Reference_10-31-1642.pickle']
# plotting_handler(load_from_pickle=True, pickle_paths=pickle_paths)

# # # #%%
# # # # #load the data
# pickle_paths = ['./results/11-02-1120_19_THA_Target_coin_mip/tmp/tall_results_dfs_19_THA_Target_11-02-1120.pickle','./results/11-02-1120_19_THA_Target_coin_mip/tmp/paths_dict_19_THA_Target_11-02-1120.pickle', './results/11-02-1120_19_THA_Target_coin_mip/tmp/config_dict_19_THA_Target_11-02-1120.pickle']
# plotting_handler(load_from_pickle=True, pickle_paths=pickle_paths)

# plotting_functions.plotting_handler(tall_results_dfs=tall_results_dfs,paths_dict=paths_dict,config_dict=config_dict,load_from_pickle=True, pickle_paths=None)

# %%
