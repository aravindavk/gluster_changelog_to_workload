import struct
import stat
import os
import sys
from errno import ENOENT

import xattr
import changelogparser


ROOTDIR = "/mnt/gv1"
ROOT_GFID = "00000000-0000-0000-0000-000000000001"

dir_num = 0


def _fmt_mknod(l):
    return "!II%dsI%dsIII" % (37, l+1)


def _fmt_mkdir(l):
    return "!II%dsI%dsII" % (37, l+1)


def _fmt_symlink(l1, l2):
    return "!II%dsI%ds%ds" % (37, l1+1, l2+1)


def entry_pack_reg(gf, bn, mo, uid, gid):
    bn = bn.encode('utf-8')
    gf = gf.encode('utf-8')
    blen = len(bn)
    return struct.pack(_fmt_mknod(blen),
                       uid, gid, gf, mo, bn,
                       stat.S_IMODE(mo), 0, os.umask(0))


def entry_pack_dir(gf, bn, mo, uid, gid):
    bn = bn.encode('utf-8')
    gf = gf.encode('utf-8')
    blen = len(bn)
    return struct.pack(_fmt_mkdir(blen),
                       uid, gid, gf, mo, bn,
                       stat.S_IMODE(mo), os.umask(0))


def entry_pack_symlink(gf, bn, lnk, mo, uid, gid):
    blen = len(bn)
    llen = len(lnk)
    return struct.pack(_fmt_symlink(blen, llen),
                       uid, gid, gf, mo, bn, lnk)


def process_changelog_record(record):
    global dir_num

    if record.fop in ["CREATE", "MKNOD"]:
        pgfid, bname = record.path.split("/")
        blob = entry_pack_reg(record.gfid, bname, record.mode,
                              record.uid, record.gid)
        pgfid_path = os.path.join(ROOTDIR, ".gfid", pgfid)

        try:
            xattr.set(pgfid_path, 'glusterfs.gfid.newfile', blob)
        except IOError as e:
            # Create a dummy parent dir if not exists already
            if e.errno == ENOENT:
                bname_dir = "%s_%s" % (changelog_file.lower(), dir_num)
                dir_num += 1
                blob_dir = entry_pack_dir(pgfid, bname_dir, 16893,
                                          0, 0)
                pgfid_path_dir = os.path.join(ROOTDIR, ".gfid", ROOT_GFID)
                xattr.set(pgfid_path_dir, 'glusterfs.gfid.newfile', blob_dir)
                xattr.set(pgfid_path, 'glusterfs.gfid.newfile', blob)
    elif record.fop == "MKDIR":
        pgfid, bname = record.path.split("/")
        blob = entry_pack_dir(record.gfid, bname, record.mode,
                              record.uid, record.gid)
        pgfid_path = os.path.join(ROOTDIR, ".gfid", pgfid)
        try:
            xattr.set(pgfid_path, 'glusterfs.gfid.newfile', blob)
        except IOError as e:
            # Create a dummy parent dir if not exists already
            if e.errno == ENOENT:
                bname_dir = "%s_%s" % (changelog_file.lower(), dir_num)
                dir_num += 1
                blob_dir = entry_pack_dir(pgfid, bname_dir, 16893,
                                          0, 0)
                pgfid_path_dir = os.path.join(ROOTDIR, ".gfid", ROOT_GFID)
                xattr.set(pgfid_path_dir, 'glusterfs.gfid.newfile', blob_dir)
                xattr.set(pgfid_path, 'glusterfs.gfid.newfile', blob)
    elif record.fop == "RENAME":
        path1 = os.path.join(ROOTDIR, ".gfid", record.path1)
        path2 = os.path.join(ROOTDIR, ".gfid", record.path2)
        os.rename(path1, path2)
    elif record.fop == "UNLINK":
        try:
            os.unlink(os.path.join(ROOTDIR, ".gfid", record.path))
        except OSError as e:
            if not e.errno == ENOENT:
                raise
    elif record.fop == "RMDIR":
        try:
            os.rmdir(os.path.join(ROOTDIR, ".gfid", record.path))
        except OSError as e:
            if not e.errno == ENOENT:
                raise

    elif record.fop_type == "D":
        # Populate file with 4mb data
        try:
            with open(os.path.join(ROOTDIR, ".gfid", record.gfid), "w") as f:
                f.write(SAMPLE_DATA)
        except OSError as e:
            if not e.errno == ENOENT:
                raise
    elif record.fop_type == "M":
        # Touch the file
        try:
            os.utime(os.path.join(ROOTDIR, ".gfid", record.gfid), None)
        except OSError as e:
            if not e.errno == ENOENT:
                raise

if __name__ == "__main__":
    ROOTDIR = sys.argv[1]
    changelog_file = sys.argv[2]
    SAMPLE_DATA = ""
    with open("sample.txt") as f:
        SAMPLE_DATA = f.read()
    changelogparser.parse(changelog_file, callback=process_changelog_record)
