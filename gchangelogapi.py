#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Find the last HTIME file, $BRICK/.glusterfs/changelogs/htime
# Read HTIME file to get Changelog file names
# Parse each changelog and populate DB  GFID|Path|CreatedAt|ModifiedAt|
# Skip parsing changelog if cache enabled/available and already processed.
# If Unlinked, remove history of that file from DB
# If Renamed, update New Name
# If Data/Metadata then update ModifiedAt to new Time. Create Row if not exists
# Analysis
#    Get list of files which are not modified after given timestamp
import os
import sqlite3
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import sys
import urllib
import logging
import time

import changelogparser

SEP = "\x00"
conn = None
cursor = None
ROOT_GFID = "00000000-0000-0000-0000-000000000001"
LOG_FILE = "gchangelogapi.log"

logger = logging.getLogger(__name__)
handler = logging.FileHandler(LOG_FILE)
handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(levelname)7s "
    "[%(lineno)s:%(funcName)s] "
    "- %(message)s"))

logger.addHandler(handler)
logger.setLevel(logging.INFO)


class NoHtimeFiles(Exception):
    pass


def symlink_gfid_to_path(brick, gfid):
    """
    Each directories are symlinked to file named GFID
    in .glusterfs directory of brick backend. Using readlink
    we get PARGFID/basename of dir. readlink recursively till
    we get PARGFID as ROOT_GFID.
    """
    if gfid == ROOT_GFID:
        return ""

    out_path = ""
    while True:
        path = os.path.join(brick, ".glusterfs", gfid[0:2], gfid[2:4], gfid)
        path_readlink = os.readlink(path)
        pgfid = os.path.dirname(path_readlink)
        out_path = os.path.join(os.path.basename(path_readlink), out_path)
        if pgfid == "../../00/00/%s" % ROOT_GFID:
            break
        gfid = os.path.basename(pgfid)
    return out_path


def db_init(db_path):
    global conn, cursor
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


def db_create_tables():
    query1 = """CREATE TABLE IF NOT EXISTS last_processed(
    ts INTEGER
    )"""
    cursor.execute(query1)

    cursor.execute("INSERT INTO last_processed(ts) VALUES(0)")

    query2 = """CREATE TABLE IF NOT EXISTS data(
    gfid VARCHAR(100),
    path VARCHAR(500),
    created_at INTEGER,
    modified_at INTEGER,
    UNIQUE(gfid, path) ON CONFLICT IGNORE
    )"""
    cursor.execute(query2)


def db_tables_cleanup():
    cursor.execute("DROP TABLE IF EXISTS last_processed")
    cursor.execute("DROP TABLE IF EXISTS data")


def db_get_last_processed():
    cursor.execute("SELECT ts FROM last_processed")
    return cursor.fetchone()[0]


def db_add_record(gfid, path, ts):
    query = """INSERT INTO data(gfid, path, created_at, modified_at)
    VALUES(?, ?, ?, ?)"""
    cursor.execute(query, (gfid, path, ts, ts))


def db_remove_record(gfid, path):
    query = "DELETE FROM data WHERE gfid=? AND path = ?"
    cursor.execute(query, (gfid, path))


def db_update_record(gfid, ts):
    query = "UPDATE data SET modified_at = ? WHERE gfid = ?"
    cursor.execute(query, (ts, gfid))


def db_rename_record(gfid, path1, path2, ts):
    query = """UPDATE data SET path = ?, modified_at = ?
    WHERE gfid = ? AND path = ?"""
    cursor.execute(query, (path2, ts, gfid, path1))


def db_get_paths_not_modified_after(ts):
    if ts == 0:
        # Get all the file paths
        query = "SELECT path FROM data"
        cursor.execute(query)
    else:
        query = "SELECT path FROM data WHERE modified_at < ?"
        cursor.execute(query, (ts, ))


def db_update_last_processed(ts):
    query = "UPDATE last_processed SET ts = ?"
    cursor.execute(query, (ts, ))


def get_latest_htime_file(brick_path):
    htime_dir = os.path.join(brick_path, ".glusterfs/changelogs/htime")
    htime_files = sorted(os.listdir(htime_dir))
    if len(htime_files) == 0:
        raise NoHtimeFiles("HTIME File not exists, Is Changelog enabled?")

    return htime_files[-1]


