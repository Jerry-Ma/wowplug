#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2018-01-02 14:40
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from functools import lru_cache
import posixpath
import os
import glob
import errno
import zipfile
from io import BytesIO
import logging
from tempfile import TemporaryDirectory
import yaml
from collections import OrderedDict
from tabulate import tabulate
import dirsync
import shutil
from subprocess import Popen, PIPE


__all__ = [
        'instance_method_lru_cache', 'log_and_raise',
        'mkdirs', 'unzipdir', 'zipdir', 'linkdir',
        'urljoin', 'expanded_abspath', 'tabulate_listofdicts', 'yaml']


instance_method_lru_cache = lru_cache
"""
.. todo::

    Find a way to implement this.
"""


def log_and_raise(logger_func, msg, exc):
    """Log message `msg` to `logger_func` and raise `exc` with the same
    message."""
    logger_func(msg)
    raise exc(msg)


def run_and_log(cmd, logger_func):
    process = Popen(cmd, stdout=PIPE)
    cmdstr = ' '.join(['"{}"'.format(c) if ' ' in c else c for c in cmd])
    with process.stdout:
        for ln in iter(process.stdout.readline, b''):
            logger_func('{}\n    {}"'.format(
                cmdstr, ln.decode('utf-8').strip('\n')))
    return process.wait()  # 0 means success


def urljoin(*args):
    """Join URL segments and *ignore* the leading slash ``/``."""
    return posixpath.join(*[a.rstrip("/") if i == 0 else a.strip("/")
                            for i, a in enumerate(args)])


def expanded_abspath(p):
    """Return absolute path with user ``~`` expanded for path `p`."""
    return os.path.abspath(os.path.expanduser(p))


def tabulate_listofdicts(lod, keymap=None, fill=None, **kwargs):
    """Return a table summarizes a list of dicts."""
    if keymap is None:
        return tabulate(lod, **kwargs)
    else:
        # create a list of list from key map
        try:
            hs, fs = zip(*keymap)
        except TypeError:
            hs, fs = zip(*keymap.items())
        lol = [[f(d) if callable(f) else d.get(f, fill)
                for f in fs] for d in lod]
        kwargs.pop('headers', None)
        return tabulate(lol, headers=hs, **kwargs)


def mkdirs(d):
    """Create directory named `d`"""
    try:
        os.makedirs(d)
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise
    return d


def zipdir(src, save=None):
    """Create a ZIP archive for a directory `src` and its contents.

    :param save: If not ``None``, the created zip file will be saved
        to the filename. Otherwise a :class:`BytesIO` object is
        returned with its seek position at the start.
    """
    logger = logging.getLogger("zip")
    _save = save
    if save is None:
        save = BytesIO()
    zf = zipfile.ZipFile(save, 'w', zipfile.ZIP_DEFLATED)
    abssrc = os.path.abspath(src)
    for dirname, subdirs, files in os.walk(src, followlinks=True):
        for filename in files:
            absname = os.path.abspath(os.path.join(dirname, filename))
            arcname = absname.split(abssrc)[-1]
            try:
                zf.write(absname, arcname)
            except FileNotFoundError:
                logger.warning("missing or broken file {}".format(absname))
    zf.close()
    if _save is None:
        save.seek(0)
        return save
    else:
        return None


