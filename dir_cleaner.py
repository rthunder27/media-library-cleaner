#!/usr/bin/env python
import sys
import os
import argparse
import json
from shutil import move,copy2
import tmdbsimple as tmdb
import re
from datetime import datetime

#Strip any remaining special characters (eg. the "!" in "Reno 911!") since they're typically dropped from downloaded file/folder names
def name_parser(name):return re.sub(r'[^a-z0-9 ]','',replace_all(name.lower(),{"'":'',".":" ","-":' ',':':'',',':'','_':' '}))
def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text
def full_show_name(name,year):
    #Builds the canonical "Series Name (Year)" form (or just "Series Name" with no year); colons
    #are replaced since they're not valid in Windows file/folder names
    full=f'{name} ({year})' if year else name
    return full.replace(':','-')
def is_show_match(parsed_show_name,parsed_candidate_name,loose=False):
    #Default: anchors the match to the start of the candidate on a word boundary, eg.
    #parsed_show_name "angel" matches "angel s01e01" but not "touched by an angel s01e01" --
    #avoiding the title-subset false positive (Angel vs Touched by an Angel). Trade-off: this
    #also misses names with something prefixed before the title, eg. "[release group] angel s01e01".
    #--loose-match flips to the opposite trade-off: `parsed_show_name in parsed_candidate_name`
    #catches those prefixed cases, at the cost of reintroducing subset false positives -- useful
    #for shows whose name isn't a likely subset of another title.
    if loose:return parsed_show_name in parsed_candidate_name
    return parsed_candidate_name==parsed_show_name or parsed_candidate_name.startswith(parsed_show_name+' ')
def make_parsed_file_dict(directory='.'):
    #Finds video files in directory, parses the file names
    video_file_types=['mkv','mp4','avi','m4v']
    files=[x.name for x in os.scandir(directory) if x.is_file() and x.name[-3:] in video_file_types]
    return { x:name_parser(x) for x in files}
def make_parsed_directory_dict(directory='.'):
    directories=[x.name for x in os.scandir(directory) if x.is_dir()]
    return { x:name_parser(x) for x in directories}
def plan_moves(directory,parsed_show_name,destination_directory,loose=False):
    #Returns [(source_path,destination_path),...] for video files that match the show and would move into destination_directory
    parsed_file_dict=make_parsed_file_dict(directory)
    return [(os.path.join(directory,file),os.path.join(destination_directory,file))
            for file in parsed_file_dict if is_show_match(parsed_show_name,parsed_file_dict[file],loose)]
def apply_moves(moves):
    #Moves each (source,destination) pair; returns [(source,destination,status),...] where status is
    #'moved' or 'copied' (used when the source couldn't be removed, eg. a video still being seeded)
    results=[]
    for source,destination in moves:
        try:
            move(source,destination)
            results.append((source,destination,'moved'))
        except Exception:
            #shutil.move copies to the destination before removing the source, so on a "couldn't remove"
            #failure a full copy is often already there -- only copy again if it's missing, to avoid
            #redoing a multi-GB transfer
            if not os.path.exists(destination):copy2(source,destination)
            print(f'  could not remove "{source}" after copying it (it may still be in use) -- the original was left in place')
            results.append((source,destination,'copied'))
    return results
def plan_renames(directory,parsed_show_name,series_name_full,loose=False):
    #Returns [(old_name,new_name),...] for video files in directory that would be renamed to the standard format
    parsed_file_dict=make_parsed_file_dict(directory)
    renames=[]
    for file in parsed_file_dict:
        if is_show_match(parsed_show_name,parsed_file_dict[file],loose):
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

def resolve_series(name,offline,year_arg):
    #Looks the series up on TMDB and lets the user pick the right match (or, offline, takes the
    #name/year directly from the caller); returns (name,year,tmdb_id). tmdb_id is None offline.
    if not offline:
        tmdb.API_KEY=os.environ['tvdb_api']
        search=tmdb.Search()
        search.tv(query=name)
        if len(search.results)==0:
            print('Series Not Found')
            sys.exit('Program Quit')
        for i,s in enumerate(search.results):
            try:print(f"{i} |title: {s['name']}, aired: {s['first_air_date']}, overview:{s['overview']}")
            except:print(f"{i} |title: {s['name']}, overview:{s['overview']}")
        print('select entry # (or q to quit)')
        selected=input()
        try:result=search.results[int(selected)]
        except:sys.exit('Program Quit')
        return result['name'],result['first_air_date'][:4],result['id']
    else:
        year=year_arg
        if year is None:
            print('year (leave blank for no year)')
            year=input().strip()
        return name,year,None

