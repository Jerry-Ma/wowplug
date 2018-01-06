wowplug
===============================

Overview
--------

`wowplug` is an addon manager for World of Warcraft.

Installation
--------------------

To install use pip:

    $ pip install wowplug


Or clone the repo:

    $ git clone https://github.com/Jerry-Ma/wowplug.git
    $ python setup.py install

Usage
------

```text
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

Available commands:

scan:

    Scan <dir> to get a list of installed addons. If no <dir> is
    given, try to scan the previously scanned one if applicable.

    Usage:
        wowplug scan [<dir>] [--output=<file>]

    Options:
        -h --help           Show this message.
        -o <file> --output=<file>
                            Dump the scan result to a file.
                            This file can be used for `sync`.
sync:

    Sync the addons listed in <file> to an AddOns directory. If
    no <file> is given, sync the previously synced one or the one
    generated by the last run of `scan`. Addons that are not in the
    list will be moved to directory `wowplugcache`. Addons that
    are in the list but do not exist in the AddOns directory or
    `wowplugcache` will be downloaded and installed.

    Usage:
        wowplug sync [<file>] [--update] [--delete] [--target=<dir>]

    Options:
        -h --help           Show an extensive help message
        -u --update         Update outdated addons if possible.
        -d --delete         Delete the unused addons instead of
                            placing them in `wowplugcache`.
        -t <dir> --target=<dir>
                            Sync to the set <dir> instead of the
                            `config.scan.dir` specified in <file>.
clean:

    Sync the <file> as if all addons listed in <file> were
    disabled. This will move all addons to `.wowplugcache`

    Usage:
        wowplug clean [<file>] [--delete]

    Options:
        -h --help           Show this message.
        -d --delete         Delete the unused addons instead of
                            placing them in `.wowplugcache`
```

Contributing
------------

TBD

Example
-------

TBD