def unzipdir(source, target, pattern='*'):
    """Unpack a ZIP archive `source` to the target diretory `target`.

    :param pattern: glob pattern to specify the files to be unzipped.
        If it points to a file, the parent directory is used. If it
        points to a directory, the directory is used.
    """
    logger = logging.getLogger("unzip")
    logger.info("{} to {} for {}".format(source, target, pattern))
    with open(source, 'rb') as fo:
        zf = zipfile.ZipFile(fo)
        # create a tempdirectory
        with TemporaryDirectory() as tmpdir:
            zf.extractall(tmpdir)
            # find the root path for the sync
            srcpaths = glob.glob(os.path.join(tmpdir, pattern))
            srcdirs = [p if os.path.isdir(p) else os.path.dirname(p)
                       for p in srcpaths]
            # get target dir and make sure those are directories not links
            tgtdirs = [os.path.join(target, os.path.basename(s))
                       for s in srcdirs]
            if any(os.path.islink(t) for t in tgtdirs):
                raise RuntimeError(
                    "cannot unzip because target is a symlink. the"
                    " target may be a linked github repository. please"
                    " check the source list.")
            for srcdir, tgtdir in zip(srcdirs, tgtdirs):
                logger.debug("unzip from {} to {}".format(srcdir, tgtdir))
                # sync the directory to target
                dirsync.sync(
                        srcdir, tgtdir, "update",
                        create=True,
                        verbose=False,
                        logger=logging.getLogger("dirsync"))
                dirsync.sync(
                        srcdir, tgtdir, "sync",
                        purge=False,
                        verbose=False,
                        logger=logging.getLogger("dirsync"))
            return tgtdirs


def linkdir(source, target, pattern='*'):
    """Link directory `source` to diretory `target`.

    :param pattern: glob pattern to specify the files to be linked.
        If it points to a file, the parent directory is used. If it
        points to a directory, the directory is used.
    """
    logger = logging.getLogger("link")
    logger.info("{} to {} for {}".format(source, target, pattern))
    # find the root path for the sync
    srcpaths = glob.glob(os.path.join(source, pattern))
    srcdirs = [p if os.path.isdir(p) else os.path.dirname(p)
               for p in srcpaths]
    tgtdirs = [os.path.join(target, os.path.basename(s)) for s in srcdirs]
    for srcdir, tgtdir in zip(srcdirs, tgtdirs):
        logger.debug("link from {} to {}".format(srcdir, tgtdir))
        if os.path.exists(tgtdir):
            logger.warning(
                    "remove existing target {} before link".format(tgtdir))
            if os.path.islink(tgtdir):
                os.unlink(tgtdir)
            else:
                if shutil.rmtree.avoids_symlink_attacks:
                    shutil.rmtree(tgtdir)
                else:
                    raise RuntimeError(
                        "{} need to be deleted first to create"
                        " a symlink from {}".format(tgtdir, srcdir))
        os.symlink(srcdir, tgtdir)
    return tgtdirs


class LoggingHandler(logging.StreamHandler):
    """Customize logging handler to cleanup some noises."""

    def emit(self, record):
        if record.name == "dirsync":
            if logging.getLogger().level > logging.DEBUG:
                return
            record.level = logging.DEBUG
            record.levelname = logging.getLevelName(logging.DEBUG)
        return super().emit(record)


def _represent_odict(dump, tag, mapping, flow_style=None):
    """Like :meth:`BaseRepresenter.represent_mapping`, but
    does not issue the :meth:`sort`.
    """
    value = []
    node = yaml.MappingNode(tag, value, flow_style=flow_style)
    if dump.alias_key is not None:
        dump.represented_objects[dump.alias_key] = node
    best_style = True
    if hasattr(mapping, 'items'):
        mapping = mapping.items()
    for item_key, item_value in mapping:
        node_key = dump.represent_data(item_key)
        node_value = dump.represent_data(item_value)
        if not (isinstance(node_key, yaml.ScalarNode) and not node_key.style):
            best_style = False
        if not (isinstance(node_value, yaml.ScalarNode) and
                not node_value.style):
            best_style = False
        value.append((node_key, node_value))
    if flow_style is None:
        if dump.default_flow_style is not None:
            node.flow_style = dump.default_flow_style
        else:
            node.flow_style = best_style
    return node


yaml.SafeDumper.add_representer(
        OrderedDict,
        lambda dumper, value: _represent_odict(
            dumper, u'tag:yaml.org,2002:map', value))
"""
Patch :mod:`pyyaml` to allow using with :obj:`OrderedDict`

See: https://stackoverflow.com/a/16782282
"""