def consolidate(parsed_show_name,destination_directory,destination_name,search_directories,loose=False):
    #Scans each directory in search_directories (and any of their matching subfolders, plus stray
    #matching subfolders already sitting inside destination_directory) for files belonging to the
    #show, moves+renames them into destination_directory, logs the changes, and removes any
    #now-empty source folders left behind
    planned_moves=[]
    source_directories=[]
    def add_subfolder_matches(parent_directory):
        for subfolder_name,parsed_name in make_parsed_directory_dict(parent_directory).items():
            if is_show_match(parsed_show_name,parsed_name,loose) and name_parser(destination_name)!=parsed_name:
                source_directory=os.path.join(parent_directory,subfolder_name)
                planned_moves.extend(plan_moves(source_directory,parsed_show_name,destination_directory,loose))
                source_directories.append(source_directory)

    for search_directory in search_directories:
        planned_moves+=plan_moves(search_directory,parsed_show_name,destination_directory,loose)
        add_subfolder_matches(search_directory)
    add_subfolder_matches(destination_directory)

    print_plan(f'Planned moves into "{destination_name}"',planned_moves)
    applied_moves=apply_moves(planned_moves)
    log_entries(destination_directory,[
        f'moved {source} -> {destination}' if status=='moved' else
        f'copied {source} -> {destination} (original left behind -- could not remove it, possibly still in use)'
        for source,destination,status in applied_moves])

    removed_directories=remove_empty_directories(source_directories)
    if removed_directories:print(f'\nRemoved now-empty source folder(s): {", ".join(removed_directories)}')

    planned_renames=plan_renames(destination_directory,parsed_show_name,destination_name,loose)
    print_plan(f'Planned renames in "{destination_name}"',planned_renames)
    applied_renames=apply_renames(destination_directory,planned_renames)
    log_entries(destination_directory,[f'renamed {old_name} -> {new_name}' for old_name,new_name in applied_renames])


class Series:
    def __init__(self,name,year,tmdb_id,loose_match,library):
        self.name=name
        self.year=year
        self.tmdb_id=tmdb_id
        self.loose_match=loose_match
        self.library=library

    @property
    def full_name(self):
        return full_show_name(self.name,self.year)

    @property
    def directory(self):
        return os.path.join(self.library.root_directory,self.full_name)


class Library:
    CONFIG_FILE='.library_config.json'

    def __init__(self,root_directory):
        self.root_directory=os.path.abspath(root_directory)
        self.scan_directories=[]
        self.series=[]

    @property
    def config_path(self):
        return os.path.join(self.root_directory,self.CONFIG_FILE)

    @classmethod
    def load(cls,root_directory):
        #Loads the library's config from root_directory, or starts a fresh (unsaved) one if there isn't one yet
        library=cls(root_directory)
        if os.path.exists(library.config_path):
            with open(library.config_path) as config_file:data=json.load(config_file)
            library.scan_directories=data.get('scan_directories',[])
            library.series=[Series(s['name'],s['year'],s.get('tmdb_id'),s.get('loose_match',False),library) for s in data.get('series',[])]
        return library

    def save(self):
        data={'scan_directories':self.scan_directories,
              'series':[{'name':s.name,'year':s.year,'tmdb_id':s.tmdb_id,'loose_match':s.loose_match} for s in self.series]}
        with open(self.config_path,'w') as config_file:json.dump(data,config_file,indent=2)

    def add_series(self,name,year,tmdb_id,loose_match=False):
        series=Series(name,year,tmdb_id,loose_match,self)
        if not os.path.isdir(series.directory):os.mkdir(series.directory)
        self.series.append(series)
        self.save()
        return series

    def add_scan_directory(self,directory):
        directory=os.path.abspath(directory)
        if directory not in self.scan_directories:
            self.scan_directories.append(directory)
            self.save()

    def update_all(self):
        #Scans every registered directory for matching episodes of every registered show and
        #organizes them into the library -- skipping (and warning about) any scan directory
        #that's gone missing, eg. an unmounted drive
        scan_directories=[]
        for directory in self.scan_directories:
            if os.path.isdir(directory):scan_directories.append(directory)
            else:print(f'(skipping scan directory that no longer exists: {directory})')
        for series in self.series:
            if not os.path.isdir(series.directory):os.mkdir(series.directory)
            print(f'\n--- {series.full_name} ---')
            consolidate(name_parser(series.name),series.directory,series.full_name,scan_directories,series.loose_match)


