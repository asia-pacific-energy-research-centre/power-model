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
import random
logger = logging.getLogger(__name__)
#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

technology_mapping = {
    'POW_Coal_PP':'Coal',
    'POW_Gas_PP':'Gas',
    'POW_Gas_CCS_PP':'Gas',
    'POW_Oil_PP':'Oil',
    'POW_Hydro_PP':'Hydro',
    'POW_Wind_PP':'Wind',
    'POW_SolarPV_PP':'Solar',
    'POW_Other_PP':'Other',
    'POW_TBATT':'Storage',
    'POW_IMPORT_ELEC_PP':'Imports',
    'POW_Geothermal_PP':'Geothermal',
    'POW_Solid_Biomass_PP':'Biomass',
}
emissions_mapping = {
    '1_x_coal_thermal_CO2':'Coal',
    '1_5_lignite_CO2':'Coal',
    '2_coal_products_CO2':'Coal',
    '7_7_gas_diesel_oil_CO2':'Oil',
    '7_8_fuel_oil_CO2':'Oil',
    '8_1_natural_gas_CO2':'Gas',
    '8_1_natural_gas_CCS_CO2':'Gas',
    '15_solid_biomass_CO2':'Biomass',
    '16_others_CO2':'Other'
}
# #TEMP see model_preparation_functions.edit_input_data() for more info
# #change keys in emissions mappings so that if they start with a number they have a letter 'a' in front
# emissions_mapping = {('a'+key if key[0].isdigit() else key):value for key,value in emissions_mapping.items()}
# #TEMP
technology_color_dict = {
    'Coal': '#000000',
    'Gas': '#FF0000',
    'Oil' : '#FFA500',
    'Hydro': '#0000FF',
    'Wind': '#00FFFF',
    'Solar': '#FFFF00',
    'Other': '#808080',
    'Geothermal': '#FF00FF',
    'Biomass': '#008000',
    #set storagecharge and storagedischarge to the same bright color (pink!)
    'Storage_charge': '#FFC0CB',
    'Storage_discharge': '#FFC0CB',
    'Imports': '#00FF00',
    'Demand': '#000000'
}


def plotting_handler(tall_results_dfs=None,paths_dict=None, load_from_pickle=True,pickle_paths=None):
    """Handler for plotting functions, pickle path is a list of two paths, the first is the path to the pickle of tall_results_dfs, the second is the path to the pickle of paths_dict. You will need to set them manually."""
    if load_from_pickle:
        if pickle_paths is None:
            tall_results_dfs = pd.read_pickle(paths_dict['tall_results_dfs_pickle'])
        else:
            #load from pickle
            tall_results_dfs = pd.read_pickle(pickle_paths[0])
            paths_dict = pd.read_pickle(pickle_paths[1])

    plot_generation_annual(tall_results_dfs, paths_dict)
    plot_emissions_annual(tall_results_dfs, paths_dict)
    plot_capacity_annual(tall_results_dfs, paths_dict)
    plot_capacity_factor_annual(tall_results_dfs, paths_dict)
    plot_average_generation_by_timeslice(tall_results_dfs, paths_dict)
    plot_8th_graphs(paths_dict)


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

    return storage_charge,storage_discharge
    
def extract_generation_data(tall_results_dfs):
    """Extract generation data from ProductionByTechnology sheet. But also extract storage charge and discharge and handle it separately then append them generation. Also convert to GWh. Note that the final data will not have been summed up by technology, timeslice or year yet."""
    #note that we may find that 'ProductionByTechnology' has been shortened, so if its not there, check for ProductionByTechnolo
    try:
        generation = tall_results_dfs['ProductionByTechnology']
    except KeyError:
        generation = tall_results_dfs['ProductionByTechnolo']
    
    generation = drop_categories_not_in_mapping(generation, technology_mapping)
    #map TECHNOLOGY to readable names:
    generation['TECHNOLOGY'] = generation['TECHNOLOGY'].apply(extract_readable_name_from_powerplant_technology)

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
    generation = extract_generation_data(tall_results_dfs)
    #sum generation by technology and year
    generation = generation.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()

    demand = tall_results_dfs['Demand']
    #sum demand by year
    demand = demand.groupby(['YEAR']).sum().reset_index()
    #convert to GWh by /3.6
    demand['VALUE'] = demand['VALUE']/3.6
    #create a column called TECHNOLOGY with value 'Demand'
    demand['TECHNOLOGY'] = 'Demand'
    
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the YEAR
    fig = px.area(generation, x="YEAR", y="VALUE", color='TECHNOLOGY',title='Generation GWh',color_discrete_map=create_color_dict(generation['TECHNOLOGY']))
    #and add line with points for demand
    fig.add_scatter(x=demand['YEAR'], y=demand['VALUE'], mode='lines+markers', name='Demand', line=dict(color=technology_color_dict['Demand']), marker=dict(color=technology_color_dict['Demand']))
    #
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_generation.html', auto_open=False)

