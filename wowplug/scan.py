#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-27 13:18
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
"""
scan.py
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import re
import glob
import logging
from collections import OrderedDict
from .yaml import yaml
from .provider import GithubProvider, AddonProvider
from .config import config


def scan(scandir, output_file=None):
    """Scan a directory for WOW addons."""
    logger = logging.getLogger('scan')
    parent, base = os.path.split(scandir)
    if base == "AddOns":
        addondir = scandir
    elif base == "Interface":
        addondir = os.path.join(scandir, 'AddOns')
    elif os.path.exists(os.path.join(scandir, 'Interface', 'AddOns')):
        addondir = os.path.join(scandir, 'Interface', 'AddOns')
    else:
        addondir = scandir
    logger.debug("addon dir {}".format(addondir))

    addons = []
    for toc in glob.glob(os.path.join(addondir, "*/*.toc")):
        addons.append(resolve_addon(toc))
    if not addons:
        raise RuntimeError("no addon found in {}".format(addondir))
    hdr = "# Id  Interface  Version              Name"
    fmt = "{:4d} {:>10s}  {:20s} {}"
    summary = [hdr, ]
    for i, addon in enumerate(addons):
        summary.append(fmt.format(
            i,
            addon['toc'].get('Interface', 'N/A'),
            addon['toc'].get('Version', 'N/A'),
            addon['toc_name']))
    logger.info("addons in {}:\n".format(addondir) + "\n".join(summary))
    # handle output
    if output_file is None:
        return
    # populate providers from config
    specs = config.get("github_providers")
    if specs is not None:
        for spec in specs:
            GithubProvider.create(spec)
    logger.debug("available providers: {}".format(AddonProvider.providers()))
    # dump some config entry to output as well
    output = OrderedDict()
    # go through the providers and collect the addons
    collected = set()
    for provider in AddonProvider.providers():
        pdict = []
        for addon in addons:
            name = addon['toc_name']
            if provider.has_addon(name):
                pdict.append(name)
                collected.add(name)
        output[provider.name] = pdict
    # add the rest to skipped group
    output['skipped'] = [
            a['toc_name'] for a in addons
            if a['toc_name'] not in collected]
    # for addon in addons:
    #     # here we go through the provider lists to get
    #     # a list of sources that provide this addon.
    #     name = addon['toc_name']
    #     srcs = []
    #     for provider in AddonProvider.providers():
    #         src = provider.query(name)
    #         if src is not None:
    #             srcs.append(src)
    #     output['addons'][name] = srcs
    # append some config data
    output['scan'] = {
            'dir': scandir}
    output['github_providers'] = specs
    y = yaml.safe_dump(output, default_flow_style=False)
    with open(output_file, 'w') as fo:
        fo.write(y)
    logger.info("dump to {}:\n{}".format(output_file, y))


def resolve_addon(toc):
    """parse an addon TOC file to get meta data
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
                info, state=PLUG_INVALID)
    # parse TOC
    info['toc'] = {}
    re_hdr = re.compile(r'^##\s*(\w+)\s*:\s*(.+)$')
    with open(toc, 'r') as fo:
        for ln in fo.readlines():
            m = re_hdr.match(ln)
            if m is None:
                continue
            info['toc'][m.group(1)] = m.group(2).strip()
    return info


# state constant
PLUG_INVALID = 'invalid'
PLUG_ENABLED = 'enabled'
PLUG_DISABLED = 'disabled'
PLUG_BUNDLED = 'bundled'
