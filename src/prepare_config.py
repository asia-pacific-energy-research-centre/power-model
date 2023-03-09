#aim to make sure the config file is what we expect it to be

#first load in the config file used in otooles github as it is a good guide:
#%%
import yaml
import pandas as pd

otoole_config = yaml.load(open('../config/otoole_config.yml'), Loader=yaml.FullLoader)

#now load in the config files we are using:
data_config = yaml.load(open('../config/data_config_copy.yml'), Loader=yaml.FullLoader)
results_config = yaml.load(open('../config/results_config_copy_test.yml'), Loader=yaml.FullLoader)

#%%
#we want to separate keys in otoole_config that have type='result'. 
otoole_results_keys = [key for key in otoole_config.keys() if otoole_config[key]['type'] == 'result']
other_keys = [key for key in otoole_config.keys() if otoole_config[key]['type'] != 'result']

#also find keys that are in results config and have type='result'
results_config_keys = [key for key in results_config.keys() if results_config[key]['type'] == 'result']

#%%
#take in main_results_config and check their keys compared to otoole_results_keys
main_results_config = yaml.load(open('../config/main_results_config.yml'), Loader=yaml.FullLoader)
main_results_config_keys = [key for key in main_results_config.keys()]
similar_keys_to_main = [key for key in otoole_results_keys if key in main_results_config_keys]

#%%
#find the similar keys between the two:
similar_keys = [key for key in otoole_results_keys if key in results_config_keys]
#find the keys that are in otoole_results_keys but not in results_config_keys
missing_keys = [key for key in otoole_results_keys if key not in results_config_keys]
#find the keys that are in results_config_keys but not in otoole_results_keys
extra_keys = [key for key in results_config_keys if key not in otoole_results_keys]

#%%


#take in main config and change some things
main_data_config = yaml.load(open('../config/main_data_config.yml'), Loader=yaml.FullLoader)
#where short_name is None, then remove the key
for key in main_data_config.keys():
    if 'short_name' in main_data_config[key].keys():
        if main_data_config[key]['short_name'] == 'None':
            del main_data_config[key]['short_name']
        
#save the new main_data_config 
with open('../config/main_data_config.yml', 'w') as file:
    documents = yaml.dump(main_data_config, file)



# %%