def plot_emissions_annual(tall_results_dfs, paths_dict):
    """Plot emissions by year by technology"""
    #load emissions
    emissions = tall_results_dfs['AnnualTechnologyEmission']
    
    #drop technologies not in technology_mapping
    emissions = drop_categories_not_in_mapping(emissions, emissions_mapping, column='EMISSION')
    #map EMISSION to readable names:
    emissions['FUEL'] = emissions['EMISSION'].apply(extract_readable_name_from_emissions_technology)

    # sum emissions by technology and year
    emissions = emissions.groupby(['FUEL','YEAR']).sum().reset_index()
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time
    fig = px.area(emissions, x="YEAR", y="VALUE", color='FUEL', title='Emissions MtCO2',color_discrete_map=create_color_dict(emissions['FUEL']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_emissions.html')

def plot_capacity_annual(tall_results_dfs, paths_dict):
    """Plot capacity by technology"""
    #load capacity
    capacity = tall_results_dfs['TotalCapacityAnnual']#'CapacityByTechnology']#couldnt find CapacityByTechnology in the results but TotalCapacityAnnual is there and it seemed to be the same

    #drop technologies not in technology_mapping
    capacity = drop_categories_not_in_mapping(capacity, technology_mapping)
    #map TECHNOLOGY to readable names:
    capacity['TECHNOLOGY'] = capacity['TECHNOLOGY'].apply(extract_readable_name_from_powerplant_technology)
    
    #sum capacity by technology and year
    capacity = capacity.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time
    fig = px.area(capacity, x="YEAR", y="VALUE", color='TECHNOLOGY', title='Capacity GW',color_discrete_map=create_color_dict(capacity['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_capacity.html')

def plot_capacity_factor_annual(tall_results_dfs, paths_dict):
    
    generation = extract_generation_data(tall_results_dfs)

    #extract capcity data
    capacity = tall_results_dfs['TotalCapacityAnnual']#'CapacityByTechnology']
    
    
    capacity = drop_categories_not_in_mapping(capacity, technology_mapping)
    #couldnt find CapacityByTechnology in the results but TotalCapacityAnnual is there and it seemed to be the same
    capacity['TECHNOLOGY'] = capacity['TECHNOLOGY'].apply(extract_readable_name_from_powerplant_technology)

    #sum generation and capacity by technology and year
    capacity = capacity.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
    generation = generation.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()

    #join both dataframes on technology and year
    generation_capacity = generation.merge(capacity, on=['TECHNOLOGY','YEAR'])

    #calculate capacity factor as generation/capacity/8.76
    generation_capacity['VALUE'] = generation_capacity['VALUE_x']/generation_capacity['VALUE_y']/8.76

    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time
    fig = px.area(generation_capacity, x="YEAR", y="VALUE", color='TECHNOLOGY', title='Capacity Factor (0-1)',color_discrete_map=create_color_dict(generation_capacity['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/annual_capacity_factor.html')

def plot_average_generation_by_timeslice(tall_results_dfs, paths_dict):
    """Calculate average generation by timeslice for each technology and year. Also calculate average generation by technology and year for power plants, to Storage, from Storage and  demand"""
    generation = extract_generation_data(tall_results_dfs)
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

    timeslice_dict = create_timeslice_details()
    #extract details about timeslice and put them into a column called TOTAL_HOURS
    generation['TOTAL_HOURS'] = generation['TIMESLICE'].apply(lambda x: timeslice_dict[x][1])
    #calculate average generation by dividing by total hours times 1000
    generation['VALUE'] = generation['VALUE']/generation['TOTAL_HOURS'] * 1000

    #get total capacity by technology and year
    capacity = tall_results_dfs['TotalCapacityAnnual']#'CapacityByTechnology']
    
    
    capacity = drop_categories_not_in_mapping(capacity, technology_mapping)
    #couldnt find CapacityByTechnology in the results but TotalCapacityAnnual is there and it seemed to be the same
    capacity['TECHNOLOGY'] = capacity['TECHNOLOGY'].apply(extract_readable_name_from_powerplant_technology)

    capacity = capacity.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
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

    #make sure Timeslice = capacity is at the bottom

    #create a dictionary with the technology as key and the color as value using create_color_dict(technology_or_fuel_column) to get the colors
    color_dict = create_color_dict(generation['TECHNOLOGY'])
    for year in range(min_year,max_year+1,10):
        fig = px.bar(generation[(generation['YEAR'] == year) & (generation['TECHNOLOGY'] != 'Demand')], x="TIMESLICE", y="VALUE", color='TECHNOLOGY', title='Average generation by timeslice for year '+str(year),color_discrete_map=color_dict)
        fig.add_scatter(x=generation[(generation['YEAR'] == year) & (generation['TECHNOLOGY'] == 'Demand')]['TIMESLICE'], y=generation[(generation['YEAR'] == year) & (generation['TECHNOLOGY'] == 'Demand')]['VALUE'], mode='lines+markers', name='Demand', line=dict(color=color_dict['Demand']), marker=dict(color=color_dict['Demand']))
        #save as html
        fig.write_html(paths_dict['visualisation_directory']+'/generation_by_timeslice_'+str(year)+'.html', auto_open=False)

def plot_8th_graphs(paths_dict):
    #load in data from data/8th_output.xlsx
    data_8th = {}
    with pd.ExcelFile('data/8th_output.xlsx') as xls:
        for sheet in xls.sheet_names:
            data_8th[sheet] = pd.read_excel(xls,sheet_name=sheet)
    
    expected_sheet_names = ['generation_by_tech']#,'Demand','emissions']

    #first print any differences betwen expected and actual
    if set(expected_sheet_names) != set(data_8th.keys()):
        logging.warning("The expected sheets in data/8th_output.xlsx are not the same as the actual sheets")
        logging.warning("Expected sheets: ", expected_sheet_names)
        logging.warning("Actual sheets: ", data_8th.keys())
    
    #NOW PLOT A DIFFERENT GRAPH FOR EACH SHEET WE EXPECT. YOU WILL AHVE TO CREATE A NEW FUNCTION FOR EACH GRAPH
    #plot generation by technology
    plot_8th_generation_by_tech(data_8th,paths_dict)

def plot_8th_generation_by_tech(data_8th,paths_dict):
    generation = data_8th['generation_by_tech']
    #drop total TECHNOLOGY
    generation = generation[generation['TECHNOLOGY'] != 'Total']
    #make the data into tall format
    generation = generation.melt(id_vars='TECHNOLOGY', var_name='YEAR', value_name='VALUE')
    #plot an area chart with color determined by the TECHNOLOGY column, and the x axis is the time
    fig = px.area(generation, x="YEAR", y="VALUE", color='TECHNOLOGY', title='Generation GWh', color_discrete_map=create_color_dict(generation['TECHNOLOGY']))
    #save as html
    fig.write_html(paths_dict['visualisation_directory']+'/8th_generation_by_tech.html', auto_open=False)



#########################UTILITY FUNCTIONS#######################
def drop_categories_not_in_mapping(df, mapping, column='TECHNOLOGY'):
    #drop technologies not in technology_mapping
    df = df[df[column].isin(mapping.keys())]
    #if empty raise a warning
    if df.empty:
        warnings.warn(f'Filtering data in {column} caused the dataframe to become empty')
    return df

def extract_readable_name_from_powerplant_technology(technology):
    """Use the set of TECHNOLOGIES we expect in the power model and map them to readable names"""
    if technology not in technology_mapping.keys():
        logging.warning(f"Technology {technology} is not in the expected set of technologies during extract_readable_name_from_powerplant_technology()")
        raise ValueError("Technology is not in the expected set of technologies")
        return technology
    return technology_mapping[technology]
    
def extract_readable_name_from_emissions_technology(technology):
    """Use the set of fuels we expect in the power model, which have emission factors and map them to readable names"""
    if technology not in emissions_mapping.keys():
        logging.warning(f"Technology {technology} is not in the expected set of technologies during extract_readable_name_from_emissions_technology()")
        raise ValueError("Technology is not in the expected set of technologies")
        return technology
    return emissions_mapping[technology]


def create_timeslice_details():
    """Below is a dictionary of the different details by timeslice. It was created using code by copy pasting the details from Alex's spreadhseet. The first entry is the key, the second is the proportion of the year that the timeslice makes up (all summing to 1), and the third is the number of hours in the timeslice (all summing to 8760)."""
    timeslice_dict = {
        'WW0004': (0.028767123, 252),
        'WW0408': (0.028767123, 252),
        'WW0812': (0.028767123, 252),
        'WW1216': (0.028767123, 252),
        'WW1620': (0.028767123, 252),
        'WW2024': (0.028767123, 252),
        'WH0004': (0.012328767, 108),
        'WH0408': (0.012328767, 108),
        'WH0812': (0.012328767, 108),
        'WH1216': (0.012328767, 108),
        'WH1620': (0.012328767, 108),
        'WH2024': (0.012328767, 108),
        'IW0004': (0.059817352, 524),
        'IW0408': (0.059817352, 524),
        'IW0812': (0.059817352, 524),
        'IW1216': (0.059817352, 524),
        'IW1620': (0.059817352, 524),
        'IW2024': (0.059817352, 524),
        'IH0004': (0.023744292, 208),
        'IH0408': (0.023744292, 208),
        'IH0812': (0.023744292, 208),
        'IH1216': (0.023744292, 208),
        'IH1620': (0.023744292, 208),
        'IH2024': (0.023744292, 208),
        'SW0004': (0.030136986, 264),
        'SW0408': (0.030136986, 264),
        'SW0812': (0.030136986, 264),
        'SW1216': (0.030136986, 264),
        'SW1620': (0.030136986, 264),
        'SW2024': (0.030136986, 264),
        'SH0004': (0.011872146, 104),
        'SH0408': (0.011872146, 104),
        'SH0812': (0.011872146, 104),
        'SH1216': (0.011872146, 104),
        'SH1620': (0.011872146, 104),
        'SH2024': (0.011872146, 104)
    }
    #double check that the sum of the proportions is 1 or close to 1
    assert sum([x[0] for x in timeslice_dict.values()]) > 0.999
    #double check that the sum of the hours is 8760
    assert sum([x[1] for x in timeslice_dict.values()]) == 8760
    
    return timeslice_dict

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


# #div by 3.6 to get GWh
# storage_charge['VALUE'] = storage_charge['VALUE']/3.6
# storage_discharge['VALUE'] = storage_discharge['VALUE']/3.6

# #sum charge and discharge by year
# storage_charge_annual = storage_charge.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()
# storage_discharge_annual = storage_discharge.groupby(['TECHNOLOGY','YEAR']).sum().reset_index()

# #sum by timeslice
# storage_charge_timeslice = storage_charge.groupby(['TECHNOLOGY','TIMESLICE']).sum().reset_index()
# storage_discharge_timeslice = storage_discharge.groupby(['TECHNOLOGY','TIMESLICE']).sum().reset_index()

#put them in dict
# storage_dict = {'storage_charge_annual':storage_charge_annual,
#                             'storage_discharge_annual':storage_discharge_annual,
#                             'storage_charge_timeslice':storage_charge_timeslice,
#                             'storage_discharge_timeslice':storage_discharge_timeslice}



#     #calculate grouped average generation by technology and year for power plants, to Storage, from Storage and  demand
#     generation_grouped = generation.copy()
#     generation_grouped['TECHNOLOGY'] = generation_grouped['TECHNOLOGY'].apply(group_technologies_by_type)


# def group_technologies_by_type(technology):
#     """Group technologies by type"""
#     if technology in ['Coal','Gas','Oil','Hydro','Wind','Solar','Geothermal','Biomass','Other']:
#         return 'Power'
#     elif technology in ['Storage_charge']:
#         return 'Storage_charge'
#     elif technology in ['Storage_discharge']:
#         return 'Storage_discharge'
#     elif technology in ['Demand']:
#         return 'Demand'
#     elif technology in ['Imports']:
#         return 'Imports'
#     else:
#         #create error
#         raise ValueError("Technology not recognised")