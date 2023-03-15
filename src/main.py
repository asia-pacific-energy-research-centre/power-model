# this script takes in the power data sheet and runs the osemosys model
# configure the model run in the START tab of the excel file
# You can run this file from the command line or using jupyter interactive notebook. 

# the following python packages are imported:
#%%
import time
import os
import sys
import post_processing_functions as post_processing_functions
import model_preparation_functions as model_preparation_functions 
import model_solving_functions as model_solving_functions
# the processing script starts from here
# get the time you started the model so the results will have the time in the filename
model_start = time.strftime("%Y-%m-%d-%H%M%S")

print(f"Script started at {model_start}...\n")
# model run inputs
#%%
#################################################################################MANUALLY SET THESE VARIABLES
################################################################################
FILE_DATE_ID = time.strftime("%Y-%m-%d-%H%M%S")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
config_dir = 'config'
#save name of the inputted data sheet here for ease of use:
input_data_sheet_file="data-sheet-power-24ts.xlsx"#"data-sheet-power-finn-test.xlsx"# "data-sheet-power-24ts.xlsx"#"data-sheet-power-finn-test.xlsx"#"data-sheet-power-24ts.xlsx"#"data-sheet-power-finn-test.xlsx"#current data-sheet-power has no data in it
data_config_file = "config_all_calculated.yaml"#_copy.yml"otoole_config_original
# results_config_file = "results_config_copy_test.yml"
#define the model script you will use (one of osemosys_fast.txt, osemosys.txt, osemosys_short.txt)

#this MUST be one of osmoseys_fast.txt or osemosys.txt. Otherwise we will have to change the code around line 86 of model_solving_functions.py
osemosys_model_script = 'osemosys_fast.txt'# 'osemosys_fast.txt'
osemosys_cloud = False

solving_method = 'coin-cbc'#'coin-cbc'#'glpsol'#'coin-cbc'#'glpsol'#'coin-cbc'#'coin-cbc'#coin-cbc'#'coin-cbc'#'glpsol'#coin-cbc'#pick from glpsol, coin-cbc 

strict_error_checking = True #if true, will raise errors if there are missing data or data that is not in the data config file. If false, will just print a warning and continue

#got it to work using osemosys.txt/fast too,glpsol,config.yaml and data-sheet-power-24ts.xlsx
# BUT it doesnt work wioth coin-cbc for os fast and osemosys.txt
#TODO, see what the difference is in the logs between the two.
#NOTE THAT ONLY 8TH AND 24TS ARE SETUP ATM.

#NOTE THAT 8TH has an eror: ./tmp/19_THA/Reference/model_19_THA_Reference.txt:190: check['19_THA',POW_Other_Coal_PP,2017] failed MathProg model processing error.
# The 24ts model doesnt get this, it just doesnt print as much output as we want.

#ran it using 24ts all years coin cbc and fast. It seemed to work but there wereprimal infs and a lot of the of the results were blanks. saved as 19_THAtest8. Now testing using glpsol to see if we can see what the values SHOULD BE. This seemed to work but there were still infs being created:    eg. 3500: obj =   3.620622165e+09 inf =   1.322e+02 (18) 10. Saved as 19_THAtest9
# otoole results --input_datafile ./tmp/19_THA/Reference/datafile_from_python_19_THA_Reference.txt cbc csv ./tmp/19_THA/Reference/cbc_results_19_THA_Reference.sol ./tmp/19_THA/Reference ./config/config.yaml
#Trying osemosys.txt with coin and 24ts all years. 

#it seems thatt i can run cbc using .txt instead of .sol files. lets try this:
# cbc ./tmp/19_THA/Reference/cbc_input_19_THA_Reference.lp solve solu ./tmp/19_THA/Reference/cbc_results_19_THA_Reference.txt
# eg. cbc ./data/input_30422.lp solve solu ./data/output_30422.txt
# #and then: 
# otoole results --input_datafile ./tmp/19_THA/Reference/datafile_from_python_19_THA_Reference.txt cbc csv ./tmp/19_THA/Reference/cbc_results_19_THA_Reference.txt ./tmp/19_THA/Reference ./config/config.yaml
#i actually got: AttributeError: Can only use .str accessor with string values!

