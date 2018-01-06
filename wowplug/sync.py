#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2018-01-04 14:40
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os
from datetime import datetime
import hashlib
import base64
import concurrent.futures
from .terminalsize import get_terminal_size
from .provider import AddonProvider
from .config import config
from .utils import tabulate_listofdicts, mkdirs, log_and_raise, zipdir
from .scan import scan


def sync(sdict, target=None, update=False, delete=False):
    logger = logging.getLogger("sync")
    # create sources
    sources = []
    for provider in AddonProvider.providers.values():
        if provider.name not in sdict:
            logger.debug("no source of provider {}".format(provider.name))
            continue
        for k in sdict[provider.name]:
            sources.append(provider.source_class(provider, k))
    logger.info("sources found:\n{}".format(
        tabulate_listofdicts(
            sources,
            [
                ("Provider", lambda d: d.provider.name),
                ("Name", lambda d: d.name),
                ],
            showindex='always',
            )
        ))
    # self.logger("sour")
    #     pdict = sources
    #     pdict = sources.get(provider.name, None)
    #     provider.setup_sources(toc_names)
    if target is None:
        return
    logger.debug("sync addons to {}".format(target))
    # scan target to get the tocs
    if os.path.exists(target):
        try:
            addons = scan(target)
        except RuntimeError:
            # guards around good directories
            if os.listdir(target):
                log_and_raise(
                        logger.warning,
                        "sync target {} is not empty and appears"
                        " to be NOT an addon directory".format(target),
                        RuntimeError
                        )
            addons = []
        # back up if has addons
        if addons:
            # look in to cachedir for backups
            bak = zipdir(target)
            bak_content = bak.read()
            sha = base64.urlsafe_b64encode(
                    hashlib.sha256(bak_content).digest()).decode('ascii')
            # check existence with the coded sha in the filename
            oldbak = [f for f in config.get_from_cachedir("AddOns_*.zip")
                      if sha in f]
            if not oldbak:
                # create backup
                bakfile = "AddOns_{}_{}.zip".format(
                        datetime.now().strftime("%Y%m%d-%H%M%S"), sha)
                logger.debug("backup to {}".format(bakfile))
                config.save_to_cachedir(bakfile, bak_content)
                logger.debug("successfully created backup")
            else:
                logger.debug("backup exist {}, skip".format(oldbak[0]))
    else:
        # create target dir
        mkdirs(target)
        logger.debug("created target dir {}".format(target))
        addons = []
    # sync the sources to target
    # for source in sources[2:]:
    #     source.sync(target)

    # get a smarter update of the screen
    def _status():
        return tabulate_listofdicts(
            sources,
            [
                ("Provider", lambda d: d.provider.name),
                ("Name", lambda d: d.name),
                ("Sync Status", lambda d: d.sync_status['message']),
                ("AddOns", lambda d: '\n'.join(d.sync_status['dirs'])),
                ],
            showindex='always',
            ).strip("\n")
    try:
        sizex, sizey = get_terminal_size()

        def pformat_status():
            st = _status()
            sts = st.split('\n')
            sy = len(sts)  # + 1  # take into account the title line
            pady = sizey - sy
            if pady < 0:
                return st
            sx = max(map(len, sts))
            if sizex < sx:
                return st
            # do padding
            return '{}\n{}'.format('\n' * pady, st)
    except RuntimeError:
        def pformat_status():
            return _status()

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="loader") as executor:
        fs = {executor.submit(s.sync, target): s for s in sources}
        for f in concurrent.futures.as_completed(fs):
            try:
                f.result()
            except Exception as exc:
                logger.exception('{} generated an exception: {}'.format(
                    fs[f].name, exc))
            else:
                logger.info('finished sync {}'.format(fs[f].name))
            # print("Status:\n{}".format(pformat_status()))
            print("{}".format(pformat_status()))
