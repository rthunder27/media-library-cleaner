#!/usr/bin/env python 
import sys
import os
import argparse
from shutil import move
import tmdbsimple as tmdb
import re
from datetime import datetime

arg_parser=argparse.ArgumentParser(
    description='Looks up a TV series, creates a "Series Name (Year)" folder in the current\n'
                'directory, and moves/renames matching video files (mkv/mp4/avi/m4v) into it\n'
                'as "Series Name (Year) sXXeXX.ext".\n'
                '\n'
                'Run it from the directory containing the show\'s files/folders -- it shows\n'
                'the planned moves and renames before making them, then (in online mode)\n'
                'prompts you to pick the matching series from TMDB search results.',
    epilog='examples:\n'
           '  python dir_cleaner.py The Office\n'
           '  python dir_cleaner.py --offline The Office               (prompts for the year)\n'
           '  python dir_cleaner.py --offline --year 2005 The Office\n'
           '  python dir_cleaner.py --offline --year "" The Office     (no year in folder/file names)\n'
           '\n'
           'Online mode (the default) requires the tvdb_api environment variable to hold a TMDB API key.',
    formatter_class=argparse.RawDescriptionHelpFormatter)
arg_parser.add_argument('series_name',nargs='+',help='name of the TV series to search for/organize')
arg_parser.add_argument('--offline',action='store_true',help='skip the TMDB lookup; enter the show name and year manually')
arg_parser.add_argument('--year',help='year the series first aired (offline mode; prompted for if omitted, leave blank for no year)')
cli_args=arg_parser.parse_args()

series_name=' '.join(cli_args.series_name)
on_line=not cli_args.offline

#todo- Clean up code, duh
#Make OOP, maybe extend to a "library" level, so can autoupdate all?

#Open Issues
# the title subset problem, when one title exists in another (Angel vs Touched by an Angel)
# What if a file is missing the s##e## string, or if it has two of them?


#Remove if uploading to github
#Strip any remaining special characters (eg. the "!" in "Reno 911!") since they're typically dropped from downloaded file/folder names
def name_parser(name):return re.sub(r'[^a-z0-9 ]','',replace_all(name.lower(),{"'":'',".":" ","-":' ',':':'',',':'','_':' '}))
def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text
def is_show_match(parsed_show_name,parsed_candidate_name):
    #Anchors the match to the start of the candidate on a word boundary, eg. parsed_show_name "angel"
    #matches "angel s01e01" but not "touched by an angel s01e01" -- fixing the title-subset false
    #positive (Angel vs Touched by an Angel). Trade-off: this also misses names with something
    #prefixed before the title, eg. "[release group] angel s01e01". An alternative "loose" mode
    #could just do `parsed_show_name in parsed_candidate_name` to catch those prefixed cases, at
    #the cost of reintroducing the subset false positives -- could be exposed as a --loose-match flag.
    return parsed_candidate_name==parsed_show_name or parsed_candidate_name.startswith(parsed_show_name+' ')
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
def plan_moves(directory,parsed_show_name,series_name_full):
    #Returns [(source_path,destination_path),...] for video files that match the show and would move into series_name_full
    parsed_file_dict=make_parsed_file_dict(directory)
    return [(os.path.join(directory,file),os.path.join(series_name_full,file))
            for file in parsed_file_dict if is_show_match(parsed_show_name,parsed_file_dict[file])]
def apply_moves(moves):
    for source,destination in moves:
        move(source,destination)
def plan_renames(directory,parsed_show_name,series_name_full):
    #Returns [(old_name,new_name),...] for video files in directory that would be renamed to the standard format
    parsed_file_dict=make_parsed_file_dict(directory)
    renames=[]
    for file in parsed_file_dict:
        if is_show_match(parsed_show_name,parsed_file_dict[file]):
            #Need to handle when the year is after the show name (the convention used when there are multiple shows with the same name)
            try:se_string=re.findall('[s]\d\d[e]\d\d', parsed_file_dict[file])[0]
            except:
                #if format was s##.e## (as I have used), the period will be space
                se_string=re.findall('[s]\d\d.[e]\d\d', parsed_file_dict[file])[0].replace(' ','')

            new_file_name=series_name_full+' '+se_string+file[-4:]
            if file!=new_file_name:renames.append((file,new_file_name))
    return renames
