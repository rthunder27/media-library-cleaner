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

- Matching is anchored to the start of the file/folder name (on a word
  boundary) to avoid title-subset false positives like "Angel" matching
  "Touched by an Angel". The trade-off: names with something prefixed before
  the title (e.g. `[ReleaseGroup] Angel - S01E01.mkv`) won't match either.
- Files missing an `sNNeNN` episode tag (or containing two of them) won't be
  renamed.
- The log records what changed, but there's no command to replay it as an
  undo yet.
