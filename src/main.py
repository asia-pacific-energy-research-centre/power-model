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
import logging
################################################################################
#LESS IMPORTANT VARIABLES TO SET (their default values are fine):
FILE_DATE_ID = time.strftime("%Y-%m-%d-%H%M%S")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
config_dir = 'config'
#this MUST be one of osmoseys_fast.txt or osemosys.txt. Otherwise we will have to change the code around line 86 of model_solving_functions.py
osemosys_model_script = 'osemosys.txt'
extract_osemosys_cloud_results_using_otoole = True#False is the default, but if you want to use otoole to extract the results, set this to True
testing = True
################################################################################

def main(input_data_sheet_file):

    ################################################################################
    #EXTRACT CONFIG AND PREFERENCES
    ################################################################################

    #prep functions:
    config_dict = model_preparation_functions.set_up_config_dict(root_dir, input_data_sheet_file, extract_osemosys_cloud_results_using_otoole, osemosys_model_script)
    # config_dict['model_end_year'] = 2023#uncomment this to override the model end year in the excel file
    # config_dict['economy'] = '19_THA'
    # config_dict['scenario'] = 'Reference'
    # config_dict['data_config_file'] ="config.yaml"
    # config_dict['solving_method'] = 'coin'#or glpsol or cloud

    paths_dict = model_preparation_functions.set_up_paths_dict(root_dir, config_dir,FILE_DATE_ID,config_dict)

    ################################################################################
    #SET UP LOGGING
    ################################################################################
    if testing:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO
    #set up logging now that we have the paths all set up:
    logging.basicConfig(
        handlers=[
            logging.StreamHandler(sys.stdout),#logging will print things to the console as well as to the log file
            logging.FileHandler(paths_dict['log_file_path'])
        ], encoding='utf-8', level=logging_level, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger()
    logger.info(f"LOGGING STARTED: {FILE_DATE_ID}, being saved to {paths_dict['log_file_path']} and outputted to console")
    # logging.debug()
    # logging.info()
    # logging.warning()
    # logging.error()
    
    ################################################################################
    #PREPARE DATA
    ################################################################################
    config_dict = model_preparation_functions.import_data_config(paths_dict,config_dict)

    if config_dict['solving_method'] != 'cloud' or config_dict['osemosys_cloud_input'] == 'n':


        model_preparation_functions.write_model_run_specs_to_file(paths_dict, config_dict, FILE_DATE_ID)
        input_data = model_preparation_functions.extract_input_data(paths_dict, config_dict)
        model_preparation_functions.write_data_to_temp_workbook(paths_dict, input_data)

        model_preparation_functions.prepare_data_for_osemosys(paths_dict,config_dict)

        model_preparation_functions.prepare_model_script_for_osemosys(paths_dict, config_dict)
        #model_preparation_functions.validate_input_data(paths_dict)# todo: mnake this this function work. too many errors. possibly otoole needs to develop it more

    ################################################################################
    #SOLVE MODEL
    ################################################################################

    if config_dict['solving_method'] != 'cloud':

        model_solving_functions.solve_model(config_dict,paths_dict)
        logging.info(f"\n######################## \n Running solve process using{osemosys_model_script} for {config_dict['solving_method']} {config_dict['economy']} {config_dict['scenario']}")


    ################################################################################
    #Post processing
    ################################################################################
    #start new timer to tiome the post-processing
    if config_dict['osemosys_cloud_input'] =='y' or config_dict['solving_method'] != 'cloud':
        config_dict = post_processing_functions.process_osemosys_cloud_results(paths_dict, config_dict)

        post_processing_functions.remove_apostrophes_from_region_names(paths_dict, config_dict)


        sheets_to_ignore_if_error_thrown=[]#['TotalDiscountedCost','CapitalInvestment','DiscountedCapitalInvestment','NumberOfNewTechnologyUnits','SalvageValueStorage','Trade']#This provides an option for dropping these values because we know they are causing problems if we set their values for calculated: True. By default we will not drop any of these values, but if we want to we can add them to this list.

        # #drop these keys from the results keys list
        # results_sheets_new = [sheet for sheet in results_sheets if sheet not in sheets_to_ignore]

        config_dict = post_processing_functions.save_results_as_excel(paths_dict, config_dict,sheets_to_ignore_if_error_thrown,quit_if_missing_csv=False)

        post_processing_functions.save_results_as_long_csv(paths_dict,config_dict,sheets_to_ignore_if_error_thrown)

        #Visualisation:
        post_processing_functions.create_res_visualisation(paths_dict,config_dict)

        if testing:
            #FOR TESTING:
            #copy results and tmp folder contents to a new folder in the results folder which will be used to comapre the results of the model run with the previous run. We will uyse the file date id to name the folder.
            #create foldewr
            import shutil
            os.mkdir('./results/'+ f"{FILE_DATE_ID}")
            #copy all files (not folders) from the tmp directory to the new folder
            for file in os.listdir(paths_dict['tmp_directory']):
                if os.path.isfile(os.path.join(paths_dict['tmp_directory'], file)):
                    shutil.copy(os.path.join(paths_dict['tmp_directory'], file), os.path.join('./results/'+ f"{FILE_DATE_ID}", file))
            #copy results_workbook, combined_results_tall_years, combined_results_tall_sheet_names to the new folder
            shutil.copy(paths_dict['results_workbook'], './results/'+ f"{FILE_DATE_ID}")
            shutil.copy(paths_dict['combined_results_tall_years'], './results/'+ f"{FILE_DATE_ID}")
            shutil.copy(paths_dict['combined_results_tall_sheet_names'], './results/'+ f"{FILE_DATE_ID}")

        

        #copy results folder

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
    input_data_sheet_file="data-sheet-power_36TS.xlsx"#"simplicity_data.xlsx"#set this based on the data sheet you want to run if you are running this from jupyter notebook
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

