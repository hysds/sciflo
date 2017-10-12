#!/bin/bash
#
# dump out Date: line for every dubov site file

find ~/data_aeronet_dubov/data/raw -type f | xargs grep -h ^Date > check_field.txt
