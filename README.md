# media-library-cleaner

A small Python script for organizing a local TV show library. Give it a series
name and it looks the show up on [TMDB](https://www.themoviedb.org/), creates a
`Series Name (Year)` folder, and moves/renames matching video files into it.

## What it does

1. Searches TMDB for the series name you give it and lets you pick the correct
   match from the results (or, in offline mode, takes the name/year directly
   from you).
2. Creates a `Series Name (Year)` folder in the current directory.
3. Scans the current directory -- both loose files and matching subfolders --
   for video files (`.mkv`, `.mp4`, `.avi`, `.m4v`) whose names match the show,
   and moves them into the new folder.
4. Renames the moved files to a consistent format: `Series Name (Year) sXXeXX.ext`

Before making any changes, it prints the planned moves and renames so you can
see exactly what's about to happen.

## Requirements

- Python 3
- [`tmdbsimple`](https://pypi.org/project/tmdbsimple/) (`pip install tmdbsimple`)
- A TMDB API key, set as the `tvdb_api` environment variable (only needed for
  the default online lookup -- not required if you use `--offline`)

## Usage

Run the script from the directory containing the show's video files/folders:

```
python dir_cleaner.py <series name>
```

You'll be shown a numbered list of TMDB search results and prompted to pick
the correct one (or `q` to quit).

### Offline mode

Skip the TMDB lookup and supply the show name/year yourself:

```
python dir_cleaner.py --offline <series name>
python dir_cleaner.py --offline --year <year> <series name>
python dir_cleaner.py --offline --year "" <series name>   # omit the year entirely
```

If `--year` isn't given in offline mode, you'll be prompted for one. Leave it
blank to omit the year -- and the surrounding parentheses -- from the folder
and file names altogether.

Run `python dir_cleaner.py --help` for the full option reference and examples.

## Library mode

For an ongoing setup -- a fixed folder of organized shows, fed by one or more
download locations -- you can register everything once and let the script
auto-organize new episodes on a schedule (eg. a cron job/scheduled task) or
whenever you remember to run it:

```
python dir_cleaner.py library add <series name> [--offline] [--year <year>]
python dir_cleaner.py library scan <directory>
python dir_cleaner.py library update
```

Run these from your library's root directory -- the folder where your
organized `Series Name (Year)` folders live (or should live). That's where
the library keeps its hidden `.library_config.json` (the registered shows and
scan directories) alongside the per-show logs.

- `add` looks the series up on TMDB (or, with `--offline`, takes the name/year
  directly, just like single-show mode) and registers it, creating its
  `Series Name (Year)` folder if it doesn't exist yet.
- `scan` registers a directory to search for new episodes -- typically wherever
  your torrent client downloads to. Run it once per location; you can register
  more than one.
- `update` scans every registered directory for matching episodes of every
  registered show and organizes them into the library -- using the exact same
  matching, moving, renaming, logging, copy-fallback, and empty-folder cleanup
  behavior as single-show mode, just repeated across shows and directories. A
  scan directory that's gone missing (eg. an unmounted drive) is skipped with
  a warning rather than failing the whole run.

Run `python dir_cleaner.py library --help` (or `library <command> --help`) for
the full reference and examples.

## Logging and cleanup

Every move and rename is appended, with a timestamp, to a hidden
`.cleaner_log.txt` file inside the destination `Series Name (Year)` folder --
a running record of what the script has done.

If a file can't be removed from its original location -- for example, a video
that's still being seeded by a torrent client -- the script falls back to
copying it to the new location and leaves the original behind, printing (and
logging) a note so you know there's a leftover copy to clean up once it's no
longer in use.

After moving videos out, any source folder left containing nothing but junk
(`.nfo`, `.txt`, `.exe` files, or nothing at all) is removed automatically.
Folders with anything else left in them (subtitles, nested folders, etc.) are
left alone.

## Known limitations

- `library` is a reserved first argument that switches to library mode (like
  `git`/`docker`/`npm` subcommands) -- a series whose name starts with
  "Library" can't be looked up in single-show mode, since the script will try
  to treat it as a library subcommand instead.
- Matching is anchored to the start of the file/folder name (on a word
  boundary) to avoid title-subset false positives like "Angel" matching
  "Touched by an Angel". The trade-off: names with something prefixed before
  the title (e.g. `[ReleaseGroup] Angel - S01E01.mkv`) won't match either.
- Files missing an `sNNeNN` episode tag (or containing two of them) won't be
  renamed.
- The log records what changed, but there's no command to replay it as an
  undo yet.