def process_changelog_record(record):
    if record.fop in ["CREATE", "MKDIR", "MKNOD", "LINK", "SYMLINK"]:
        db_add_record(record.gfid, record.path, record.ts)
    elif record.fop == "RENAME":
        db_rename_record(record.gfid, record.path1, record.path2, record.ts)
    elif record.fop_type in ["D", "M"]:
        db_update_record(record.gfid, record.ts)
    elif record.fop in ["UNLINK", "RMDIR"]:
        db_remove_record(record.gfid, record.path)


def process_htime_file(brick_path, filename):
    last_processed = db_get_last_processed()
    logger.info("Last processed Changelog TS from cache is {0}".format(
        last_processed))

    htime_file_path = os.path.join(brick_path,
                                   ".glusterfs/changelogs/htime",
                                   filename)
    changelog_ts = 0

    with open(htime_file_path) as f:
        # Read first few bytes and split into paths
        # get length of first path to get path size
        data = f.read(300)
        path_length = len(data.split(SEP)[0])
        f.seek(0)

        # Get each Changelog file name and process it
        while True:
            changelog_file = f.read(path_length + 1).strip(SEP)
            if not changelog_file:
                break

            changelog_ts = int(changelog_file.split(".")[-1])
            fname = changelog_file.split("/")[-1]

            # Avoid Reprocess if the changelog is already processed
            if changelog_ts < last_processed:
                if fname.startswith("CHANGELOG."):
                    logger.debug("Skipped processing Changelog {0}"
                                 "(Already processed)".format(fname))
                continue

            # If no real changelog file, Changelog filename starts
            # with lower case changelog.TS instead of CHANGELOG.TS
            # Parse Changelog file only if it is real Changelog file
            if fname.startswith("CHANGELOG."):
                logger.debug("Processing Changelog {0}".format(fname))
                changelogparser.parse(changelog_file.strip(SEP),
                                      callback=process_changelog_record)

            # Update last processed Time
            db_update_last_processed(changelog_ts)

            conn.commit()

        if changelog_ts > 0:
            logger.info("Changelogs processed Till {0}".format(
                changelog_ts))


def get_args():
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__)
    parser.add_argument("brick_path", help="Brick Path")
    parser.add_argument("--output-file", "-o", help="Output File")
    parser.add_argument("--not-modified-since", "-n", type=int,
                        help="Files not modified since",
                        default=int(time.time()))
    parser.add_argument("--mmin", type=int,
                        help="File's data was last modified n minutes ago.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Do not use cache")
    parser.add_argument("--output-prefix", help="Output prefix for path",
                        default="")
    parser.add_argument("--pgfid-to-path", action="store_true",
                        help="Convert PGFID to Path")
    parser.add_argument("--debug", help="Enable debug logging",
                        action="store_true")
    return parser.parse_args()


def output(args, not_modified_since, file_obj=None):
    db_get_paths_not_modified_after(not_modified_since)

    for row in cursor:
        path = row[0]
        if args.pgfid_to_path:
            pgfid, bn = row[0].split("/")
            path = os.path.join(symlink_gfid_to_path(args.brick_path,
                                                     pgfid), bn)

        if args.output_prefix:
            path = os.path.join(args.output_prefix, path)

        if file_obj is not None:
            file_obj.write("{0}\n".format(path))
        else:
            print (path)


def main():
    args = get_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    db_path = "changelogdata_" + urllib.quote_plus(args.brick_path) + ".db"
    db_init(db_path)

    # Delete Db if no cache is set
    if args.no_cache:
        db_tables_cleanup()

    # Initialize tables
    db_create_tables()

    try:
        htime_file = get_latest_htime_file(args.brick_path)
    except NoHtimeFiles as err:
        sys.stderr.write("{0}\n".format(err))
        sys.exit(1)

    not_modified_since = 0
    if args.mmin is not None:
        not_modified_since = int(time.time()) - (args.mmin * 60)
    elif args.not_modified_since is not None:
        not_modified_since = args.not_modified_since

    logger.info("Not modified Since: {0}".format(not_modified_since))

    process_htime_file(args.brick_path, htime_file)

    if args.output_file:
        with open(args.output_file, "w") as f:
            output(args, not_modified_since, f)
    else:
        output(args, not_modified_since)


if __name__ == "__main__":
    main()
