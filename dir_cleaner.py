#!/usr/bin/env python 
import sys
import os
series_name=' '.join(sys.argv[1:])
from shutil import move
import tmdbsimple as tmdb
import re

#todo- Clean up code, duh
#Create offline mode, or method for handling when lookup fails (manual year entry?)
#Make OOP, maybe extend to a "library" level, so can autoupdate all? 
# Maybe create logs of changes made, for the ability to undo. (also a list of all source directories would help
# with the next idea)
#Remove (relatively) empty folders after moving the videos out. (directories containing only .nfo, .txt,.exe?)

#Open Issues
# the title subset problem, when one title exists in another (Angel vs Touched by an Angel)
# What if a file is missing the s##e## string, or if it has two of them?
# Does it no longer look for files in top level directory?


#Remove if uploading to github
def name_parser(name):return replace_all(name.lower(),{"'":'',".":" ","-":' ',':':'',',':'','_':' '})
def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text
# def get_file_names(directory='.'):
#     return [x.name for x in os.scandir(directory) if x.is_file() and x.name[-3:] in video_file_types]
def make_parsed_file_dict(directory='.'):
    #Finds video files in directory, parses the file names
    video_file_types=['mkv','mp4','avi','m4v']
    files=[x.name for x in os.scandir(directory) if x.is_file() and x.name[-3:] in video_file_types]
    return { x:name_parser(x) for x in files}
def make_parsed_directory_dict(directory='.'):

    directories=[x.name for x in os.scandir(directory) if x.is_dir()]
    return { x:name_parser(x) for x in directories}
def copy_files_to(directory,parsed_show_name,series_name_full):
    parsed_file_dict=make_parsed_file_dict(directory)
    for file in parsed_file_dict:
        if parsed_show_name in parsed_file_dict[file]:
            move('./'+directory+'./'+file, './'+series_name_full+'./'+file)
def clean_names(directory,parsed_show_name,series_name_full):
    parsed_file_dict=make_parsed_file_dict(directory)
    for file in parsed_file_dict:
        if parsed_show_name in parsed_file_dict[file]:
            #Need to handle when the year is after the show name (the convention used when there are multiple shows with the same name)
            try:se_string=re.findall('[s]\d\d[e]\d\d', parsed_file_dict[file])[0]
            except:
                #if format was s##.e## (as I have used), the period will be space
                se_string=re.findall('[s]\d\d.[e]\d\d', parsed_file_dict[file])[0].replace(' ','')

            new_file_name=series_name_full+' '+se_string+file[-4:]
            #rename file
            try:
                if file!=new_file_name:
                    os.rename(directory+'/'+file,directory+'/'+new_file_name)
                    print(new_file_name)
            except:print(f'failed to rename {file}')
            

tmdb.API_KEY = os.environ['tvdb_api']

on_line=1

"""
Reno 911 failed. Special character in official name, Reno 911!, but not in file name. 
maybe remove special characters from the downloaded names?
"""

#Offline option?
if on_line:
    search = tmdb.Search()
    #print(1)
    response = search.tv(query=series_name)
    #print(2)
    if len(search.results)==0:
        print('Series Not Found')
        sys.exit("Program Quit")
    #Maybe only run if multiple results? Start assuming the 0th?
    for i,s in enumerate(search.results):
        try:print(f"{i} |title: {s['name']}, aired: {s['first_air_date']}, overview:{s['overview']}")
        except:print(f"{i} |title: {s['name']}, overview:{s['overview']}")
    print('select entry # (or q to quit)')
    series_selected=input()
    try:
        series_result=search.results[int(series_selected)]
    except:sys.exit("Program Quit")
    parsed_show_name=name_parser(series_result['name'])
    series_year=series_result['first_air_date'][:4]
    series_name_full=f"{series_result['name']} ({series_year})"
else:
    parsed_show_name=name_parser(series_name)
    print('year')
    series_year=input()
    series_name_full=f"{series_name} ({series_year})"
    
series_name_full=series_name_full.replace(':','-')
#print(parsed_show_name)
#make
#try: 
if series_name_full not in make_parsed_directory_dict():os.mkdir(series_name_full)
#except:pass
#search for episodes in current folders

parsed_directories_dict=make_parsed_directory_dict()

#sys.exit("Program Quit 1")

#search for folders containing episodes. Note that this does not look for folders in folders, just file in folders
for directory in parsed_directories_dict:
    if (parsed_show_name in parsed_directories_dict[directory] and 
        series_name_full!=parsed_directories_dict[directory]):copy_files_to(directory,parsed_show_name,series_name_full)
#Look in 
parsed_directories_dict=make_parsed_directory_dict('./'+series_name_full)
for directory in parsed_directories_dict:
    if (parsed_show_name in parsed_directories_dict[directory] and 
        parsed_show_name!=parsed_directories_dict[directory]):copy_files_to('./'+series_name_full+'/'+directory,parsed_show_name,series_name_full)
#clean names
#
clean_names('./'+series_name_full,parsed_show_name,series_name_full)



class TV_Series():
    pass