# I think the fast version might actually be working. See here from otoole:  https://otoole.readthedocs.io/en/latest/functionality.html 'The short and fast versions omit a large number of these calculated result variables so as to speed up the model matrix generation and solution times.' - but i think the results we are getting is far fewer than even osemosys_fast should be outputting. - no these are being created in the csvs in tmp folder during thhe use of solve i think? otoole results --input_datafile ./tmp/19_THAtest8/Reference/datafile_from_python_19_THA_Reference.txt cbc csv ./tmp/19_THAtest8/Reference/cbc_results_19_THA_Reference.sol ./tmp/19_THAtest8/Reference ./config/config.yaml - but some csvs werent created. like trade.csv. why? lets test if running thw previous calls will create them:
# glpsol -d ./tmp/19_THA/Reference/datafile_from_python_19_THA_Reference.txt -m ./tmp/19_THA/Reference/model_19_THA_Reference.txt --wlp ./tmp/19_THA/Reference/cbc_input_19_THA_Reference.lp --check
# cbc ./tmp/19_THA/Reference/cbc_input_19_THA_Reference.lp solve solu ./tmp/19_THA/Reference/cbc_results_19_THA_Reference.sol
#also the trade csv seemed to come from 20min before the otehrs?
#- i think it was because everything not ending up in the results folder has calcualted: False. so i think we need to change the config file to have all the results we want to be calculated: True. lets try this.
#that worked for most of the stuff. now there is just the set of sheets_to_ignore that arent being outputted. I reckon this is because the data to calcualte these values is jsut blank. With that assumption lets take the config file being used by power modellers and test if we can get what they want out
#%%
################################################################################
#FOR RUNNING THROUGH JUPYTER INTERACTIVE NOTEBOOK (FINNS SETUP, need to make root of project the cwd so we can import functions properly)
################################################################################
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
#%%
################################################################################
#PREPARE DATA
#preparation is done to clean up the input data that was manually created in the excel file. This most notably involves filtering for the specific scenario economy and years we want to model, and removing columns that are not needed.
# The output is a txt file that is the input data for OSeMOSYS. This is saved in the tmp folder for the economy and we are running the model for.
#this is like the otoole Convert step but allows for customised use of the data sheet
################################################################################
#start timer
start = time.time()

config_dict, economy, scenario, model_end_year = model_preparation_functions.import_run_preferences(root_dir, input_data_sheet_file)
# model_end_year = 2023
paths_dict = model_preparation_functions.set_up_paths(scenario, economy, root_dir, config_dir ,data_config_file, input_data_sheet_file,osemosys_model_script,osemosys_cloud,FILE_DATE_ID)

results_sheets, data_config, data_config_short_names = model_preparation_functions.import_data_config(paths_dict)
#%%
start2 = time.time()
input_data = model_preparation_functions.extract_input_data(data_config_short_names,paths_dict,model_end_year,economy,scenario)
print("\nTime taken to extract input data: {}\n########################\n ".format(time.time()-start2))


#%%

model_preparation_functions.write_data_to_temp_workbook(paths_dict, input_data)

model_preparation_functions.prepare_data_for_osemosys(paths_dict,data_config)

model_preparation_functions.prepare_model_script_for_osemosys(paths_dict, osemosys_cloud)

start2 = time.time()
model_preparation_functions.validate_input_data(paths_dict)# todo: fix this function
print("\nTime taken to validate data: {}\n########################\n ".format(time.time()-start2))

print("\nTotal time taken for preparation: {}\n########################\n ".format(time.time()-start))

#%%

################################################################################
#SOLVE MODEL
#Pull in the prepared data file and solve the model
################################################################################
# We first make a copy of osemosys_fast.txt so that we can modify where the results are written.
# Results from OSeMOSYS come in csv files. We first save these to the tmp directory for each economy.
# making a copy of the model file in the tmp directory so it can be modified

if not osemosys_cloud:
    #start new timer to time the solving process
    start = time.time()

    #open log file in case of error:|
    log_file = open(paths_dict['log_file_path'],'w')

    log_file = model_solving_functions.solve_model(solving_method,log_file,paths_dict)
    print(f'\n######################## \n Running solve process using{osemosys_model_script} for {solving_method} {economy} {scenario}')
    print("Time taken for solve_model: {}\n########################\n ".format(time.time()-start))

    log_file.close()
#%%
################################################################################
#Post processing
################################################################################
#start new timer to tiome the post-processing
start = time.time()

if osemosys_cloud:
    results_in_directory = post_processing_functions.extract_osmosys_cloud_results_to_csv(paths_dict,remove_results_txt_file=True)
    if not results_in_directory:
        print("No results found in directory.")
        sys.exit()
        
post_processing_functions.remove_apostrophes_from_region_names(paths_dict, osemosys_cloud, results_sheets, data_config)

#%%
sheets_to_ignore=['TotalDiscountedCost','CapitalInvestment','NumberOfNewTechnologyUnits','SalvageValueStorage','Trade']#dropping these because we know they are causing problems. We will add them back in later
#drop tehse keys from the results keys list

