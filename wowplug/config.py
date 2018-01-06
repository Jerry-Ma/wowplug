#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-27 12:08
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import glob
import logging
from appdirs import AppDirs
from .utils import yaml, mkdirs


__all__ = ['Config', 'config']


class Config(object):
    """Class that configures :mod:`wowplug`.
    """

    _dirs = AppDirs("wowplug", "jerryma")
    """An :obj:'AppDirs' object that provide the conventional path to store
    the config. See documentations of :mod:`appdirs` for details"""

    _default_filename = "wowplug.yaml"
    _default_cachedirname = 'wowplugcache'

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

github:
    providers:
      - fgprodigal/RayUI/Interface/AddOns

curseforge:
    search:
        blacklist: [option, options, ui, core, data, the]
    match:
        min_score: 80
        max_try: 5

cache:
    dir: {}
    """.format(self.default_filepath, self.default_cachedir)

    @property
    def default_filepath(self):
        """Default path to the saved config file."""
        return os.path.abspath(os.path.join(
                self._dirs.user_config_dir, self._default_filename))

    @property
    def default_cachedir(self):
        """Default directory to save cached files"""
        return os.path.abspath(os.path.join(
                self._dirs.user_config_dir, self._default_cachedirname))

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
            mkdirs(os.path.dirname(f))
        with open(f, 'w') as fo:
            fo.write(s)

    @property
    def cachedir(self):
        """Return the cache dir. If not yet created, create it and return."""
        d = self.get("cache.dir")
        if os.path.exists(d):
            if os.path.isdir(d):
                return d
            else:
                raise RuntimeError(
                        "unable to create cache dir {}"
                        " due to existing file of same name".format(d))
        else:
            return mkdirs(d)

    def save_to_cachedir(self, filename, content):
        """Save the file `filename` to :attr:`cachedir`"""
        cachedir = self.cachedir
        basename = os.path.basename(filename)
        if basename != filename:
            raise ValueError(
                    "filename has to be a basename, not {}".format(filename))
        outname = os.path.join(cachedir, filename)
        with open(outname, 'wb') as fo:
            fo.write(content)
        self.logger.debug("file {} size {:.2f}MB saved to {}".format(
            filename, len(content) / 1e6, cachedir))
        return outname

    def get_from_cachedir(self, pattern):
        """Get list of files matching glob pattern `pattern`
        within :attr:`cache.dir`"""
        cachedir = self.cachedir
        return glob.glob(os.path.join(cachedir, pattern))


config = Config()
"""A shared instance of :obj:`Config` object."""
