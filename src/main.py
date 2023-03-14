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
input_data_sheet_file="data-sheet-power.xlsx"#"data-sheet-power-finn-test.xlsx"# "data-sheet-power-24ts.xlsx"#"data-sheet-power-finn-test.xlsx"#"data-sheet-power-24ts.xlsx"#"data-sheet-power-finn-test.xlsx"#current data-sheet-power has no data in it
data_config_file = "otoole_config_original.yml"#_copy.yml"
# results_config_file = "results_config_copy_test.yml"
#define the model script you will use (one of osemosys_fast.txt, osemosys.txt, osemosys_short.txt)

#this MUST be one of osmoseys_fast.txt or osemosys.txt. Otherwise we will have to change the code around line 86 of model_solving_functions.py
osemosys_model_script = 'osemosys_fast.txt'# 'osemosys_fast.txt'
osemosys_cloud = False

solving_method = 'coin-cbc'#'glpsol'#'coin-cbc'#'coin-cbc'#coin-cbc'#'coin-cbc'#'glpsol'#coin-cbc'#pick from glpsol, coin-cbc 

strict_error_checking = True #if true, will raise errors if there are missing data or data that is not in the data config file. If false, will just print a warning and continue
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

input_keys_short_names, results_keys, data_config,data_config_short_names = model_preparation_functions.import_data_config(paths_dict)

start2 = time.time()
filtered_input_data = model_preparation_functions.extract_input_data(paths_dict, input_keys_short_names, model_end_year,economy,scenario)
print("\nTime taken to extract input data: {}\n########################\n ".format(time.time()-start2))

model_preparation_functions.write_data_to_temp_workbook(paths_dict, filtered_input_data)

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

    #open log file in case of error:
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
        
post_processing_functions.remove_apostrophes_from_region_names(paths_dict, osemosys_cloud, results_keys, data_config)

#%%
keys_to_ignore=['TotalDiscountedCost','CapitalInvestment']#dropping these because we know they are causing problems. We will add them back in later
#drop tehse keys from the results keys list
results_keys_new = [key for key in results_keys if key not in keys_to_ignore]

post_processing_functions.save_results_as_excel(paths_dict, scenario, results_keys_new, data_config)

print("\nTime taken for save_results_as_excel: {}\n########################\n ".format(time.time()-start))
start = time.time()

post_processing_functions.save_results_as_long_csv(paths_dict,results_keys_new)
print("\nTime taken for save_results_as_long_csv: {}\n########################\n ".format(time.time()-start))

#%%
start = time.time()
#Visualisation:
post_processing_functions.create_res_visualisation(paths_dict,scenario,economy)
print("\nTime taken for create_res_visualisation: {}\n########################\n ".format(time.time()-start))
#%%