def run_library_command(argv):
    library_parser=argparse.ArgumentParser(
        prog='dir_cleaner.py library',
        description='Manages a persistent library: register shows once, register the directories\n'
                    'your torrent client downloads into, then run "update" to auto-organize new\n'
                    'episodes into the library the same way the regular mode organizes one show.\n'
                    '\n'
                    'Run these from the library\'s root directory -- where your organized\n'
                    '"Series Name (Year)" folders live (or should live); that\'s also where the\n'
                    'library\'s config and log are kept.',
        epilog='examples:\n'
               '  python dir_cleaner.py library add The Office\n'
               '  python dir_cleaner.py library add --offline --year 2005 The Office\n'
               '  python dir_cleaner.py library scan /path/to/torrent/downloads\n'
               '  python dir_cleaner.py library update',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers=library_parser.add_subparsers(dest='action')
    subparsers.required=True  #add_subparsers(required=True) raises TypeError on Python 3.6 (bpo-29298)

    add_parser=subparsers.add_parser('add',help='look up a series and register it in the library')
    add_parser.add_argument('series_name',nargs='+',help='name of the TV series to add')
    add_parser.add_argument('--offline',action='store_true',help='skip the TMDB lookup; enter the show name and year manually')
    add_parser.add_argument('--year',help='year the series first aired (offline mode; prompted for if omitted, leave blank for no year)')
    add_parser.add_argument('--loose-match',action='store_true',help='match any file/folder containing the show name rather than just ones starting with it -- catches names with something prefixed (eg. a release group tag), at the risk of subset false positives (eg. "Angel" matching "Touched by an Angel"); saved with the series and used on every future update')

    scan_parser=subparsers.add_parser('scan',help='register a directory to scan for new episodes (eg. a torrent download folder)')
    scan_parser.add_argument('directory',help='path to the directory to scan on update')

    subparsers.add_parser('update',help='scan all registered directories and organize matching episodes into the library')

    args=library_parser.parse_args(argv)
    library=Library.load('.')

    if args.action=='add':
        name,year,tmdb_id=resolve_series(' '.join(args.series_name),args.offline,args.year)
        series=library.add_series(name,year,tmdb_id,args.loose_match)
        loose_note=' (loose matching enabled)' if series.loose_match else ''
        print(f'Added "{series.full_name}" to the library at {series.directory}{loose_note}')
    elif args.action=='scan':
        library.add_scan_directory(args.directory)
        print(f'Now scanning for episodes in: {os.path.abspath(args.directory)}')
    elif args.action=='update':
        if not library.series:
            print('No series registered yet -- add one with: python dir_cleaner.py library add <series name>')
        else:
            library.update_all()


if len(sys.argv)>1 and sys.argv[1]=='library':
    run_library_command(sys.argv[2:])
    sys.exit()

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
           '  python dir_cleaner.py --loose-match The Office           (also matches "[Group] The Office - S01E01.mkv")\n'
           '\n'
           'Online mode (the default) requires the tvdb_api environment variable to hold a TMDB API key.\n'
           '\n'
           'To manage a persistent library across multiple shows and download locations instead,\n'
           'see: python dir_cleaner.py library --help',
    formatter_class=argparse.RawDescriptionHelpFormatter)
arg_parser.add_argument('series_name',nargs='+',help='name of the TV series to search for/organize')
arg_parser.add_argument('--offline',action='store_true',help='skip the TMDB lookup; enter the show name and year manually')
arg_parser.add_argument('--year',help='year the series first aired (offline mode; prompted for if omitted, leave blank for no year)')
arg_parser.add_argument('--loose-match',action='store_true',help='match any file/folder containing the show name rather than just ones starting with it -- catches names with something prefixed (eg. a release group tag), at the risk of subset false positives (eg. "Angel" matching "Touched by an Angel")')
cli_args=arg_parser.parse_args()

series_name=' '.join(cli_args.series_name)
name,year,tmdb_id=resolve_series(series_name,cli_args.offline,cli_args.year)
parsed_show_name=name_parser(name)
series_name_full=full_show_name(name,year)

if series_name_full not in make_parsed_directory_dict():os.mkdir(series_name_full)
consolidate(parsed_show_name,series_name_full,series_name_full,['.'],cli_args.loose_match)
