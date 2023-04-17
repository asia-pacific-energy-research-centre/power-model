# this script takes in the power data sheet and runs the osemosys model
# configure the model run in the START tab of the excel file or by uncommenting and changing the variables below the model_preparation_functions.import_run_preferences() statement

# You can run this file from the command line or using jupyter interactive notebook. If using that you can change the input variables after the if is_notebook(): statement

# the following python packages are imported:

#%%
import time
import os
import sys

import model_preparation_functions
import model_solving_functions
import post_processing_functions
import plotting_functions
import logging
import pickle as pickle
################################################################################
#LESS IMPORTANT VARIABLES TO SET (their default values are fine):
FILE_DATE_ID = time.strftime("%m-%d-%H%M")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
#this MUST be one of osmoseys_fast.txt or osemosys.txt. Otherwise we will have to change the code around line 86 of model_solving_functions.py
keep_current_tmp_files = False
dont_solve = False
plotting = True
write_to_workbook = True
save_results_vis_and_inputs = True
################################################################################

def main(input_data_sheet_file):

    ################################################################################
    #EXTRACT CONFIG AND PREFERENCES
    ################################################################################

    #prep functions:
    config_dict = model_preparation_functions.set_up_config_dict(root_dir, input_data_sheet_file)

    #uncomment these to override the model settings in the excel file
    #config_dict['model_end_year'] = 2050
    # config_dict['model_start_year'] = 2019
    # config_dict['economy'] = '19_THA'
    # config_dict['scenario'] = 'Reference'
    # config_dict['data_config_file'] ="config.yaml"
    # config_dict['solving_method'] = 'coin'#or glpsol or cloud

    paths_dict = model_preparation_functions.set_up_paths_dict(root_dir,FILE_DATE_ID,config_dict,keep_current_tmp_files,write_to_workbook=write_to_workbook)

    ################################################################################
    #SET UP LOGGING
    ################################################################################
    model_preparation_functions.setup_logging(FILE_DATE_ID,paths_dict)
    
    ################################################################################
    #PREPARE DATA
    ################################################################################
    config_dict = model_preparation_functions.import_data_config(paths_dict,config_dict)

    if config_dict['solving_method'] != 'cloud' or config_dict['osemosys_cloud_input'] == 'n':
        model_preparation_functions.write_model_run_specs_to_file(paths_dict, config_dict, FILE_DATE_ID)
        input_data = model_preparation_functions.extract_input_data(paths_dict, config_dict)
        config_dict = model_preparation_functions.prepare_model_script_for_osemosys(paths_dict, config_dict)
        model_preparation_functions.write_data_config_to_new_file(paths_dict,config_dict)

        if write_to_workbook:
            model_preparation_functions.write_data_to_temp_workbook(paths_dict, input_data)
            model_preparation_functions.convert_workbook_to_datafile(paths_dict,config_dict)
        else:
            model_preparation_functions.write_input_data_as_csvs_to_data_folder(paths_dict, input_data)
            model_preparation_functions.convert_csvs_to_datafile(paths_dict)
            
        #model_preparation_functions.validate_input_data(paths_dict)# todo: mnake this this function work. too many errors. possibly otoole needs to develop it more

    ################################################################################
    #SOLVE MODEL
    ################################################################################

    if config_dict['solving_method'] != 'cloud' and not dont_solve:
        logging.info(f"\n######################## \n Running solve process using {config_dict['osemosys_model_script']} for {config_dict['solving_method']} {config_dict['economy']} {config_dict['scenario']}")
        model_solving_functions.solve_model(config_dict,paths_dict)

    ################################################################################
    #Post processing
    ################################################################################
    #start new timer to tiome the post-processing
    if config_dict['osemosys_cloud_input'] =='y' or config_dict['solving_method'] != 'cloud':
        config_dict = post_processing_functions.process_osemosys_cloud_results(paths_dict, config_dict)

        config_dict = post_processing_functions.check_for_missing_and_empty_results(paths_dict, config_dict)

        ##########################
        #extract and save results
        ##########################

        config_dict,tall_results_dfs,wide_results_dfs = post_processing_functions.extract_results_from_csvs(paths_dict, config_dict)

        post_processing_functions.save_results_as_excel(paths_dict, config_dict,wide_results_dfs)
        
        post_processing_functions.save_results_as_long_csvs(paths_dict,config_dict,tall_results_dfs)

        post_processing_functions.save_results_as_pickle(paths_dict,tall_results_dfs,config_dict)
        ##########################
        #Visualisation:
        ##########################
        post_processing_functions.create_res_visualisation(paths_dict,config_dict)
        
        if save_results_vis_and_inputs:
            post_processing_functions.save_results_visualisations_and_inputs_to_folder(paths_dict,save_plotting=False,save_results_and_inputs=True)

        post_processing_functions.TEST_output(paths_dict,config_dict)

        if plotting:
            plotting_functions.plotting_handler(tall_results_dfs=tall_results_dfs,paths_dict=paths_dict,config_dict=config_dict,load_from_pickle=True, pickle_paths=None)

        if save_results_vis_and_inputs:
            post_processing_functions.save_results_visualisations_and_inputs_to_folder(paths_dict,save_plotting=True, save_results_and_inputs=False)

#%%



################################################################################
#FOR RUNNING THROUGH JUPYTER INTERACTIVE NOTEBOOK (FINNS SETUP, allows for running the function outside of the command line through jupyter interactive)
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
    input_data_sheet_file="data-sheet-power_36TS.xlsx"#"simplicity_data.xlsx"#"data-sheet-power_36TS.xlsx"##set this based on the data sheet you want to run if you are running this from jupyter notebook
    #make directory the root of the project
    if os.getcwd().split('\\')[-1] == 'src':
        os.chdir('..')
        print("Changed directory to root of project")
    
    main(input_data_sheet_file)

elif __name__ == '__main__':

    if len(sys.argv) != 2:
        msg = "Usage: python {} <input_data_sheet_file>"
        print(msg.format(sys.argv[0]))
        sys.exit(1)
    else:
        input_data_sheet_file = sys.argv[1]
        main(input_data_sheet_file)
# %%

