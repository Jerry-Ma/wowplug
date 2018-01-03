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
import yaml
from collections import OrderedDict


__all__ = [
        'instance_method_lru_cache', 'log_and_raise',
        'urljoin', 'norm_path', 'yaml']


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


def urljoin(*args):
    """Join URL segments and *ignore* the leading slash ``/``."""
    return posixpath.join(*[a.rstrip("/") if i == 0 else a.strip("/")
                            for i, a in enumerate(args)])


def norm_path(p):
    """Return absolute path with user ``~`` expanded for path `p`."""
    return os.path.abspath(os.path.expanduser(p))


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
