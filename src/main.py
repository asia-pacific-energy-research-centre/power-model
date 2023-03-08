# this script takes in the power data sheet and runs the osemosys model
# configure the model run in the START tab of the excel file
# You can run this file from the command line or using jupyter interactive notebook. 

# the following python packages are imported:
#%%
import time
import os
import sys
from post_processing_functions import create_res_visualisation, save_results_as_excel,save_results_as_long_csv,remove_apostrophes_from_region_names, extract_osmosys_cloud_results_to_csv
from model_preparation_functions import import_run_preferences, import_data_config, import_and_clean_data, write_data_to_tmp,compare_combined_data_to_data_config, prepare_data_for_osemosys, set_up_paths
from model_solving_functions import prepare_solving_process, solve_model
# the processing script starts from here
# get the time you started the model so the results will have the time in the filename
model_start = time.strftime("%Y-%m-%d-%H%M%S")

print(f"Script started at {model_start}...\n")
# model run inputs
#%%
#################################################################################MANUALLY SET THESE VARIABLES
################################################################################
model_start = time.strftime("%Y-%m-%d-%H%M%S")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
config_dir = 'config'
#save name of the inputted data sheet here for ease of use:
input_data_sheet_file= "data-sheet-power-24ts.xlsx"#"data-sheet-power-finn-test.xlsx"#current data-sheet-power has no data in it
data_config_file = "data_config_copy.yml"
results_config_file = "results_config_copy_test.yml"
#define the model script you will use (one of osemosys_fast.txt, osemosys.txt, osemosys_short.txt)
osemosys_model_script = 'osemosys_fast.txt'
osemosys_cloud = True

solving_methods = ['coin-cbc']#pick from glpsol, coin-cbc 
#%%
################################################################################
#FOR RUNNING THROUGH JUPYTER INTERACTIVE NOTEBOOK (FINNS SETUP, need to make root of project the cwd)
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

config_dict, economy, scenario, years = import_run_preferences(root_dir, input_data_sheet_file)

tmp_directory, results_directory, path_to_results_config, path_to_data_config, path_to_data_config, path_to_data_workbook, input_data_file_path,path_to_combined_data_sheet,path_to_input_data_file = set_up_paths(scenario, economy, root_dir, config_dir, results_config_file,data_config_file, input_data_sheet_file,osemosys_cloud)

data_config_short_names, short_to_long_name, data_config = import_data_config(path_to_data_config)

filtered_data = import_and_clean_data(data_config_short_names, economy,scenario,input_data_file_path)

subset_of_years = write_data_to_tmp(filtered_data, config_dict, path_to_data_workbook)

prepare_data_for_osemosys(data_config_short_names, data_config, path_to_combined_data_sheet, path_to_input_data_file, subset_of_years)

#%%
print("\nTime taken for preparation: {}\n########################\n ".format(time.time()-start))
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
    for osemosys_model_script in ['osemosys_fast.txt']:#,'osemosys.txt', 'osemosys_short.txt']:
        print(f'\n######################## \n Running solve process using{osemosys_model_script}')

        osemosys_model_script_path,model_file_path,log_file,cbc_intermediate_data_file_path,cbc_results_data_file_path = prepare_solving_process(root_dir, config_dir,  tmp_directory, economy, scenario,change_model_script=False,osemosys_model_script='osemosys_fast.txt')

        for solving_method in solving_methods:
            log_file = solve_model(solving_method, tmp_directory, path_to_results_config,log_file,model_file_path,path_to_input_data_file,cbc_intermediate_data_file_path,cbc_results_data_file_path)
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
    results_in_directory = extract_osmosys_cloud_results_to_csv(tmp_directory, path_to_results_config)
    if not results_in_directory:
        print("No results found in directory.")
        sys.exit()
        
remove_apostrophes_from_region_names(tmp_directory, path_to_results_config,remove_all_in_temp_dir=True)
# save_results_as_excel_OSMOSYS_CLOUD(tmp_directory, path_to_results_config, economy, scenario, root_dir,model_start)
# tmp_directory, path_to_results_config, economy, scenario, root_dir,model_start = 

save_results_as_excel(tmp_directory, results_directory,path_to_results_config, economy, scenario, model_start)

print("\nTime taken for save_results_as_excel: {}\n########################\n ".format(time.time()-start))
start = time.time()

save_results_as_long_csv(tmp_directory, results_directory,economy, scenario, model_start)
print("\nTime taken for save_results_as_long_csv: {}\n########################\n ".format(time.time()-start))

start = time.time()
#Visualisation:
path_to_results_config = path_to_data_config
create_res_visualisation(path_to_results_config,scenario,economy,path_to_input_data_file,results_directory)
print("\nTime taken for create_res_visualisation: {}\n########################\n ".format(time.time()-start))
#%%