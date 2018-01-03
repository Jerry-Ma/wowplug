#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-26 21:51
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from collections import OrderedDict
import os
import sys
import inspect
import logging
import logging.config
from textwrap import indent
import pkg_resources
from docopt import docopt
from schema import Schema, Or, SchemaError
from .utils import norm_path


__all__ = ['cli', ]

LOGGER_NAME = 'cli'


def cli():
    """Command line interface of :mod:`wowplug`. Run

    .. code-block:: sh

        $ wowplug --help

    for an extensive description.
    """
    doc = """
An addon manager for World of Warcraft.

Usage:
    wowplug -h
    wowplug --help
    wowplug (-v|--version)
    wowplug [(-d|--debug)] [(-n|--ignore-config)] <command> [<args>...]

Options:
    -h                  Show this message.
    --help              Show a more detailed help message
    -v --version        Show version.
    -d --debug          Show debug messages.
    -n --ignore-config  Ignore previously saved config file
"""

    cmderr_fmt = "ERROR: {}"
    cmds = OrderedDict()

    def register_cmd(cmd):
        def wrapper(func):
            cmds[cmd] = func
            return func
        return wrapper

    @register_cmd('scan')
    def cmd_scan(args):
        """
Scan <dir> to get a list of installed addons. If no <dir> is
given, try to scan the previously scanned one if applicable.

Usage:
    wowplug scan [<dir>] [--output=<file>]

Options:
    -h --help           Show this message.
    -o <file> --output=<file>
                        Dump the scan result to a file.
                        This file can be used for `sync`.
"""
        args, fc, tc = _sync_args_with_config(
                args, config,
                {
                    # use config entry if <dir> not specified
                    # always update config entry
                    '<dir>': {
                        'key': 'scan.dir',
                        'norm': lambda v: v,
                        'from': lambda a, c: a is None,
                        'to': lambda a, c: True,
                        },
                    # do not use config entry
                    # update to config entry if specified
                    '--output': {
                        'key': 'sync.file',
                        'norm': norm_path,
                        'from': lambda a, c: False,
                        'to': lambda a, c: a is not None,
                        },
                    }
                )
        # validate the args
        args = Schema({
            '<dir>': Or(
                os.path.isdir,
                error="`{}` is not a valid directory".format(args['<dir>'])
                      if '<dir>' not in fc else
                      "no valid directory found in saved config {} from"
                      " previous scan. one has to be specified via"
                      " command line".format(config.filepath)),
            '--output': object,
            }, ignore_extra_keys=True).validate(args)
        from . import scan
        scan.scan(args['<dir>'], output_file=args['--output'])

    @register_cmd('sync')
    def cmd_sync(args):
        """
Sync the enabled addons listed in <file> to the addons
directory. If no <file> is given, sync the previously synced
one. Addons that are not in <file> or are disabled will be
moved to directory `.wowplugcache`. Addons that do not exist
in the addons directory or `.wowplugcache` will be downloaded
and installed.

Usage:
    wowplug sync [<file>] [--update] [--delete] [--clean] [--output=<dir>]

Options:
    -h --help           Show an extensive help message
    -u --update         Update outdated addons if possible.
    -d --delete         Delete the unused addons instead of
                        placing them in `.wowplugcache`.
    -o <dir> --output=<dir>
                        Sync to the set <dir> instead of the
                        scan <dir> specified in <file>.
"""
        pass

    @register_cmd('clean')
    def cmd_clean(args):
        """
Sync the <file> as if all addons listed in <file> were
disabled. This will move all addons to `.wowplugcache`

Usage:
    wowplug clean [<file>] [--delete]

Options:
    -h --help           Show this message.
    -d --delete         Delete the unused addons instead of
                        placing them in `.wowplugcache`
"""
        pass

    # process main doc
    version = pkg_resources.get_distribution("wowplug").version
    args = docopt(doc, version=version, options_first=True, help=False)
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'short': {
                'format': '%(levelname)s: %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'class': 'logging.StreamHandler',
                'formatter': 'short',  # standard
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': "DEBUG" if args['--debug'] else "INFO",
                'propagate': False
            },
        }
    })
    if args['-h']:
        print(doc.strip("\n"))
        sys.exit(0)
    if args['--help']:
        # concat all docs in cmds
        fdoc = "{}\nAvailable commands:\n\n".format(doc)
        for cmd, cmd_func in cmds.items():
            fdoc += "{}:\n\n{}\n".format(
                    cmd, indent(cmd_func.__doc__, "    ").strip('\n'))
        print(fdoc.strip("\n"))
        sys.exit(0)
    # execute command
    from .config import config
    config.load_saved_config = not args['--ignore-config']
    cmd = args['<command>']
    argv = [cmd, ] + args['<args>']
    if cmd in cmds:
        cmd_func = cmds[cmd]
        try:
            cmd_func(docopt(cmd_func.__doc__, argv=argv))
        except SchemaError as e:
            sys.exit("{}\n\n{}".format(
                cmderr_fmt.format(e.code),
                cmds[cmd].__doc__.strip("\n"),
                ))
        except Exception as e:
            f_locals = inspect.trace()[-1][0].f_locals
            if 'logger' in f_locals:
                logger = f_locals['logger']
            elif 'self' in f_locals:
                logger = getattr(f_locals['self'], "logger", None)
            else:
                logger = None
            if logger is not None:
                sys.exit(logger.exception(e))
            else:
                raise
    else:
        sys.exit(cmderr_fmt.format(
            "`{}` is not a valid wowplug command. See 'wowplug -h'."
            .format(cmd)))
    # save config file on exit
    config.save()


# some internal stuff

def _sync_args_with_config(args, config, sync_policy):
    logger = logging.getLogger(LOGGER_NAME)
    fc = []
    tc = []
    for ak, sp in sync_policy.items():
        ck, nm, ff, tf = sp['key'], sp['norm'], sp['from'], sp['to']
        av, cv = args[ak], config.get(ck)
        if ff(av, cv):
            logger.debug("sync {}=`{}` in config {} to `{}`".format(
                ck, cv, config.filepath, ak))
            args[ak] = config.get(ck)
            fc.append(ak)
        if tf(av, cv):
            logger.debug("sync {}=`{}` to `{}` in config {}".format(
                ak, av, ck, config.filepath))
            args[ak] = nm(args[ak])
            config.set(ck, args[ak])
            tc.append(ak)
    return args, fc, tc