results_sheets_new = [sheet for sheet in results_sheets if sheet not in sheets_to_ignore]

post_processing_functions.save_results_as_excel(paths_dict, scenario, results_sheets_new, data_config)

print("\nTime taken for save_results_as_excel: {}\n########################\n ".format(time.time()-start))
start = time.time()

post_processing_functions.save_results_as_long_csv(paths_dict,results_sheets_new)
print("\nTime taken for save_results_as_long_csv: {}\n########################\n ".format(time.time()-start))

#%%
start = time.time()
#Visualisation:
post_processing_functions.create_res_visualisation(paths_dict,scenario,economy)
print("\nTime taken for create_res_visualisation: {}\n########################\n ".format(time.time()-start))
#%%




# #%%

# for col in sheet.columns:
#     if str(col).isdigit() and len(str(col)) == 4:
#         print(col)
#     else:
#         print(f'nope {col}')
# #%%
# import pandas as pd
# #load the excel file and save it as a new one to get rid of the protected sheets:
# wb = pd.ExcelFile(paths_dict['input_data_file_path'])
# #now parse every sheet in the workbook and save it to a new workbook:
# wb_new = pd.ExcelWriter('./data-sheet-power-8th.xlsx')
# for sheet_name in wb.sheet_names:
#     sheet = wb.parse(sheet_name)
#     sheet.to_excel(wb_new,sheet_name,index=False)
# wb_new.save()
# #%%



# glpsol -d ./tmp/19_THA/Reference/datafile_from_python_19_THA_Reference.txt -m ./tmp/19_THA/Reference/model_19_THA_Reference.txt --wlp ./tmp/19_THA/Reference/cbc_input_19_THA_Reference.lp --check

# otoole convert excel datafile ./tmp/19_THA/test/combined_data_19_THA_Reference.xlsx ./tmp/19_THA/test/datafile_from_python_19_THA_Reference.txt ./config/config.yaml

# glpsol -d ./tmp/19_THA/Reference/datafile_from_python_19_THA_Reference.txt -m ./tmp/19_THA/Reference/model_19_THA_Reference.txt --wlp ./tmp/19_THA/Reference/cbc_input_19_THA_Reference.lp --check

# $ otoole convert --help
# usage: otoole convert [-h] [--write_defaults] {csv,datafile,excel} {csv,datafile,excel} from_path to_path config

# positional arguments:
# {csv,datafile,excel}  Input data format to convert from
# {csv,datafile,excel}  Input data format to convert to
# from_path             Path to file or folder to convert from
# to_path               Path to file or folder to convert to
# config                Path to config YAML file

# optional arguments:
# -h, --help            show this help message and exit
# --write_defaults      Writes default values
# --keep_whitespace     Keeps leading/trailing whitespace


#%%
do_this = True
if do_this:
    import pandas as pd
    #put input data into tall format:
    #create empty df
    tall_df = pd.DataFrame() 
    for sheet in input_data.keys():
        if 2017 in input_data[sheet].columns:
            print(sheet)
            break
        #get the data from the sheet
        df = input_data[sheet]
        #add a column for the sheet name
        df['sheet'] = sheet
        #append to tall_df
        tall_df = pd.concat([tall_df, df], axis=0, ignore_index=True)
    #now pivot so we have a column for each sheet with the value in it
    #we will need to remove the following cols and then drop duplicates
    new_tall_df = tall_df.copy()
    new_tall_df.drop(['TIMESLICE',
 'STORAGE',
 'DAYTYPE',
 'DAILYTIMEBRACKET',
 'SEASON',
 'MODE_OF_OPERATION'], axis=1, inplace=True)
    cols = new_tall_df.columns.tolist()
    cols.remove('sheet')
    cols.remove('VALUE')
    new_tall_df.drop_duplicates(subset=cols, inplace=True)
    tall_df_wide = new_tall_df.pivot(index=cols, columns='sheet', values='VALUE')
    tall_df_wide.reset_index(inplace=True)

#check for duplicates in tall_df
tall_df[tall_df.duplicated(subset=cols, keep=False)]
#%%
#check tall_df for the sheets in the equation below, for the REGION, TECHNOLOGY and YEAR: ['19_THA',POW_Other_Coal_PP,2017] 
#%%