def apply_renames(directory,renames):
    #Renames files, returning the (old_name,new_name) pairs that actually succeeded
    successful=[]
    for old_name,new_name in renames:
        try:
            os.rename(os.path.join(directory,old_name),os.path.join(directory,new_name))
            print(new_name)
            successful.append((old_name,new_name))
        except:print(f'failed to rename {old_name}')
    return successful
def print_plan(title,items):
    print(f'\n{title}:')
    if items:
        for source,destination in items:print(f'  {source}  ->  {destination}')
    else:print('  (nothing to do)')
def log_entries(directory,entries):
    #Appends timestamped entries to a hidden log file in directory, as a record of changes made (and a basis for a future undo command)
    if not entries:return
    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(os.path.join(directory,'.cleaner_log.txt'),'a') as log_file:
        for entry in entries:log_file.write(f'{timestamp}  {entry}\n')
def remove_empty_directories(directories,junk_extensions=('nfo','txt','exe')):
    #Removes any directory left containing nothing but junk files (eg. leftover .nfo/.txt/.exe) once its videos have moved out
    removed=[]
    for directory in directories:
        entries=list(os.scandir(directory))
        if all(entry.is_file() and entry.name.rsplit('.',1)[-1].lower() in junk_extensions for entry in entries):
            for entry in entries:os.remove(entry.path)
            os.rmdir(directory)
            removed.append(directory)
    return removed


if on_line:
    tmdb.API_KEY = os.environ['tvdb_api']

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
    series_year=cli_args.year
    if series_year is None:
        print('year (leave blank for no year)')
        series_year=input().strip()
    series_name_full=f"{series_name} ({series_year})" if series_year else series_name

series_name_full=series_name_full.replace(':','-')
#print(parsed_show_name)
#make
#try:
if series_name_full not in make_parsed_directory_dict():os.mkdir(series_name_full)
#except:pass
#search for episodes in current folders

parsed_directories_dict=make_parsed_directory_dict()

planned_moves=[]
source_directories=[]
#search for loose episode files sitting directly in the top level (current) directory
planned_moves+=plan_moves('.',parsed_show_name,series_name_full)
#search for folders containing episodes. Note that this does not look for folders in folders, just file in folders
for directory in parsed_directories_dict:
    if (is_show_match(parsed_show_name,parsed_directories_dict[directory]) and
        name_parser(series_name_full)!=parsed_directories_dict[directory]):
        planned_moves+=plan_moves(directory,parsed_show_name,series_name_full)
        source_directories.append(directory)
#Look in
parsed_directories_dict=make_parsed_directory_dict('./'+series_name_full)
for directory in parsed_directories_dict:
    if (is_show_match(parsed_show_name,parsed_directories_dict[directory]) and
        parsed_show_name!=parsed_directories_dict[directory]):
        source_directory='./'+series_name_full+'/'+directory
        planned_moves+=plan_moves(source_directory,parsed_show_name,series_name_full)
        source_directories.append(source_directory)

print_plan(f'Planned moves into "{series_name_full}"',planned_moves)
apply_moves(planned_moves)
log_entries('./'+series_name_full,[f'moved {source} -> {destination}' for source,destination in planned_moves])

removed_directories=remove_empty_directories(source_directories)
if removed_directories:print(f'\nRemoved now-empty source folder(s): {", ".join(removed_directories)}')

#clean names
planned_renames=plan_renames('./'+series_name_full,parsed_show_name,series_name_full)
print_plan(f'Planned renames in "{series_name_full}"',planned_renames)
applied_renames=apply_renames('./'+series_name_full,planned_renames)
log_entries('./'+series_name_full,[f'renamed {old_name} -> {new_name}' for old_name,new_name in applied_renames])



class TV_Series():
    pass
