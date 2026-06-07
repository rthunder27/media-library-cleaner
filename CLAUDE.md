# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A single-file Python script (`dir_cleaner.py`) that organizes a local TV show
library. It has two modes:

- **Single-show mode** (default): looks up one series on TMDB (or takes the
  name/year offline), creates a `Series Name (Year)` folder in the current
  directory, and moves+renames matching video files into it as
  `Series Name (Year) sXXeXX.ext`.
- **Library mode** (`library add`/`scan`/`update` subcommands): a persistent
  registry of shows and download/scan locations, backed by a hidden
  `.library_config.json`, that lets you re-run the same organize-and-rename
  logic across many shows and directories without repeating the TMDB lookup.

There is no build system, test suite, linter, or dependency manifest — this is
a personal utility script in active, informal development.

## Running the script

```
python dir_cleaner.py <series name>                 # single-show mode
python dir_cleaner.py library add <series name>     # register a show in the library
python dir_cleaner.py library scan <directory>      # register a directory to scan for episodes
python dir_cleaner.py library update                # organize new episodes for every registered show
```

- Requires the `tvdb_api` environment variable to be set to a **TMDB** API key
  (the variable name is misleading — `tmdb.API_KEY = os.environ['tvdb_api']`
  actually authenticates against TMDB via the `tmdbsimple` package). Not
  needed in `--offline` mode.
- Single-show mode operates relative to the current working directory (`'.'`)
  — run it from the directory containing the show's files/folders. Library
  commands operate relative to the current directory too, treating it as the
  library's root directory (where `.library_config.json` and the organized
  `Series Name (Year)` folders live).
- Online mode is interactive: it prints TMDB search results and prompts you to
  pick the matching entry by index (or `q` to quit).
- Dependencies are not pinned anywhere; install `tmdbsimple` manually
  (`pip install tmdbsimple`) before running.
- `python dir_cleaner.py --help` / `library --help` / `library <command> --help`
  document the full option/argument reference with examples.

## Architecture / control flow

Everything lives in `dir_cleaner.py`. Functions/classes are defined first, then
a small dispatch block at the bottom either runs `run_library_command` (if
`sys.argv[1] == 'library'`) or falls through to the single-show flow:

1. **Name normalization** — `name_parser`/`replace_all` lowercase names and
   strip punctuation so directory/file names can be matched against the
   canonical series name; `is_show_match` anchors that match to the start of
   the candidate on a word boundary (see the in-code comment for the
   title-subset trade-off this resolves, and a suggested `--loose-match`
   alternative); `full_show_name` builds the canonical `"Name (Year)"` form.
2. **Directory scanning** — `make_parsed_file_dict`/`make_parsed_directory_dict`
   build `{original_name: parsed_name}` maps for video files
   (`mkv`/`mp4`/`avi`/`m4v`) and subdirectories of a given path.
3. **`resolve_series(name, offline, year_arg)`** — the TMDB-search-and-pick (or
   offline name+year entry) flow, returning `(name, year, tmdb_id)`. Shared by
   single-show mode and `library add`.
4. **`consolidate(parsed_show_name, destination_directory, destination_name, search_directories)`**
   — the core organize step: scans each search directory (and matching
   subfolders, including stray ones already inside the destination) for files
   belonging to the show, plans+applies moves (`plan_moves`/`apply_moves`),
   logs them (`log_entries`, distinguishing `moved` from `copied` — see below),
   removes now-empty source folders (`remove_empty_directories`), then
   plans+applies renames (`plan_renames`/`apply_renames`) the same way. Used by
   both single-show mode (with `search_directories=['.']`) and
   `Library.update_all` (with `search_directories=library.scan_directories`).
5. **`Series`/`Library`** — the library-mode persistence layer. `Series` bundles
   `name`/`year`/`tmdb_id` plus derived `full_name`/`directory` properties
   (`directory` is an absolute path under `library.root_directory`). `Library`
   holds `root_directory`, `scan_directories`, and `series`, and
   `load`/`save`s them as `.library_config.json`; `update_all` runs
   `consolidate` for every registered show against every registered (existing)
   scan directory, skipping any that have gone missing.
6. **`run_library_command(argv)`** — builds an `ArgumentParser` with `add`/
   `scan`/`update` subcommands and dispatches to the `Library` methods above.

`apply_moves` wraps each move in a try/except: if the source can't be removed
(eg. a video still being seeded), it falls back to copying the file to the
destination, leaves the original in place, and reports/logs that explicitly —
this is what makes auto-cleanup of scan-directory folders safe to do
unconditionally in `consolidate`.

## Known sharp edges (see also README "Known limitations")

- Files missing an `sNNeNN` pattern (or containing two) are not renamed —
  `plan_renames` will raise and `apply_renames` prints `failed to rename {file}`.
- The log (`.cleaner_log.txt`, one per organized show folder) records what
  changed, but there's no command to replay it as an undo yet.
- `is_show_match`'s anchored matching trades away names with something
  prefixed before the title (eg. `[ReleaseGroup] Angel - S01E01.mkv`) to avoid
  title-subset false positives — see the trade-off comment on `is_show_match`.
