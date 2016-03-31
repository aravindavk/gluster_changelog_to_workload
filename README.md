# Gluster Changelog API

Script to find the list of files not modified after a given timestamp

Script takes two arguments, Brick path and Output file name. Using the
brick path it finds the HTIME directory and gets the latest HTIME
file. HTIME file is a index file maintained by changelog translator,
which will have changelog file names.

    python gchangelogapi.py <BRICK_PATH> <OUTPUT_FILE>

For example,

    python gchangelogapi.py /exports/brick1/b1 ~/output.txt

Script uses
[this](https://github.com/gluster/glustertool/blob/master/glustertool/plugins/changelogparser.py)
changelog parser to parse the Gluster changelogs. I will add this tool
also to the same repository.

Script stores the processed details in a sqlite table to avoid
reprocessing Changelogs. Script uses sqlite table as cache when the
script run second time. (Which can be overridden by specifying
`--no-cache`)

    python gchangelogapi.py /exports/brick1/b1 ~/output.txt --no-cache

Cache will be stored in current directory where we run the script, if
we run the script in different directory then cache will not be
used.(This can be enhanced in future by saving in common path)

By default script lists all the files in the Brick, to list only the
files which are not modified after a given Timestamp,

    python gchangelogapi.py /exports/brick1/b1 ~/output.txt \
        --not-modified-since 1459423298

Script can be run in debug mode by specifying `--debug`

    python gchangelogapi.py /exports/brick1/b1 ~/output.txt \
        --not-modified-since 1459423298 --debug

Script by default will not convert PGFID into Path since it involves
readlink. Files can still be accessed using `aux-gfid-mount`.

Example output,

    00000000-0000-0000-0000-000000000001/f1
    00000000-0000-0000-0000-000000000001/f2

Output can be prefixed by giving `--output-prefix`,

    python gchangelogapi.py /exports/brick1/b1 ~/output.txt \
        --not-modified-since 1459423298 --debug \
        --output-prefix=/mnt/gv1/.gfid

Example output,

    /mnt/gv1/.gfid/00000000-0000-0000-0000-000000000001/f1
    /mnt/gv1/.gfid/00000000-0000-0000-0000-000000000001/f2

If we need to convert PGFID to path, specify `--pgfid-to-path`

    python gchangelogapi.py /exports/brick1/b1 ~/output.txt \
        --not-modified-since 1459423298 --debug --pgfid-to-path
    
For help,

    python gchangelogapi.py --help


## TODO/Issues:

- [ ] Script will not detect the files which are existed before
  enabling Changelog.(We can build the cache by crawling. NOT
  IMPLEMENTED)
- [ ] More filters similar to `--not-modified-since`
- [ ] Store Cache in common path so that script will be portable.
- [ ] Integrate with [glustertool](https://github.com/gluster/glustertool)
- [ ] Stale data handling with cache. For example, if Volume is deleted
  and recreated with same brick path then Cache will have stale data.
