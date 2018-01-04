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
from .utils import yaml
from .provider import AddonProvider


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
    logger.debug("scan dir {}".format(addondir))

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
    logger.info("addons found in {}:\n".format(addondir) + "\n".join(summary))
    # handle output
    if output_file is None:
        return
    output = OrderedDict()  # hold the output
    collected = set()  # used to keep track of uncollected addons
    logger.debug("available providers: {}".format(
        list(AddonProvider.providers.keys())))
    # go through the providers and collect the addons
    tocs = [a['toc_name'] for a in addons]
    for provider in AddonProvider.providers.values():
        provider.setup_sources(tocs)
        logger.debug("collect addons to {}".format(provider.name))
        pdict = OrderedDict()
        for source in provider.sources.values():
            alist = []
            for addon in addons:
                name = addon['toc_name']
                if source.has_toc(name):
                    alist.append(name)
                    collected.add(name)
            if not alist:
                continue
            # format alist to one line string
            pdict[source.name] = alist
            # append some metadata
            # for metakey, metaval in provider.metadata.items():
            #     pdict[metakey] = metaval
        output[provider.name] = pdict

    # add the rest under skipped key
    output['skipped'] = []
    for addon in addons:
        name = addon['toc_name']
        if name not in collected:
            output['skipped'].append(name)
    # append some config data
    output['config'] = {'scan': {'dir': scandir}}
    # dump to output_file
    y = yaml.safe_dump(output, default_flow_style=False)
    with open(output_file, 'w') as fo:
        fo.write(y)
    logger.info("dump to {}:\n{}".format(output_file, y))


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
