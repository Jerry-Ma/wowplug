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

To make the [Curseforge](https://www.curseforge.com/wow/addons) queries,
additional packages have to be installed:

* `PyQt5`

    This can be installed via `yum` or `apt-get` on Linux, and
    `homebrew` on MacOS.

* `BeautifulSoup` and `fuzzywuzzy`:

        $ pip install beautifulsoup4 fuzzywuzzy[speedup]


Usage
------

```text
$ wowplug --help
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
