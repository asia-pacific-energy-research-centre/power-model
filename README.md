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

Install cbc solver by following instructions below:

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

## Testing using simplicity.txt
You can test the model using the OSeMOSYS simplicity.txt setup in this repo. This may be useful for testing any changes made. It also helps to understand the most basic functionality of this repo (excluding the process of cleaning and converting data from a excel data sheet to an osemosys input). You can use the following code for glpsol:

```bash
conda activate ./env

# Create the GNUMathProg data file with otoole
otoole convert csv datafile ./data/simplicity/data ./data/simplicity/simplicity.txt ./data/simplicity/config.yaml

# Solve the model
glpsol -m ./data/simplicity/OSeMOSYS.txt -d ./data/simplicity/simplicity.txt
```

And for the coin-cbc solver:

```bash
# converting to lp file 
glpsol -d ./data/simplicity/simplicity.txt -m ./data/simplicity/OSeMOSYS.txt --wlp ./data/simplicity/simplicity.lp --check

# CBC solver 
cbc ./data/simplicity/simplicity.lp solve solu ./data/simplicity/simplicity.sol

# converting cbc output to csv 
otoole results --input_datafile ./data/simplicity/simplicity.txt cbc csv ./data/simplicity/simplicity.sol ./tmp/simplicity ./data/simplicity/config.yaml
```

## Avoiding errors when running the system:
I have included a few checks to make sure things in the input data are as they should be, however it is hard to cover for all of the possible ones, and a bit of a waste of time to cover for ones which will eventually be caught by otoole/cbc/osemosys. So if you find some error you dont expect take a look below:

### Known issues:
 - AttributeError: Can only use .str accessor with string values!
    - this seems to happen when running the model using coin-cbc and the osemosys.txt model. It occurs in the osemosys results call of model_solving_fuctions.solve_model(). I cannot work out why it occurs but i haven't tried very hard, because it doesnt seem to occur with osemosys_fast.txt.
 - Primal infs and other infs when running cbc solve.
    - perhaps these also occur with glpsol. I expect this is because of bad input data, i.e. the numbers being unrealistic, but its hard to tell since there are a lot of inputs. 
 - Something like EmissionActivityRatio['19_THA',POW_1_x_coal_thermal,1,'1_x_coal_thermal_CO2',2017] MathProg model processing error:
    - i fixed this one by changing the indices for EmissionActivityRatio from [REGION,TECHNOLOGY,MODE_OF_OPERATION,EMISSION,YEAR] to [REGION,TECHNOLOGY,EMISSION,MODE_OF_OPERATION,YEAR] in the config file. It seems this is because that is the order they are stated in osemosys.txt/osemosys_fast.txt (the model file)
 - blank output csvs
    - i cant tell for sure why this is but i think its related to the primal infs issue and can also happen if the supplied input data for calculating the variable for that sheet are not available, i.e. not supplied. 
 - SystemExit Errors. 
    - These should be occuring because of some check i have introduced to the code to make sure the input data is closer to what it should be for the model.
 - ./power-model/env/Library/bin/cbc.exe: error while loading shared libraries: ucrtbased.dll: cannot open shared object file: No such file or directory
    - This is a windows error. It doesnt occur on my home computer so i expect it is to do with the APERC laptops. I've tried a few things but no success. If this happens then you can try running the model using glpsol (is much slower), or you can try running the model on your own computer, or perhaps the OSeMOSYS CLOUD solution.
 
### What can you do to avoid errors in the first place:
 - When introducing new paramaters to the model, check they arent already stated in the osemosys_official_config.yaml as this should contain every variable calcualted or used in the osemosys.txt model file. That way you can make sure you dont make any annoying mistakes like misordering indices, supplying the wrong values etc. 
 - If you are introducing something that isnt even in the model file then you're kind of on your own but someone who knows code might be able to help. 
  - When removing variables from the config.yaml file be aware that this could affect other varaibles if they are calculated using them or so on. 

### Validation:
https://otoole.readthedocs.io/en/latest/functionality.html#otoole-validate