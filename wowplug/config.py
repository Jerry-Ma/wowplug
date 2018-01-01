#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-27 12:08
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import errno
import logging
from appdirs import AppDirs
from .omap_yaml import yaml


__all__ = ['Config', 'config']


class Config(object):
    """Class that configures :mod:`wowplug`.
    """

    _dirs = AppDirs("wowplug", "jerryma")
    """An :obj:'AppDirs' object that provide the conventional path to store
    the config. See documentations of :mod:`appdirs` for details"""

    _default_filename = "wowplug.yaml"

    load_saved_config = False
    """Prevent from loading the saved config file if `False`, which is
    the default."""

    @property
    def default_content(self):
        """Default empty configuration."""
        return """# {}
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
    """.format(self._default_filename)

    @property
    def default_filepath(self):
        """Directory to which the config file is saved."""
        return os.path.abspath(os.path.join(
                self._dirs.user_config_dir, self._default_filename))

    def __init__(self, config_file=None):
        """Create a `Config` object. If `config_file` is set, entries
        within will override the default ones. The config is
        not loaded until `get` or `set` is called.
        """
        self.logger = logging.getLogger("config")
        if config_file is None:
            self.filepath = self.default_filepath
        else:
            self.filepath = os.path.abspath(os.path.expanduser(config_file))
        self._config = None  # lazy load

    def load(self):
        """Actually load the config. This will be done at the first call
        of `get` or `set`"""
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
        """Return the config entry specified by `keys`

        :param keys:
            keys of the entry. multi-level keys is supported
            using format like ``key1.key2``.
        """
        if self._config is None:
            self.load()
        keys = keys.split('.')
        ret = self._config[keys[0]]
        for k in keys[1:]:
            ret = ret[k]
        return ret

    def set(self, keys, value):
        """Set `value` to config entry specified by `keys`.

        :param keys:
            keys of the entry. multi-level keys is supported
            using format like ``key1.key2``.
        :param value:
            value to be set.
        """
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
        """Save the config to the default save path. See document
        of `appdirs` for details.
        """
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
"""A shared instance of :obj:`Config` object."""
