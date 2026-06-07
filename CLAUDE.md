# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A single-file Python script (`dir_cleaner.py`) that organizes a local TV show
library: it looks up a series on TMDB, creates a `Series Name (Year)` folder,
moves matching video files into it from scattered subdirectories, and renames
them to a consistent `Series Name (Year) sXXeXX.ext` format.

There is no build system, test suite, linter, or dependency manifest — this is
a personal utility script in active, informal development (see TODO/Open Issues
comments at the top of `dir_cleaner.py`).

## Running the script

```
python dir_cleaner.py <series name>
```

- Requires the `tvdb_api` environment variable to be set to a **TMDB** API key
  (the variable name is misleading — `tmdb.API_KEY = os.environ['tvdb_api']`
  actually authenticates against TMDB via the `tmdbsimple` package).
- Run it from the directory containing the show's video files/subfolders — the
  script operates relative to the current working directory (`'.'`).
- It is interactive: it prints TMDB search results for the given name and
  prompts you to pick the matching entry by index (or `q` to quit).
- Dependencies are not pinned anywhere; install `tmdbsimple` manually
  (`pip install tmdbsimple`) before running.

## Architecture / control flow

Everything lives in `dir_cleaner.py` and runs top-to-bottom as a script (the
`TV_Series` class at the bottom is an unused stub for a planned OOP refactor):

1. **Name normalization** — `name_parser`/`replace_all` lowercase names and
   strip punctuation (`'`, `.`, `-`, `:`, `,`, `_`) so directory/file names can
   be fuzz-matched against the canonical series name.
2. **Directory scanning** — `make_parsed_file_dict` / `make_parsed_directory_dict`
   build `{original_name: parsed_name}` maps for video files
   (`mkv`/`mp4`/`avi`/`m4v`) and subdirectories of a given path.
3. **TMDB lookup** — `tmdb.Search().tv(query=...)` resolves the series to a
   canonical name + air year, producing `series_name_full = "Name (Year)"`
   (colons replaced with `-` for filesystem safety). An `on_line` flag exists
   to switch to a manual/offline entry path, but that path is incomplete.
4. **Consolidation** — `copy_files_to` walks matching subdirectories (both in
   the CWD and inside the newly created series folder) and moves any video
   file whose parsed name contains the parsed show name into the target
   `series_name_full` directory.
5. **Renaming** — `clean_names` extracts an `sNNeNN` (or `sNN.eNN`) episode
   tag via regex from each matching file and renames it to
   `"{series_name_full} {sXXeXX}{ext}"`.

## Known sharp edges (from in-file TODO/Open Issues comments)

- Title-subset collisions are unresolved (e.g. "Angel" matches "Touched by an
  Angel").
- Files missing an `sNNeNN` pattern (or containing two) are not handled —
  `clean_names` will throw and print `failed to rename {file}`.
- No change log/undo mechanism exists yet for moves or renames.
- Empty leftover folders (containing only `.nfo`/`.txt`/`.exe`) are not cleaned
  up after files are moved out.
