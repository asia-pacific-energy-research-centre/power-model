# power-model

These files are for running the power model (OSeMOSYS).

## 1. Get set up first
The recommended way to get these files on your computer is to clone using Git:

`git clone https://github.com/asia-pacific-energy-research-centre/power-model.git`

Make sure you run this command in the folder you want.

You need to create a conda environment. To install, move to your working directory and copy and paste the following in your command line:

`conda env create --prefix ./env --file ./config/environment.yml`

`conda activate ./env`

## 2. To run the model 
Make sure you did Step 1 (only need to do it once).

1. Make sure you are in the working directory:
    In the command prompt you can check with `pwd`

2. Edit the data input sheet. Configure your model run using the START tab. Leave `Config file` and `Solver` as `data_config_all_calculated.yaml` and `coin_mip` if you are unsure. They should be what you use 99% of the time anyway.

3. Run the model by typing in `python ./src/main.py <input_data_sheet_file>"
    a. where <input_data_sheet_file> is the name of the input data sheet file in ./data (e.g., data.xlsx)
    b. For example, `python ./src/main.py data.xlsx` is the command to run the model with the data in data.xlsx
    c. You can also add `> output.txt 2>&1` to save the complete output to a text file. For example, `python ./src/main.py data.xlsx > output.txt 2>&1`. This will print a lot of stuff, so the file could become quite large. If you want to just see the most important outputs, the `tmp/ECONOMY/SCENARIO/process_log_ECONOMY_SCENARIO_FILEDATEID.txt` is useful.

4. The model will run. You can take a look at the input and intermediate data in the `tmp/ECONOMY/SCENARIO/` folder. There will be results in the `results/ECONOMY/SCENARIO` folder and visualisations in the `visualisations/ECONOMY_SCENARIO` folder.

## 3. Debugging model runs
When the script runs, the following temporary files are saved in `./tmp/ECONOMY NAME/SCENARIO`:
- combined_data_ECONOMYNAME_SCENARIO.xlsx
- datafile_from_python_ECONOMYNAME_SCENARIO.txt
- model_ECONOMYNAME_SCENARIO.txt
- process_log_ECONOMY_SCENARIO_FILEDATEID.txt
- specs_FILEDATEID.txt
- ECONOMYNAME_SCENARIO_config.yaml
The above files are created before OSeMOSYS runs. If you notice that OSeMOSYS gives you an error, check these files. 

If the model solves successfully, a bunch of CSV files will be written to the same tmp folder. These are then combined and saved in the `results` folder as Excel files. 

If there is an error message saying the model is infeasible, check your model data. You can also double check the process_log_{economy}_{scenario}.txt file for outputs from the solving process. If the model is infeasible, the results files will not be written and you will get a "file not found" error message or something. This is your clue that the model did not solve. You always want to see a message in the solver output saying "OPTIMAL LP SOLUTION FOUND".

## 4. Adding results to config yml files
To add results (e.g., capacity factor) you need to edit the following files:
- osemosys.txt
- XYZ_config.yaml

The `osemosys_fast.txt` file is where the calculations occur. Following the pattern from the other results. The `results_config.yml` file tells the script to include that result and add it to the combined results Excel file.

## 5. Using results
Saved in the results folder will be a few different files. The ones with name ~ tall_...xlsx, will be a combination of all the results in one csv. 

Also, if you have set the variable SAVE_RESULTS_VIS_AND_INPUTS to True in the main.py file, then you will also have a folder in results/ with the FILEDATEID and some general settings in it's name (i.e. /2023-04-11-134916_19_THA_Reference_coin_mip/) which will contain all the resutls, input, intermediate and visualisation files. This can be useful for debugging and testing.

### Extras: 
## Creating visualisation of RES
You can create a visualisaton of the RES as stated within the config/config.yml files. The script to run this will be outputted at the end of each model run, but you will need to run it in command line yourself.

## Avoiding errors when running the system:
I have included a few checks to make sure things in the input data are as they should be, however it is hard to cover for all of the possible ones, and a bit of a waste of time to cover for ones which will eventually be caught by otoole/cbc/osemosys. So if you find some error you dont expect take a look below:

### Validation:
https://otoole.readthedocs.io/en/latest/functionality.html#otoole-validate - to do when they develop its capacity a bit more. It would help to prevent possible bugs from changes to the config and input data.