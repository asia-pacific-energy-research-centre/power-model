
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

def prepare_solving_process(root_dir, config_dir,  tmp_directory, economy, scenario,osemosys_model_script='osemosys_fast.txt'):
    #start time
    start = time.time()
    # We first make a copy of osemosys_fast.txt so that we can modify where the results are written.
    # Results from OSeMOSYS come in csv files. We first save these to the tmp directory for each economy.
    # making a copy of the model file in the tmp directory so it can be modified

    print(f'\n######################## \n Running solve process using{osemosys_model_script}')

    osemosys_model_script_path = f'{root_dir}/{config_dir}/{osemosys_model_script}'

    model_file_path = f'{tmp_directory}/model_{economy}_{scenario}.txt'

    with open(osemosys_model_script_path) as t:
        model_text = t.read()
    f = open(model_file_path,'w')
    f.write('%s\n'% model_text)
    f.close()

    # Read in the file again to modify it
    with open(model_file_path, 'r') as file:
        filedata = file.read()
    # Replace the target string
    filedata = filedata.replace("param ResultsPath, symbolic default 'results';",f"param ResultsPath, symbolic default '{tmp_directory}';")
    # Write the file out again
    with open(model_file_path, 'w') as file:
        file.write(filedata)

    #create path to save copy of outputs to txt file in case of error:
    log_file_path = f'{tmp_directory}/process_output_{economy}_{scenario}.txt'

    cbc_intermediate_data_file_path = '{tmp_directory}/cbc_input_{economy}_{scenario}.lp'
    cbc_results_data_file_path='{tmp_directory}/cbc_results_{economy}_{scenario}.txt'

    print("\nTime taken: {}\n########################\n ".format(time.time()-start))

    return osemosys_model_script_path,model_file_path,log_file_path,cbc_intermediate_data_file_path,cbc_results_data_file_path

def solve_model(solving_method, tmp_directory, path_to_results_config,log_file_path,model_file_path,path_to_input_data_file,cbc_intermediate_data_file_path,cbc_results_data_file_path):
        
    #save copy of outputs to txt file in case of error:
    log_file = open(log_file_path,'w')

    #previous solving method:
    if solving_method == 'glpsol':
        command =f"glpsol -d {path_to_input_data_file} -m {model_file_path}"
        result = subprocess.run(command,shell=True, capture_output=True, text=True)

        print(command+'\n')
        print(result.stdout+'\n')
        print(result.stderr+'\n')
        print("Time taken: {} for glpsol\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))

    if solving_method == 'coin-cbc':
        #new solving method (faster apparently):
        #start new timer to time the solving process
        start = time.time()
        command=f"glpsol -d {path_to_input_data_file} -m {model_file_path} --wlp {cbc_intermediate_data_file_path}"
        #create a lp file to input into cbc
        result = subprocess.run(command,shell=True, capture_output=True, text=True)
        print("\n Printing command line output from converting to lp file \n")
        print(command+'\n')
        print(result.stdout+'\n')
        print(result.stderr+'\n')
        print("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting to lp file \n\n########################\n ".format(time.time()-start))

        #input into cbc solver:
        command= f"cbc {cbc_intermediate_data_file_path} solve solu {cbc_results_data_file_path}"
        start = time.time()
        result = subprocess.run(command,shell=True, capture_output=True, text=True)
        
        print("\n Printing command line output from CBC solver \n")
        print(command+'\n')
        print(result.stdout+'\n')
        print(result.stderr+'\n')
        print("\n Time taken: {} for CBC solver \n\n########################\n ".format(time.time()-start))
        #save stdout and err to file
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for CBC solver \n\n########################\n ".format(time.time()-start))

        #convert to csv
        command = f"otoole results cbc csv {cbc_results_data_file_path} {tmp_directory} {path_to_results_config}"
        start = time.time()
        result = subprocess.run(command,shell=True, capture_output=True, text=True)

        print("\n Printing command line output from converting cbc output to csv \n")#results_cbc_{economy}_{scenario}.txt
        print(command+'\n')
        print(result.stdout+'\n')
        print(result.stderr+'\n')
        print('\n Time taken: {} for converting cbc output to csv \n\n########################\n '.format(time.time()-start))
        #save stdout and err to log_file
        log_file.write(command+'\n')
        log_file.write(result.stdout+'\n')
        log_file.write(result.stderr+'\n')
        #save time taken to log_file
        log_file.write("\n Time taken: {} for converting cbc output to csv \n\n########################\n ".format(time.time()-start))


    #close log_file
    log_file.close()

    return
    

