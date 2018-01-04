#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2018-01-04 14:40
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging


def sync(addonfile, syncdir, update=False, delete=False):
    logger = logging.getLogger("sync")
    logger.debug("sync addons in {} to {}".format(addonfile, syncdir))
