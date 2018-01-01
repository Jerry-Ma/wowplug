#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-27 12:08
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
"""
config.py
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import errno
import logging
from appdirs import AppDirs
from .yaml import yaml


class Config(object):

    dirs = AppDirs("wowplug", "jerryma")
    _DEFAULT_FILENAME = "wowplug.yaml"

    default_content = """# {}
scan:
    dir:

sync:
    file:

github_providers:
  - repo: fgprodigal/RayUI
    addon_path: Interface/AddOns

curseforge:
    search:
        blacklist: [option, options, ui, core, data, the]
    match:
        min_score: 80
        max_try: 5
    """.format(_DEFAULT_FILENAME)

    load_saved_config = False

    @property
    def default_filepath(self):
        return os.path.abspath(os.path.join(
                self.dirs.user_config_dir, self._DEFAULT_FILENAME))

    def __init__(self, config_file=None):
        self.logger = logging.getLogger("config")
        if config_file is None:
            self.filepath = self.default_filepath
        else:
            self.filepath = os.path.abspath(os.path.expanduser(config_file))
        self._config = None  # lazy load

    def load(self):
        self._config = yaml.load(self.default_content)
        if os.path.exists(self.filepath) and self.load_saved_config:
            try:
                with open(self.filepath, 'r') as stream:
                    self._config.update(yaml.safe_load(stream))
                self.logger.debug("load config from {}".format(self.filepath))
                return
            except TypeError:
                self.logger.warning("discard corrupted config file {}".format(
                    self.filepath))
        self.logger.debug("load empty config")

    def get(self, keys):
        if self._config is None:
            self.load()
        keys = keys.split('.')
        ret = self._config[keys[0]]
        for k in keys[1:]:
            ret = ret[k]
        return ret

    def set(self, keys, value):
        if self._config is None:
            self.load()
        keys = keys.split('.')
        d = self._config
        nk = len(keys)
        for i, k in enumerate(keys):
            if i + 1 == nk:  # last
                d[k] = value
            else:
                d = d[k]

    def save(self):
        s = yaml.safe_dump(self._config, default_flow_style=False)
        f = self.filepath
        self.logger.debug("save config to {}".format(f))
        if not os.path.exists(os.path.dirname(f)):
            try:
                os.makedirs(os.path.dirname(f))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        with open(f, 'w') as fo:
            fo.write(s)


config = Config()
