# Gluster Changelog API

Script to find the list of files not modified after a given timestamp

Script takes two arguments, Brick path and Output file name. Using the
brick path it finds the HTIME directory and gets the latest HTIME
file. HTIME file is a index file maintained by changelog translator,
which will have changelog file names.

    python gchangelogapi.py <BRICK_PATH>

For example,

    python gchangelogapi.py /exports/brick1/b1

Creates log file(`gchangelogapi.log`) in the current directory.

By default prints file names to stdout, which can be redirected to
output file using `-o` or `--output-file`

For example,

    python gchangelogapi.py /exports/brick1/b1 -o output.txt

Script uses
[this](https://github.com/gluster/glustertool/blob/master/glustertool/plugins/changelogparser.py)
changelog parser to parse the Gluster changelogs. I will add this tool
also to the same repository.

Script stores the processed details in a sqlite table to avoid
reprocessing Changelogs. Script uses sqlite table as cache when the
script run second time. (Which can be overridden by specifying
`--no-cache`)

    python gchangelogapi.py /exports/brick1/b1 -o output.txt --no-cache

Cache will be stored in current directory where we run the script, if
we run the script in different directory then cache will not be
used.(This can be enhanced in future by saving in common path)

## Crawl
When Changelog not enabled from the beginning, this script will not
pick up the changes happened to the files which existed before
changelog enable. Use `--crawl` to initiate the crawl when running
this script for a brick for first time. Note: This script invalidates
the cache if any.

	python gchangelogapi.py /exports/brick1/b1 -o output.txt --crawl

## Filters
#### not-modified-since <TS>
By default script lists all the files in the Brick, to list only the
files which are not modified after a given Timestamp,

    python gchangelogapi.py /exports/brick1/b1 -o output.txt \
        --not-modified-since 1459423298

#### mmin MMIN File's data was last modified n minutes ago.

	--mmin n  - Find files that are exactly n minutes old
    --mmin -n - Find files that are less than n minutes old
    --mmin +n - Find files that are more than n minutes old

To list the files which are not modified in last two hours,

    python gchangelogapi.py /exports/brick1/b1 -o output.txt \
        --mmin +120

#### type
List only files using,

    python gchangelogapi.py /exports/brick1/b1 -o output.txt \
		--mmin +120 --type f

List only directories using,

    python gchangelogapi.py /exports/brick1/b1 -o output.txt \
		--mmin +120 --type d

## Debug
Script can be run in debug mode by specifying `--debug`

    python gchangelogapi.py /exports/brick1/b1 -o output.txt \
        --not-modified-since 1459423298 --debug

## Output Prefix
Since script works in the brick backend, but we need to operate on the
output in Gluster mount. We can prefix every line of output path with
required prefix using `--output-prefix` option.

Script by default will not convert PGFID into Path since it involves
readlink. Files can still be accessed using `aux-gfid-mount`.

Mount the volume using,

	mount -t glusterfs -o aux-gfid-mount localhost:gv1 /mnt/gv1

Now we can access the files in this mount with parent GFID and
basename even though full path is not known.

	cat /mnt/gv1/.gfid/e09e523d-97d3-4c00-968d-db747c3fda9c/f1

Where `00000000-0000-0000-0000-000000000001` is GFID of root directory.

If we give output prefix as `$MOUNT_PATH/.gfid`, script will add this
prefix while printing the output.

Example output(without `--output-prefix`),

    00000000-0000-0000-0000-000000000001/f1
    00000000-0000-0000-0000-000000000001/f2

Output can be prefixed by giving `--output-prefix`,

    python gchangelogapi.py /exports/brick1/b1 -o output.txt \
        --not-modified-since 1459423298 --debug \
        --output-prefix=/mnt/gv1/.gfid

Example output(with `--output-prefix`),

    /mnt/gv1/.gfid/00000000-0000-0000-0000-000000000001/f1
    /mnt/gv1/.gfid/00000000-0000-0000-0000-000000000001/f2

## Parent GFID to Path
If we don't use aux mount, then we need full path of the file to
access it. Convert PGFID to path by specifying `--pgfid-to-path`

Mount without aux-gfid-mount option,

	mount -t glusterfs localhost:gv1 /mnt/gv1

Run with `--pgfid-to-path` and `--output-prefix`

    python gchangelogapi.py /exports/brick1/b1 -o output.txt \
		--not-modified-since 1459423298 --debug --pgfid-to-path \
		--output-prefix=/mnt/gv1

**Note:** .gfid is not required in `--output-prefix`

## Usecase - Deleting Old files
The script output can be piped to another command, which can be used
to delete the older files. For example, delete all files which are not
modified in last one hour.

    python gchangelogapi.py /exports/brick1/b1 \
        --output-prefix=/mnt/gv1/.gfid \
        --mmin +60 | xargs rm

**Note:** You can double confirm before deleting actual file,

    python gchangelogapi.py /exports/brick1/b1 \
        --output-prefix=/mnt/gv1/.gfid \
        --mmin +60 | xargs -t -I {} find {} -mmin +60 | xargs rm

## GFID to Path Conversion
Since Cache is available, it is easy to convert GFID to path. Pass
GFID to the script using `gfid-to-path` or `-g` option.

    python gchangelogapi.py /exports/brick1/b1 \
		--output-prefix=/mnt/gv1/ \
		--pgfid-to-path \
		-g ebdb3062-f935-460e-a02a-8b84e3dbe300

**Note:** Multiple GFIDs can be provided at once

    python gchangelogapi.py /exports/brick1/b1 \
		--output-prefix=/mnt/gv1/ \
		--pgfid-to-path \
		-g ebdb3062-f935-460e-a02a-8b84e3dbe300 \
		-g 77e78a8e-3641-404e-9852-8a3fa4d15f7b

For help,

    python gchangelogapi.py --help


## TODO/Issues:

- [ ] Exact time of each file operation is not available from
  Changelogs. We need to use Changelog rollover time(Changelog file
  suffix) as FOP Timestamp.
- [X] Script will not detect the files which are existed before
  enabling Changelog.(Added `--crawl` option)
- [ ] If Changelog is disabled and enabled, script only considers
  latest HTIME file only for processing Changelogs.
- [ ] More filters similar to `--not-modified-since`
- [X] Store Cache in common path so that script will be
  portable(Introduced `--cache-dir` option)
- [ ] Integrate with [glustertool](https://github.com/gluster/glustertool)
- [ ] Stale data handling with cache. For example, if Volume is deleted
  and recreated with same brick path then Cache will have stale data.
- [X] Handling Unicode file names
