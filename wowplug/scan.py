#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-27 13:18
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import re
import glob
import logging
from collections import OrderedDict

from .utils import yaml, tabulate_listofdicts
from .provider import AddonProvider
from .config import config


def scan(scandir, output=None):
    """Scan a directory for WOW addons.

    This function uses :mod:`asyncio` for better performance.

    :param output: If not ``None``, compose a YAML file containing the
        found addons. This file can be used as input of subcommand
        `sync`.
    """
    logger = logging.getLogger('scan')
    logger.info("look into {}".format(scandir))
    addons = []
    for toc_name in glob.glob(os.path.join(scandir, "*/*.[tT][oO][cC]")):
        toc = resolve_addon(toc_name)
        if 'error' in toc:
            logger.info("discard {} due to {}".format(
                toc_name, toc['error']))
            continue
        addons.append(toc)
    if not addons:
        raise RuntimeError("no addon found in {}".format(scandir))
    logger.info("addons found:\n{}".format(
        tabulate_listofdicts(
            addons,
            [
                ("Interface", lambda d: d['toc'].get('Interface', 'N/A')),
                ("Version", lambda d: d['toc'].get('Version', 'N/A')),
                ("Name", 'toc_name')
                ],
            showindex='always',
            )
        ))
    if output is None:
        return addons
    # compose output YAML
    sdict = OrderedDict([('skipped', [])])
    toc_names = [a['toc_name'] for a in addons]
    # go through the providers and collect the addons
    for provider in AddonProvider.providers.values():
        provider.setup_sources(toc_names)
        logger.debug("collect addons to {}".format(provider.name))
        pdict = OrderedDict()
        for source in provider.sources.values():
            alist = []
            for toc_name in toc_names:
                if source.has_toc(toc_name):
                    alist.append(toc_name)
                    # remove from the skipped list
                    if toc_name in sdict['skipped']:
                        sdict['skipped'].remove(toc_name)
            if not alist:
                continue
            pdict[source.name] = alist
        sdict[provider.name] = pdict
    # append some config data
    sdict['config'] = {
            'scan': {'dir': scandir},
            'cache': {'dir': config.get("cache.dir")}
            }
    # dump to output_file
    out = yaml.safe_dump(sdict, default_flow_style=False)
    with open(output, 'w') as fo:
        fo.write(out)
    logger.info("dump to {}:\n{}".format(output, out))


def resolve_addon(toc):
    """Parse the TOC file of an addon to get meta data.
    """
    tocdir, tocbase = os.path.split(toc)
    tocstem = os.path.splitext(tocbase)[0]
    info = {
            'toc_path': toc,
            'toc_dir': tocdir,
            'toc_name': tocstem,
            }
    if tocstem != os.path.basename(tocdir):
        return dict(
                info, error="mismatch TOC and directory name")
    # parse TOC
    info['toc'] = {}
    re_hdr = re.compile(r'^##\s*(\w+)\s*:\s*(.+)$')
    logger = logging.getLogger('resolve')
    logger.info("read {}".format(toc))
    with open(toc, 'r') as fo:
        try:
            for ln in fo.readlines():
                m = re_hdr.match(ln)
                if m is None:
                    continue
                info['toc'][m.group(1)] = m.group(2).strip()
        except UnicodeDecodeError:
            pass
    return info