# check{r in REGION, t in TECHNOLOGY, y in YEAR:
#       TotalAnnualMaxCapacity[r,t,y]<>0 && TotalAnnualMaxCapacity[r,t,y] <> -1 && TotalTechnologyAnnualActivityLowerLimit[r,t,y]<>0 && AvailabilityFactor[r,t,y]<>0 && CapacityToActivityUnit[r,t]<>0}: sum{l in TIMESLICE: CapacityFactor[r,t,l,y]<>0 && YearSplit[l,y]<>0}(CapacityFactor[r,t,l,y]*YearSplit[l,y])*TotalAnnualMaxCapacity[r,t,y]* AvailabilityFactor[r,t,y]*CapacityToActivityUnit[r,t] >= TotalTechnologyAnnualActivityLowerLimit[r,t,y];

# a = tall_df[(tall_df['REGION']=='19_THA') & (tall_df['TECHNOLOGY']=='POW_Other_Coal_PP') & (tall_df['YEAR']==2017)]
# #filter for the sheets in the equation above
# a = a[a['sheet'].isin(['TotalAnnualMaxCapacity','TotalTechnologyAnnualActivityLowerLimit','AvailabilityFactor','CapacityToActivityUnit','CapacityFactor','YearSplit'])]

# #and then for : 
# # table TotalDiscountedCostResults
# # 	{r in REGION, y in YEAR}
# # 	OUT "CSV"
# # 	ResultsPath & "/TotalDiscountedCost.csv":
# # 	r~REGION, y~YEAR,
# # 	sum{t in TECHNOLOGY}
# #         ((((sum{yy in YEAR: y-yy < OperationalLife[r,t] && y-yy>=0}
# #             NewCapacity[r,t,yy]) + ResidualCapacity[r,t,y]) * FixedCost[r,t,y]
# #           + sum{l in TIMESLICE, m in MODEperTECHNOLOGY[t]}
# #                 RateOfActivity[r,l,t,m,y] * YearSplit[l,y] * VariableCost[r,t,m,y]) / (DiscountFactorMid[r,y])
# #           + CapitalCost[r,t,y] * NewCapacity[r,t,y] * CapitalRecoveryFactor[r,t] * PvAnnuity[r,t]/ (DiscountFactor[r,y])
# #           + DiscountedTechnologyEmissionsPenalty[r,t,y]
# #           - DiscountedSalvageValue[r,t,y])
# #           + sum{s in STORAGE}
# #                 (CapitalCostStorage[r,s,y] * NewStorageCapacity[r,s,y] / (DiscountFactorStorage[r,s,y])
# #                  - CapitalCostStorage[r,s,y] * NewStorageCapacity[r,s,y] / (DiscountFactorStorage[r,s,y])
# #           )~VALUE;
# #%%
# b = tall_df[(tall_df['REGION']=='19_THA') & (tall_df['YEAR']==2017)]
# #filter for the sheets in the equation above
# b = b[b['sheet'].isin(['NewCapacity','ResidualCapacity','FixedCost','RateOfActivity','YearSplit','VariableCost','DiscountFactorMid','CapitalCost','NewCapacity','CapitalRecoveryFactor','PvAnnuity','DiscountFactor','DiscountedTechnologyEmissionsPenalty','DiscountedSalvageValue','CapitalCostStorage','NewStorageCapacity','DiscountFactorStorage'])]
# # %%
# array(['AccumulatedAnnualDemand', 'AnnualEmissionLimit',
#        'AvailabilityFactor', 'CapacityFactor', 'CapacityToActivityUnit',
#        'CapitalCost', 'CapitalCostStorage', 'Conversionld',
#        'Conversionlh', 'Conversionls', 'DAILYTIMEBRACKET',
#        'DaysInDayType', 'DaySplit', 'DAYTYPE', 'DepreciationMethod',
#        'EMISSION', 'EmissionActivityRatio', 'FixedCost', 'FUEL',
#        'InputActivityRatio', 'MODE_OF_OPERATION', 'OperationalLife',
#        'OperationalLifeStorage', 'OutputActivityRatio', 'REGION',
#        'ReserveMargin', 'ReserveMarginTagFuel',
#        'ReserveMarginTagTechnology', 'ResidualCapacity',
#        'ResidualStorageCapacity', 'SEASON', 'SpecifiedAnnualDemand',
#        'SpecifiedDemandProfile', 'STORAGE', 'StorageLevelStart',
#        'StorageMaxChargeRate', 'StorageMaxDischargeRate', 'TECHNOLOGY',
#        'TechnologyFromStorage', 'TechnologyToStorage', 'TIMESLICE',
#        'TotalAnnualMaxCapacity', 'TotalAnnualMinCapacity', 'VariableCost',
#     #    'YEAR', 'YearSplit', 'TotalTechnologyAnnualActivityLo'],