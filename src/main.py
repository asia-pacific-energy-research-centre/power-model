# this script takes in the power data sheet and runs the osemosys model
# configure the model run in the START tab of the excel file or by uncommenting and changing the variables below the model_preparation_functions.import_run_preferences() statement

# You can run this file from the command line or using jupyter interactive notebook. If using that you can change the input variables after the if is_notebook(): statement

# the following python packages are imported:
#%%
import time
import os
import sys
import post_processing_functions as post_processing_functions
import model_preparation_functions as model_preparation_functions 
import model_solving_functions as model_solving_functions
################################################################################
#LESS IMPORTANT VARIABLES TO SET (their default values are fine):
FILE_DATE_ID = time.strftime("%Y-%m-%d-%H%M%S")
root_dir = '.' # because this file is in src, the root may change if it is run from this file or from command line
config_dir = 'config'
#this MUST be one of osmoseys_fast.txt or osemosys.txt. Otherwise we will have to change the code around line 86 of model_solving_functions.py
osemosys_model_script = 'osemosys_fast.txt'
extract_osemosys_cloud_results_using_otoole = True#False is the default, but if you want to use otoole to extract the results, set this to True
################################################################################

def main(input_data_sheet_file):

    # get the time you started the model so the results will have the time in the filename
    model_start = time.strftime("%Y-%m-%d-%H%M%S")

    print(f"Script started at {model_start}...\n")


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
    
    config_dict = model_preparation_functions.import_data_config(paths_dict,config_dict)


    ################################################################################
    #PREPARE DATA
    ################################################################################
    

    if config_dict['solving_method'] != 'cloud' or config_dict['osemosys_cloud_input'] == 'n':
        #start timer
        start = time.time()

        model_preparation_functions.write_model_run_specs_to_file(paths_dict, config_dict, FILE_DATE_ID)

        start2 = time.time()
        input_data = model_preparation_functions.extract_input_data(paths_dict, config_dict)
        print("\nTime taken to extract input data: {}\n########################\n ".format(time.time()-start2))

        model_preparation_functions.write_data_to_temp_workbook(paths_dict, input_data)

        model_preparation_functions.prepare_data_for_osemosys(paths_dict,config_dict)

        model_preparation_functions.prepare_model_script_for_osemosys(paths_dict, config_dict)

        start2 = time.time()
        model_preparation_functions.validate_input_data(paths_dict)# todo: mnake this this function work by creating the data vaildation yaml file.
        print("\nTime taken to validate data: {}\n########################\n ".format(time.time()-start2))

        print("\nTotal time taken for preparation: {}\n########################\n ".format(time.time()-start))



    ################################################################################
    #SOLVE MODEL
    ################################################################################

    if config_dict['solving_method'] != 'cloud':
        #start new timer to time the solving process
        start = time.time()

        #open log file in case of error:|
        log_file = open(paths_dict['log_file_path'],'w')

        log_file = model_solving_functions.solve_model(config_dict,log_file,paths_dict)
        print(f"\n######################## \n Running solve process using{osemosys_model_script} for {config_dict['solving_method']} {config_dict['economy']} {config_dict['scenario']}")
        print("Time taken for solve_model: {}\n########################\n ".format(time.time()-start))

        log_file.close()


    ################################################################################
    #Post processing
    ################################################################################
    #start new timer to tiome the post-processing
    start = time.time()

    config_dict = post_processing_functions.process_osemosys_cloud_results(paths_dict, config_dict)

    post_processing_functions.remove_apostrophes_from_region_names(paths_dict, config_dict)


    sheets_to_ignore_if_error_thrown=['TotalDiscountedCost','CapitalInvestment','DiscountedCapitalInvestment','NumberOfNewTechnologyUnits','SalvageValueStorage','Trade']#This provides an option for dropping these values because we know they are causing problems if we set their values for calculated: True. By default we will not drop any of these values, but if we want to we can add them to this list.

    # #drop these keys from the results keys list
    # results_sheets_new = [sheet for sheet in results_sheets if sheet not in sheets_to_ignore]

    post_processing_functions.save_results_as_excel(paths_dict, config_dict,sheets_to_ignore_if_error_thrown)

    print("\nTime taken for save_results_as_excel: {}\n########################\n ".format(time.time()-start))
    start = time.time()

    post_processing_functions.save_results_as_long_csv(paths_dict,config_dict,sheets_to_ignore_if_error_thrown)
    print("\nTime taken for save_results_as_long_csv: {}\n########################\n ".format(time.time()-start))


    start = time.time()
    #Visualisation:
    post_processing_functions.create_res_visualisation(paths_dict,config_dict)
    print("\nTime taken for create_res_visualisation: {}\n########################\n ".format(time.time()-start))

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
    input_data_sheet_file="data-sheet-power_36TS.xlsx"#set this based on the data sheet you want to run if you are running this from jupyter notebook
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

