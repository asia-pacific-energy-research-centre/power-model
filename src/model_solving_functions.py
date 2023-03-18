
#%%

import os
import time
import subprocess

#make directory the root of the project
if os.getcwd().split('\\')[-1] == 'src':
    os.chdir('..')
    print("Changed directory to root of project")

#%%

################################################################################
#SOLVE MODEL
#Pull in the prepared data file and solve the model
################################################################################

def solve_model(solving_method,log_file,paths_dict):
    """Use subprocess to run the model file in the tmp directory. This is done using the command line. The methods used in the command line are mostly detailed in https://otoole.readthedocs.io/en/latest/functionality.html . The results are saved in the tmp directory for the economy and scenario we are running the model for. They will be processed after this function"""
    #create path variables
    tmp_directory = paths_dict['tmp_directory']
    path_to_data_config = paths_dict['path_to_data_config']
    model_file_path = paths_dict['new_osemosys_model_script_path']
    old_model_file_path = paths_dict['osemosys_model_script_path']
    path_to_input_data_file = paths_dict['path_to_input_data_file']
    cbc_intermediate_data_file_path = paths_dict['cbc_intermediate_data_file_path']
    cbc_results_data_file_path = paths_dict['cbc_results_data_file_path']


    #previous solving method:
    if solving_method == 'glpsol':
        start = time.time()
        command =f"glpsol -d {path_to_input_data_file} -m {model_file_path}"
        result = subprocess.run(command,shell=True, capture_output=True, text=True)
        print("\n Printing command line input from glpsol \n")
        print(command+'\n')
        # print(result.stdout+'\n')
        # print(result.stderr+'\n')
        print("Time taken: {} for glpsol\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write("\n Printing command line output from glpsol \n")
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))

    if solving_method == 'coin':
        #new solving method (much faster):
        #start new timer to time the solving process
        start = time.time()
        command=f"glpsol -d {path_to_input_data_file} -m {model_file_path} --wlp {cbc_intermediate_data_file_path} --check"
        #create a lp file to input into cbc
        result = subprocess.run(command,shell=True, capture_output=True, text=True)
        print("\n Printing command line input from converting to lp file \n")
        print(command+'\n')
        # print(result.stdout+'\n')
        # print(result.stderr+'\n')
        print("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write("\n Printing command line output from converting to lp file \n")
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))

        #input into cbc solver:
        command= f"cbc {cbc_intermediate_data_file_path} solve solu {cbc_results_data_file_path}"
        start = time.time()
        result = subprocess.run(command,shell=True, capture_output=True, text=True)
        
        print("\n Printing command line input from CBC solver \n")
        print(command+'\n')
        # print(result.stdout+'\n')
        # print(result.stderr+'\n')
        print("\n Time taken: {} for CBC solver \n\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write("\n Printing command line output from CBC solver \n")
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for CBC solver \n\n########################\n ".format(time.time()-start))

        #convert to csv
        #check if old_model_file_path contains osemosys_fast.txt, if so we need to include the input data file.txt in the call, with --input_datafile.
        if 'osemosys_fast.txt' in old_model_file_path:
            #we have to include the input data file.txt in the call, with --input_datafile. 
            command = f"otoole results --input_datafile {path_to_input_data_file} cbc csv {cbc_results_data_file_path} {tmp_directory} {path_to_data_config}"
        elif 'osemosys.txt' in old_model_file_path:
            command = f"otoole results cbc csv {cbc_results_data_file_path} {tmp_directory} {path_to_data_config}"
        else:
            raise ValueError('The model file path does not contain osemosys.txt or osemosys_fast.txt. Please check the model file path and try again')
        
        start = time.time()
        result = subprocess.run(command,shell=True, capture_output=True, text=True)

        print("\n Printing command line input from converting cbc output to csv \n")#results_cbc_{economy}_{scenario}.txt
        print(command+'\n')
        # print(result.stdout+'\n')
        # print(result.stderr+'\n')
        # print('\n Time taken: {} for converting cbc output to csv \n\n########################\n '.format(time.time()-start))
        #save stdout and err to log_file
        log_file.write("\n Printing command line output from converting cbc output to csv \n")#results_cbc_{economy}_{scenario}.txt
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting cbc output to csv \n\n########################\n ".format(time.time()-start))
    return log_file
    

