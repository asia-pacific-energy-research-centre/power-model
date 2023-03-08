# power-model

These files are for running the power model (OSeMOSYS).

## 1. Get set up first
The recommended way to get these files on your computer is to clone using Git:

`git clone https://github.com/asia-pacific-energy-research-centre/power-model.git`

Make sure you run this command in the folder you want.

You need to create a conda environment. To install, move to your working directory and copy and paste the following in your command line:

`conda create --prefix ./env python=3.9 pandas numpy xlrd glpk`

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
When the script runs, the following temporary files are saved in `./tmp/ECONOMY NAME`:
- combined_data_ECONOMYNAME.xlsx
- datafile_from_python_ECONOMYNAME.txt
- model_ECONOMYNAME.txt

The above files are created before OSeMOSYS runs. If you notice that OSeMOSYS gives you an error, check these files. The combined data Excel file is easy to check. You can see if there is missing data, typos, etc. This Excel file is converted to the text version (datafile_from_python). Finally, check the model text file. This is the file with sets, parameters, and equations that contains the OSeMOSYS model.

If the model solves successfully, a bunch of CSV files will be written to the same tmp folder. These are then combined and saved in the `results` folder as an Excel file.

If there is an error message saying the model is infeasible, check your model data. If the model is infeasible, the results files will not be written and you will get a "file not found" error message. This is your clue that the model did not solve. You always want to see a message in the solver output saying "OPTIMAL LP SOLUTION FOUND".

## 4. Adding results
To add results (e.g., capacity factor) you need to edit the following files:
- osemosys_fast.txt
- results_config.yml

The `osemosys_fast.txt` file is where the calculations occur. Following the pattern from the other results. The `results_config.yml` file tells the script to include that result and add it to the combined results Excel file.




