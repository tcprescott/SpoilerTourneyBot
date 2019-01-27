import yaml
import sys

def get_config():
    try:
        with open("cfg/config.yaml") as configfile:
            try:
                return yaml.load(configfile)
            except yaml.YAMLError as e:
                print(e)
                sys.exit(1)
    except FileNotFoundError:
        print('cfg/config.yaml does not exist!')
        sys.exit(1)