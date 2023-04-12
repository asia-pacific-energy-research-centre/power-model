
#import libs
import pandas as pd

if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")
do_this = False
if do_this:
    #load D:\APERC\power-model\config\long_to_short_names_concordance.xlsx
    long_to_short_names_concordance = pd.read_excel(r'D:\APERC\power-model\config\long_to_short_names_concordance.xlsx',sheet_name=None)
    long_names_dict = {}
    #for every sheet in the excel file, extract the first col and put it in a list called long names. then put the list in a dictionary with the sheet name as the key
    for sheet in long_to_short_names_concordance:
        long_names_dict[sheet] = list(long_to_short_names_concordance[sheet].iloc[:,0])

    #now print each lsit out
    for sheet in long_names_dict:
        print(sheet)
        print(long_names_dict[sheet])


    #
    EMISSION = ['1_x_coal_thermal_CO2', '1_5_lignite_CO2', '2_coal_products_CO2', '7_7_gas_diesel_oil_CO2', '7_8_fuel_oil_CO2', '8_1_natural_gas_CO2', '8_1_natural_gas_CCS_CO2', '15_solid_biomass_CO2', '16_others_CO2']
    TIMESLICE = ['WW0004', 'WW0408', 'WW0812', 'WW1216', 'WW1620', 'WW2024', 'WH0004', 'WH0408', 'WH0812', 'WH1216', 'WH1620', 'WH2024', 'IW0004', 'IW0408', 'IW0812', 'IW1216', 'IW1620', 'IW2024', 'IH0004', 'IH0408', 'IH0812', 'IH1216', 'IH1620', 'IH2024', 'SW0004', 'SW0408', 'SW0812', 'SW1216', 'SW1620', 'SW2024', 'SH0004', 'SH0408', 'SH0812', 'SH1216', 'SH1620', 'SH2024']
    FUEL = ['17_electricity', '17_electricity_Dx', '17_electricity_own', '17_electricity_loss', '17_electricity_imports', '17_electricity_PV', '1_x_coal_thermal', '1_5_lignite', '2_coal_products', '7_7_gas_diesel_oil', '7_8_fuel_oil', '8_1_natural_gas', '8_1_natural_gas_CCS', '10_hydro', '11_geothermal', '12_1_of_which_photovoltaics', '14_wind', '15_solid_biomass', '16_others']
    TECHNOLOGY = ['POW_Coal_PP', 'POW_Oil_PP', 'POW_Gas_PP', 'POW_Gas_CCS_PP', 'POW_Hydro_PP', 'POW_Geothermal_PP', 'POW_SolarPV_PP', 'POW_Wind_PP', 'POW_Solid_Biomass_PP', 'POW_Other_PP', 'POW_Transmission', 'POW_TRN', 'POW_IMPORT_ELEC_PP', 'POW_TBATT', 'POW_1_x_coal_thermal', 'POW_1_5_lignite', 'POW_2_coal_products', 'POW_7_7_gas_diesel_oil', 'POW_7_8_fuel_oil', 'POW_8_1_natural_gas', 'POW_8_1_natural_gas_CCS', 'POW_10_hydro', 'POW_11_geothermal', 'POW_12_1_of_which_photovoltaics', 'POW_14_wind', 'POW_15_solid_biomass', 'POW_16_others', 'POW_17_electricity_imports', 'YYY_1_x_coal_thermal', 'YYY_1_5_lignite', 'YYY_2_coal_products', 'YYY_7_7_gas_diesel_oil', 'YYY_7_8_fuel_oil', 'YYY_8_1_natural_gas', 'YYY_8_1_natural_gas_CCS', 'YYY_10_hydro', 'YYY_11_geothermal', 'YYY_12_1_of_which_photovoltaics', 'YYY_14_wind', 'YYY_15_solid_biomass', 'YYY_16_others', 'YYY_17_electricity', 'YYY_17_electricity_PV', 'YYY_17_electricity_Dx', 'YYY_17_electricity_own', 'YYY_17_electricity_loss', 'YYY_17_electricity_imports']

    #for every value in the lists above we need a unique, 5 chracter name to identify it, that is different from all other values in the list and the other lists.
    EMISSION_short = ['1_xC02','1_5C02','2C02','7_7C02','7_8C02','8_1C02','8_1CCSC02','15C02','16C02']
    #for timeselice we only need thefirst two cahracters followe by a number, whch can jsut be the index of the list
    TIMESLICE_short = ['WW0','WW1','WW2','WW3','WW4','WW5','WH0','WH1','WH2','WH3','WH4','WH5','IW0','IW1','IW2','IW3','IW4','IW5','IH0','IH1','IH2','IH3','IH4','IH5','SW0','SW1','SW2','SW3','SW4','SW5','SH0','SH1','SH2','SH3','SH4','SH5']
    FUEL_short = ['17','17D','17O','17L','17I','17P','1','1_5','2','7_7','7_8','8_1','8_1CCS','10','11','12','14','15','16']
    TECHNOLOGY_short = ['PC','PO','PG','PGC','PH','PGT','PS','PW','PB','POt','PT','PTR','PI','PTB','P1','P1_5','P2','P7_7','P7_8','P8_1','P8_1CCS','P10','P11','P12','P14','P15','P16','P17I','Y1','Y1_5','Y2','Y7_7','Y7_8','Y8_1','Y8_1CCS','Y10','Y11','Y12','Y14','Y15','Y16','Y17','Y17P','Y17D','Y17O','Y17L','Y17I']

    #now we need to create a dictionary for each list, with the short name as the key and the short name as the value. Then we will create a df from each dictionary and save it as a csv file.
    EMISSION_dict = {}
    for i in range(len(EMISSION)):
        EMISSION_dict[EMISSION[i]] = EMISSION_short[i]
    TIMESLICE_dict = {}
    for i in range(len(TIMESLICE)):
        TIMESLICE_dict[TIMESLICE[i]] = TIMESLICE_short[i]
    FUEL_dict = {}
    for i in range(len(FUEL)):
        FUEL_dict[FUEL[i]] = FUEL_short[i]
    TECHNOLOGY_dict = {}
    for i in range(len(TECHNOLOGY)):
        TECHNOLOGY_dict[TECHNOLOGY[i]] = TECHNOLOGY_short[i]

    EMISSION_df = pd.DataFrame.from_dict(EMISSION_dict, orient='index', columns=['short_name'])
    TIMESLICE_df = pd.DataFrame.from_dict(TIMESLICE_dict, orient='index', columns=['short_name'])
    FUEL_df = pd.DataFrame.from_dict(FUEL_dict, orient='index', columns=['short_name'])
    TECHNOLOGY_df = pd.DataFrame.from_dict(TECHNOLOGY_dict, orient='index', columns=['short_name'])
    #make teh df index the long name
    EMISSION_df.index.name = 'long_name'
    TIMESLICE_df.index.name = 'long_name'
    FUEL_df.index.name = 'long_name'
    TECHNOLOGY_df.index.name = 'long_name'

    #make sure there are no duplicates wehn we concatinate the dfs.
    large_df = pd.concat([EMISSION_df, TIMESLICE_df, FUEL_df, TECHNOLOGY_df])
    #extract the duplicates in short
    duplicates = large_df[large_df.duplicated(['short_name'], keep=False)]
    if len(duplicates) > 0:
        raise ValueError('There are duplicates in the short names. Please check the lists above and make sure they are unique.')

    #add them all to one xlsx
    with pd.ExcelWriter('config/long_variable_names_to_short_variable_names_new.xlsx') as writer:
        EMISSION_df.to_excel(writer, sheet_name='EMISSION')
        TIMESLICE_df.to_excel(writer, sheet_name='TIMESLICE')
        FUEL_df.to_excel(writer, sheet_name='FUEL')
        TECHNOLOGY_df.to_excel(writer, sheet_name='TECHNOLOGY')


#extract short names from the regions by removing the numbers and _
# 01_AUS
# 02_BD
# 03_CDA
# 04_CHL
# 05_PRC
# 06_HKC
# 07_INA
# 08_JPN
# 09_ROK
# 10_MAS
# 11_MEX
# 12_NZ
# 13_PNG
# 14_PE
# 15_RP
# 16_RUS
# 17_SIN
# 18_CT
# 19_THA
# 20_USA
# 21_VN

regions = ['01_AUS','02_BD','03_CDA','04_CHL','05_PRC','06_HKC','07_INA','08_JPN','09_ROK','10_MAS','11_MEX','12_NZ','13_PNG','14_PE','15_RP','16_RUS','17_SIN','18_CT','19_THA','20_USA','21_VN']
regions_short = ['AUS','BD','CDA','CHL','PRC','HKC','INA','JPN','ROK','MAS','MEX','NZ','PNG','PE','RP','RUS','SIN','CT','THA','USA','VN']
#save as csv
regions_df = pd.DataFrame({'long_name':regions, 'short_name':regions_short})
regions_df.to_csv('regions_long_to_short.csv', index=False)