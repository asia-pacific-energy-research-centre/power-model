# power-model

These files are for running the power model (OSeMOSYS).

## 1. Get set up first
The recommended way to get these files on your computer is to clone using Git:

`git clone https://github.com/asia-pacific-energy-research-centre/power-model.git`

Make sure you run this command in the folder you want.

You need to create a conda environment. To install, move to your working directory and copy and paste the following in your command line:

`conda env create --prefix ./env --file ./config/env.yml`

Install otoole. Activate your environment before installing otoole!!

`conda activate ./env`

`pip install otoole`

# Installing coin cbc solver
This will help to run the model faster. However it's installation is a little tricky. Go to the word document in ./documentation/ called "Installing CBC solver.docx" and follow the instructions. If you dont use this you will need to set 'use_coincbc' to False in the main.py file, and use use_glpsol to True.

## 2. To run the model 
Make sure you did Step 1 (only need to do it once).

1. Make sure you are in the working directory:
    In the command prompt you can check with `pwd`

2. Edit the data input sheet. Configure your model run using the START tab.

3. Run the model by typing in `python ./src/main.py`

4. The model will run. Pay attention to the OSeMOSYS statements. There should not be any issues with the python script.

## 3. Debugging model runs
When the script runs, the following temporary files are saved in `./tmp/ECONOMY NAME/SCENARIO`:
- combined_data_ECONOMYNAME_SCENARIO.xlsx
- datafile_from_python_ECONOMYNAME_SCENARIO.txt
- model_ECONOMYNAME_SCENARIO.txt
- process_log_{economy}_{scenario}.txt
The above files are created before OSeMOSYS runs. If you notice that OSeMOSYS gives you an error, check these files. The combined data Excel file is easy to check. You can see if there is missing data, typos, etc. This Excel file is converted to the text version (datafile_from_python). Finally, check the model text file. This is the file with sets, parameters, and equations that contains the OSeMOSYS model.

If the model solves successfully, a bunch of CSV files will be written to the same tmp folder. These are then combined and saved in the `results` folder as an Excel file.

If there is an error message saying the model is infeasible, check your model data. You can also double check the process_log_{economy}_{scenario}.txt file for outputs from the solving process. If the model is infeasible, the results files will not be written and you will get a "file not found" error message. This is your clue that the model did not solve. You always want to see a message in the solver output saying "OPTIMAL LP SOLUTION FOUND".

## Running OsEMOSYS CLOUD
It may be better to use OsEMOSYS CLOUD. In this case refer to the ./documentation/Running_osemosys_cloud.docx file for instructions.

## 4. Adding results
To add results (e.g., capacity factor) you need to edit the following files:
- osemosys_fast.txt
- results_config.yml

The `osemosys_fast.txt` file is where the calculations occur. Following the pattern from the other results. The `results_config.yml` file tells the script to include that result and add it to the combined results Excel file.

## 5. Using results
Saved in the results folder will be a few different files. The ones with name ~ tall_...xlsx, will be a combination of all the results.

## Creating visualisation of RES
You can create a visualisaton of the RES as stated within the config/config.yml files. The script to run this will be outputted at the end of each model run, but you will need to run it in command line yourself.

## Common errors:
3/14/2023: Used 
    glpsol -m ./config/osemosys.txt -d ./config/simplicity.txt 
and got the error:
    E:/APERC/power-model/env/Library/bin/glpsol.exe: error while loading shared libraries: ucrtbased.dll: cannot open shared object file: No such file or directory
It seems that this is because conda install glpk installs glpk on the computer you are using. But if you are using a usb drive to hold your work then you may need to run conda install glpk on the computer you are using. This will install glpk on the computer you are using, and then you can run the model, I think.