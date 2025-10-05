
## Documenting your configuration parameters

In order to get configuration parameters you can modify, execute:

    python detect_function_calls.py  rester/ get_config_ --exclude get_config_location

Every configuration parameter can be changed in configuration file and overwritten by using 
environment variable. 

For instance, `url` can be specified in configuration file and can be modified using `RESTER_URL` environment variable.

Configuration file is specified using `RESTER_CONFIG` and default location is at `~/.config/rester.json`
