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
extract_osemosys_cloud_results_using_otoole = False#False is the default, but if you want to use otoole to extract the results, set this to True
################################################################################

def main(input_data_sheet_file, data_config_file, osemosys_cloud, solving_method):

    # get the time you started the model so the results will have the time in the filename
    model_start = time.strftime("%Y-%m-%d-%H%M%S")

    print(f"Script started at {model_start}...\n")

    ################################################################################
    #PREPARE DATA
    ################################################################################

    #prep functions:
    config_dict, economy, scenario, model_end_year = model_preparation_functions.import_run_preferences(root_dir, input_data_sheet_file)
    # model_end_year = 2023#uncomment this to override the model end year in the excel file
    # economy = '19_THA'
    # scenario = 'Reference'
    paths_dict = model_preparation_functions.set_up_paths(scenario, economy, root_dir, config_dir ,data_config_file, input_data_sheet_file,osemosys_model_script,osemosys_cloud,FILE_DATE_ID)
    results_sheets, data_config, data_config_short_names = model_preparation_functions.import_data_config(paths_dict,osemosys_cloud)


    #depdning on whether we are running on osemosys cloud or not, we will run differtent functions:
    osemosys_cloud_input = None
    if osemosys_cloud:
        prompt = f"Have you put the zip files from osemosys-cloud.com into {paths_dict['tmp_directory']} (y/n): "
        osemosys_cloud_input = input(prompt).lower()
        if osemosys_cloud_input == 'y':
            print("Great, let's continue")
        

    if not osemosys_cloud or osemosys_cloud_input == 'n':
        #start timer
        start = time.time()

        model_preparation_functions.write_model_run_specs_to_file(paths_dict, scenario, economy, model_end_year, osemosys_cloud, FILE_DATE_ID,solving_method)

        start2 = time.time()
        input_data = model_preparation_functions.extract_input_data(data_config_short_names,paths_dict,model_end_year,economy,scenario)
        print("\nTime taken to extract input data: {}\n########################\n ".format(time.time()-start2))

        model_preparation_functions.write_data_to_temp_workbook(paths_dict, input_data)

        model_preparation_functions.prepare_data_for_osemosys(paths_dict,data_config)

        model_preparation_functions.prepare_model_script_for_osemosys(paths_dict, osemosys_cloud)

        start2 = time.time()
        model_preparation_functions.validate_input_data(paths_dict)# todo: mnake this this function work by creating the data vaildation yaml file.
        print("\nTime taken to validate data: {}\n########################\n ".format(time.time()-start2))

        print("\nTotal time taken for preparation: {}\n########################\n ".format(time.time()-start))



    ################################################################################
    #SOLVE MODEL
    ################################################################################

    if not osemosys_cloud:
        #start new timer to time the solving process
        start = time.time()

        #open log file in case of error:|
        log_file = open(paths_dict['log_file_path'],'w')

        log_file = model_solving_functions.solve_model(solving_method,log_file,paths_dict)
        print(f'\n######################## \n Running solve process using{osemosys_model_script} for {solving_method} {economy} {scenario}')
        print("Time taken for solve_model: {}\n########################\n ".format(time.time()-start))

        log_file.close()


    ################################################################################
    #Post processing
    ################################################################################
    #start new timer to tiome the post-processing
    start = time.time()

    #if osemosys cloud is true then do this to extract results form the zip files you get from the cloud
    if osemosys_cloud:
        if osemosys_cloud_input == 'y':
            if extract_osemosys_cloud_results_using_otoole:
                post_processing_functions.extract_osmosys_cloud_results_txt_to_csv(paths_dict)
                #to do why does this only extract a few of the files we want to extract? i expect its a problem related to the general way we extract results, even with non cloud results.
            else:
                post_processing_functions.aggregate_and_edit_osemosys_cloud_csvs(paths_dict, data_config, results_sheets)
        else:
            print('Please put the zip files from osemosys-cloud.com into the tmp directory and then run the code again')
            sys.exit()


    post_processing_functions.remove_apostrophes_from_region_names(paths_dict, osemosys_cloud, results_sheets, data_config)


    sheets_to_ignore_if_error_thrown=['TotalDiscountedCost','CapitalInvestment','DiscountedCapitalInvestment','NumberOfNewTechnologyUnits','SalvageValueStorage','Trade']#This provides an option for dropping these values because we know they are causing problems if we set their values for calculated: True. By default we will not drop any of these values, but if we want to we can add them to this list.

    # #drop these keys from the results keys list
    # results_sheets_new = [sheet for sheet in results_sheets if sheet not in sheets_to_ignore]

    post_processing_functions.save_results_as_excel(paths_dict, scenario, results_sheets, data_config,sheets_to_ignore_if_error_thrown)

    print("\nTime taken for save_results_as_excel: {}\n########################\n ".format(time.time()-start))
    start = time.time()

    post_processing_functions.save_results_as_long_csv(paths_dict,results_sheets,sheets_to_ignore_if_error_thrown)
    print("\nTime taken for save_results_as_long_csv: {}\n########################\n ".format(time.time()-start))


    start = time.time()
    #Visualisation:
    post_processing_functions.create_res_visualisation(paths_dict,scenario,economy)
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
    input_data_sheet_file="data-sheet-power-24ts.xlsx"#set this based on the data sheet you want to run if you are running this from jupyter notebook
    data_config_file ="config.yaml"
    osemosys_cloud = True
    solving_method = 'coin-cbc'#or glpsol
    #make directory the root of the project
    if os.getcwd().split('\\')[-1] == 'src':
        os.chdir('..')
        print("Changed directory to root of project")
    
    main(input_data_sheet_file, data_config_file, osemosys_cloud, solving_method)

elif __name__ == '__main__':

    if len(sys.argv) != 5:
        msg = "Usage: python {} <input_data_sheet_file> <data_config_file> <osemosys_cloud> <solving_method>"
        print(msg.format(sys.argv[0]))
        sys.exit(1)
    else:
        input_data_sheet_file = sys.argv[1]
        data_config_file = sys.argv[2]
        osemosys_cloud = sys.argv[3]
        solving_method = sys.argv[4]
        main(input_data_sheet_file, data_config_file, osemosys_cloud, solving_method)
# %%

