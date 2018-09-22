#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-30 13:11
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import io
from zipfile import ZipFile
import re
import os
import glob
import abc
from collections import OrderedDict
from inspect import isabstract
import concurrent.futures
import shutil

import requests
from bs4 import BeautifulSoup
import fuzzywuzzy.process

from .config import config
from .utils import (
        instance_method_lru_cache, log_and_raise, urljoin,
        unzipdir, linkdir,
        run_and_log, expanded_abspath)


__all__ = [
        'AddonProvider', 'AddonSource',
        'Github', 'GithubRepo',
        'Curseforge', 'CurseProject',
        ]


class AddonProvider(abc.ABC):
    """Abstract base class that all provider classes should be
    derived from.

    It manages a list of available concrete providers at class level, and a
    list of available addon sources at instance level.
    """

    providers = OrderedDict()
    """Dict of available :obj:`AddonProvider` instances."""

    session = requests.Session()
    """:obj:`requests.Session` object to be used for the sources to query
    remote websites."""

    @property
    def source_class(self):
        """Class of the sources this provider provides."""
        return AddonSource

    @abc.abstractproperty
    def name(self):
        """Convenience attribute to the name of the class. It is used
        as the key to identify the provider."""
        return NotImplemented

    @abc.abstractproperty
    def metadata(self):
        """Dict of some useful information."""
        return NotImplemented

    @abc.abstractmethod
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._sources = OrderedDict()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        logger = logging.getLogger(AddonProvider.__name__)
        if not isabstract(cls):
            if cls.name in cls.providers:
                logger.warning(
                        "name collision when adding provider {}".format(
                            cls.name))
            cls.providers[cls.name] = cls()

    @abc.abstractmethod
    def setup_sources(self, toc_names):
        """Create and setup a list of :obj:`AddonSource` instances
        that *may* provide the addons with TOCs `toc_names`.

        This method shall be implemented by subclasses and ended with
        a call to :meth:`_finish_setup_sources` to make the sources
        available in :attr:`sources`.
        """
        return NotImplemented

    def _finish_setup_sources(self, sources):
        """Make `sources` available to :meth:`sources` method.

        Subclass should call this method at the end of its implementation of
        :meth:`setup_sources`.
        """
        self.logger.debug("setup sources for {}: {}".format(
            self.name, [s.name for s in sources]))
        for source in sources:
            if source.name in self._sources:
                self.logger.warning(
                        "name collision when setup source {}".format(
                            source.name))
            self._sources[source.name] = source
        self.logger.debug("sources added to {}: {}".format(
            self.name, [s.name for s in self.sources.values()]))

    @property
    def sources(self):
        """Return a list of available :obj:`AddonSource` instances.

        .. note::

            The returned list is only populated after the call of
            :meth:`setup_sources`, which should be decorated with
            :meth:`_finish_setup_sources`.
        """
        return self._sources

    def hastoc(self, toc_name):
        """Return ``True`` if the sources of this provider provide addon
        of TOC `toc_name`."""

        return any(s.hastoc(toc_name) for s in self.sources)


class AddonSource(abc.ABC):
    """Abstract base class of classes that provide access to addons.
    """

    @abc.abstractproperty
    def name(self):
        """Name to identify the addon source."""
        return NotImplemented

    @abc.abstractproperty
    def addons(self):
        """A list of addons provided by the sources."""
        return NotImplemented

    def __init__(self, provider):
        """
        :param provider: provider this addon source belongs to.

        :ivar sync_status: Usually is ``None``, will be set
            to something meaningful after call of :meth:`sync`.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.provider = provider
        self._reset_sync_status()
        self.logger.debug("create addon source {}".format(self.name))

    @abc.abstractmethod
    def sync(self, target):
        """Sync the source of this addon to directory `target`."""
        return NotImplemented

    def _reset_sync_status(self):
        self.sync_status = {
                'message': None,
                'dirs': [],
            }

    def _set_sync_status(self, message, dirs):
        self.sync_status = {
                'message': message,
                'dirs': dirs}

    def synczip(self, target, pattern='*'):
        """Sync ZIP source of this addon to directory `target`.

        May be called within the implementation of :meth:`sync`.
        """
        if not hasattr(self, 'zipurl'):
            raise NotImplementedError(
                    '`zipurl` has to be implemented to run `synczip`')
        self.logger.debug("zip url: {}".format(self.zipurl))
        zipinfo = self.zipinfo
        zipfile = config.save_to_cachedir(
                zipinfo['name'], zipinfo['content'])
        return unzipdir(zipfile, target, pattern=pattern)

    @property
    @instance_method_lru_cache()
    def zipinfo(self):
        """Dict contains information from the source zip file. To use
        it, :attr:`zipurl` has to be implemented.

        This property is cached to avoid querying remote site
        repeatedly.
        """
        if not hasattr(self, 'zipurl'):
            raise NotImplementedError(
                    '`zipurl` has to be implemented to get zipinfo')
        self.logger.debug("retrieving files for {}".format(self.name))
        r = self.provider.session.get(self.zipurl)
        if not r.ok:
            log_and_raise(
                    self.logger.warning,
                    "unable to get {}".format(self.zipurl),
                    RuntimeError
                    )
        # process the zip file
        zipname = r.url.split("/")[-1]
        zipver = os.path.splitext(zipname)[0].rsplit('-', 1)[-1]
        zipsize = len(r.content)
        zipcontent = r.content
        zipfile = ZipFile(io.BytesIO(zipcontent))
        tocs = [f for f in zipfile.namelist() if f.lower().endswith('.toc')]
        zipfile.close()
        self.logger.debug(
                "downloaded zip {}, ver={}, size={:.2f}MB,"
                " TOCs:\n{}".format(
                    zipname, zipver, zipsize / 1e6, '\n'.join(tocs)))
        return {
                'name': zipname,
                'version': zipver,
                'content': zipcontent,
                'size': zipsize,
                'tocs': tocs,
                }

    def hastoc(self, toc_name):
        """
        Return ``True`` if the addon source provides addon with TOC of
        `toc_name`.
        """
        return toc_name in self.addons

    def __repr__(self):
        return super().__repr__().replace(self.__class__.__name__, self.name)


class Github(AddonProvider):
    """Class that manages addons provided through `Github`.

    :ivar specs: List of specs of `Github` repositories that provide addons.
        A predefined set of repositories is read from config item
        ``github.providers``
    """

    repo_url_base = 'https://api.github.com/repos'
    """URL to connect to a `Github` repository."""

    contents_url = "contents"
    """URL path to the contents of a `Github` repository."""

    zipball_url = "zipball/master"
    """URL path to the zipball of a `Github` repository."""

    name = "github"
    """Name of this provider."""

    def __init__(self):
        super().__init__()
        self.specs = config.get("github.providers")

    @property
    def source_class(self):
        """Class of the sources this provider provides."""
        return GithubRepo

    @property
    def metadata(self):
        """Dict of some useful information, include the following keys:

        * ``providers``: a list of specs of known providers.
        """
        return {'providers': self.specs}

    def setup_sources(self, toc_names):
        """Initialize sources with :attr:`self.specs`.

        .. note::

            The argument `toc_names` is ignored at this moment, i.e., only
            predefined `Github` sources from :attr:`specs` are available. In
            the future, it may allow automatic detection of the repository
            specs for TOCs `toc_names`.
        """
        sources = [self.source_class(self, spec) for spec in self.specs]
        self._finish_setup_sources(sources)


class GithubRepo(AddonSource):
    """Class that provides access to addons provided through a
    `Github` repository
    """

    def __init__(self, provider, spec, info=None):
        """
        :param spec: ``{author}/{repo_name}/{path}``, unique identifier
            to the provided addons.
        :param info: Dict of any metadata to be kept along with.

        :ivar author: Author's name.
        :ivar repo_name: Name of the repository.
        :ivar repo: ``{author}/{repo_name}``, unique identifier
            of the `Github` repository.
        :ivar path: Path relative to the repository's root
            to the folder that contains addon source files.
        :ivar gitcmd: Path to the `git` command executable.

        .. note::

            One repository may contain one or more addon folders.
        """
        self.info = {} if info is None else info
        self.spec = re.sub(r'/+', '/', spec.strip("/"))
        m = re.match(
            r'(?P<author>[^ /]+)/(?P<repo_name>[^ /]+)(?:/(?P<path>[^ ]+))?',
            self.spec)
        if m is None:
            raise RuntimeError("invalid GithubRepo source spec {}".format(
                self.spec))
        m = m.groupdict()
        self.author = m['author']
        self.repo_name = m['repo_name']
        self.path = '' if m['path'] is None else m['path']
        self.repo = "{}/{}".format(self.author, self.repo_name)
        self.gitcmd = shutil.which('git')
        super().__init__(provider)
        self.logger.debug("source {} initialized".format(self.name))

    @property
    def name(self):
        """Name to identify this addon `Github` repository."""
        # return self.repo.strip("/ ").split("/")[-1]
        return self.spec

    @property
    def addons(self):
        """Return the TOC names of addons provided in this `Github`
        repository.
        """
        try:
            return list(self.repoinfo.keys())
        except RuntimeError:
            return []

    @property
    @instance_method_lru_cache()
    def repoinfo(self):
        """Dict contains information from the repository.

        This property is cached to avoid repeatedly querying the `Github`
        site.
        """
        url = urljoin(
                self.provider.repo_url_base, self.repo,
                self.provider.contents_url, self.path)
        r = self.provider.session.get(url)
        if not r.status_code == requests.codes.ok:
            log_and_raise(
                    self.logger.warning,
                    "unable to get addons from {}".format(url),
                    RuntimeError
                    )
        addons = {c['name']: c for c in r.json()}
        self.logger.debug("addons available from {}:\n{}".format(
            url, '\n'.join(addons.keys())))
        return addons

    @property
    def zipurl(self):
        """URL to the `Github` repo zipball file.
        """
        return urljoin(
                self.provider.repo_url_base, self.repo,
                self.provider.zipball_url)

    @property
    def zipinfo(self):
        """Reimplement :attr:`AddonSource.zipinfo` to get a meaning
        full zip name instead of `master.zip`."""
        return dict(super().zipinfo, name='{}-{}.zip'.format(
            self.author, self.repo_name))

    def sync(self, target):
        """Sync the remote addons to target directory ``target``."""
        self._reset_sync_status()
        self.logger.debug("start sync to {}".format(target))
        if self.gitcmd is None:
            # get zip ball
            self.logger.debug("no git installation found. get zip file")
            pattern = os.path.join(
                    "{}-{}-*".format(self.author, self.repo_name),
                    self.path,
                    "*/*.[tT][oO][cC]")
            tgtdirs = self.synczip(target, pattern)
        else:
            clonedir = os.path.join(config.cachedir, self.repo_name)
            if os.path.exists(clonedir):
                if os.listdir(clonedir) and \
                        glob.glob(os.path.join(clonedir, '.git')):
                    self.logger.debug("update exist repo {}".format(clonedir))
                    retcode = run_and_log(
                            [self.gitcmd, '-C', clonedir, 'pull'],
                            self.logger.debug
                            )
                else:
                    raise RuntimeError(
                        "{} exist but seems not to be a "
                        "valid local git repository".format(clonedir))
            else:
                self.logger.debug("clone repo to {}".format(clonedir))
                retcode = run_and_log([
                    self.gitcmd, 'clone', 'git@github.com:{}.git'.format(
                        self.repo),
                    clonedir
                    ],
                    self.logger.debug,
                    )
            if retcode != 0:
                raise RuntimeError("error to clone or update {}".format(
                    self.repo))
            pattern = os.path.join(self.path, "*/*.[tT][oO][cC]")
            tgtdirs = linkdir(clonedir, target, pattern=pattern)
        self._set_sync_status(
                "success", [os.path.basename(d) for d in tgtdirs])


class Curseforge(AddonProvider):
    """
    Class that manages addons provided through `Curseforge`.
    """
    url_base = 'https://www.curseforge.com'
    """URL of `Curseforge` site."""

    search_url = 'wow/addons/search?'
    """URL path to the search form."""

    name = "curseforge"
    """Name of this provider."""

    def __init__(self):
        super().__init__()

    @property
    def source_class(self):
        """Class of the sources this provider provides."""
        return CurseProject

    @property
    def metadata(self):
        """Dict of some useful information."""
        return {}

    def setup_sources(self, toc_names):
        """
        Populate :attr:`sources` with a list of :obj:`CurseProject` that
        provide the addons specified with `toc_names` by searching the
        `Curseforge` site.
        """

        def _func(toc_name):
            try:
                return self.find_source(toc_name)
            except RuntimeError:
                return None

        with concurrent.futures.ThreadPoolExecutor(
                max_workers=8, thread_name_prefix="loader") as executor:
            fs = list(map(
                lambda t: executor.submit(_func, t), toc_names))
            rs = [
                    f.result() for f in concurrent.futures.as_completed(fs)
                    ]
        self._finish_setup_sources([s for s in rs if s is not None])

    def find_source(self, toc_name):
        """Return :obj:`CurseProject` instance that provides addon with TOC
        name `toc_name`.

        It first tries to search with `toc_name`, if no hit, search with some
        fuzzy keywords instead. A list of :obj:`CurseProject` will be returned
        from searching the site. The projects will be ranked according naming
        similarity and the project file will be downloaded and examined in this
        order. The first project that provides addon of TOC `toc_name` is
        returned. If no project found, raise :exc:`RuntimeError`.
        """
        self.logger.debug("search TOC `{}` in Curseforge".format(
                toc_name))
        try:
            sources = self._search(toc_name)
        except RuntimeError:
            sources = OrderedDict()
            # do fuzzy search if there is no hit
            ks = self._make_fuzzy_search_keys(toc_name)
            if not ks:
                log_and_raise(
                        self.logger.debug,
                        "unable to find source for TOC `{}`".format(toc_name),
                        RuntimeError)
            self.logger.debug(
                    "no hit. try fuzzy search with: {}".format(ks))
            for k in ks:
                try:
                    sources.update(self._search(k))
                except RuntimeError:
                    pass
            if not sources:
                log_and_raise(
                        self.logger.debug,
                        "no hit after fuzzy search. give up",
                        RuntimeError
                        )
        # do a fuzzy match between toc_name and the sources
        source_names = fuzzywuzzy.process.extract(toc_name, sources.keys())
        self.logger.debug("project candidates for TOC `{}`:\n{}".format(
            toc_name, '\n'.join([n[0] for n in source_names])))

        # examine the source projects
        min_score = config.get("curseforge.match.min_score")
        max_try = config.get("curseforge.match.max_try")
        for i, (name, score) in enumerate(source_names):
            if score < min_score or i >= max_try:
                break
            # hastoc is case sensitive
            if sources[name].hastoc(toc_name):
                self.logger.debug("found TOC {} in project {}".format(
                    toc_name, name))
                return sources[name]
        else:
            log_and_raise(
                    self.logger.debug,
                    "unable to find TOC {} after examine {} projects with "
                    "matching score greater than {}. The full candidate "
                    "list:\n{}".format(
                        toc_name, max_try, min_score, '\n'.join(
                            source_names)),
                    RuntimeError
                    )

    def _search(self, key):
        """Wrapper to make the lru cache work with params of different
        capitalization"""
        return self._search_case_insensitive(key.lower())

    @instance_method_lru_cache()
    def _search_case_insensitive(self, key):
        """Returns search result from `Curseforge` with search key `key`.

        This method is cached to avoid repeatedly querying the `Curseforge`
        site.
        """
        r = self.session.get(urljoin(
            self.url_base, self.search_url), params={
                    'search': key,
                    # 'providerIdent': 'projects'
                    })
        if not r.status_code == requests.codes.ok:
            log_and_raise(
                    self.logger.debug,
                    "unable to get search results of {}".format(key),
                    RuntimeError
                    )
        return self._parse_search_result(r.text, search_key=key)

    def _parse_search_result(self, html, **kwargs):
        soup = BeautifulSoup(html, 'html.parser')
        self.logger.debug("parse result from search of `{}`".format(
            kwargs['search_key']))
        tbl = soup.select("ul.listing.listing-project.project-listing")
        if len(tbl) == 0:
            log_and_raise(
                    self.logger.debug,
                    "no table listing found",
                    RuntimeError
                    )
        if len(tbl) > 1:
            self.logger.debug("multiple addon listing found."
                              " the first one is used.")
        tbl = tbl[0]
        rows = tbl.select("li.project-list-item")
        if len(rows) == 0:
            log_and_raise(
                    self.logger.debug,
                    "no result row is found",
                    RuntimeError
                    )
        # construct `CurseProject` objects for each row
        sources = OrderedDict()
        for row in rows:
            info = kwargs.copy()

            d_d = row.select('div.list-item__details')[0]

            d_l = d_d.select('a[href^="/wow/addons/"]')[0]
            info['url'] = d_l['href'].strip()
            info['name'] = info['url'].strip('/').split("/")[-1]
            info['display_name'] = d_l.select(
                    '.list-item__title')[0].string.strip()

            d_s = d_d.select('p.list-item__stats')[0]
            info['stats'] = {
                    'count_download': int(
                         d_s.select('span.count--download')[0].string.replace(
                             ",", "")),
                    'date_updated': d_s.select(
                        'span.date--updated abbr.standard-datetime'
                        )[0]['title'].strip(),
                    'date_created': d_s.select(
                        'span.date--created abbr.standard-datetime'
                        )[0]['title'].strip(),
                    }

            d_dc = d_d.select('div.list-item__description')[0]
            info['description'] = d_dc.select('p')[0]['title'].strip()

            d_cs = row.select('div.list-item__categories a.category__item')
            info['categories'] = [
                    d_c['href'].strip(' /').split('/')[-1] for d_c in d_cs]

            d_dl = row.select(
                    'div.list-item__actions a.button--download')[0]
            info['dlurl'] = d_dl['href'].strip()
            source = self.source_class(self, info['name'], info)
            sources[source.name] = source
        return sources

    @staticmethod
    def _make_fuzzy_search_keys(name):
        # all keys are lower case
        name = name.lower()
        blacklist = config.get('curseforge.search.blacklist')
        if blacklist is None:
            blacklist = []
        blacklist = list(map(str.lower, blacklist))
        norm_name = re.sub(r'(\W|_)+', ' ', name).strip()
        stems = norm_name.split()
        if norm_name not in stems:
            stems.insert(0, norm_name)
        if name in stems:
            stems.remove(name)
        return [s for s in stems if s not in blacklist and s != name]


class CurseProject(AddonSource):
    """Class that provides access to addons provided through `Curseforge`.
    """

    def __init__(self, provider, name, info=None):
        """
        :param name: Name of the `Curseforge` project.
        :param info: Dict of metadata of the project, composed
            from the searching page.

        .. note::

            One project may contain one or more addon folders.
        """

        self.info = {} if info is None else info
        self._name = name
        super().__init__(provider)
        self.logger.debug("source {} initialized".format(self.name))

    @property
    def name(self):
        """
        Name of the `Curseforge` project.
        """
        return self._name

    @property
    def addons(self):
        """Return the TOCs of addons provided in this `Curseforge` project.
        """
        try:
            return [os.path.split(t)[-2] for t in self.zipinfo['tocs']]
        except RuntimeError:
            return []

    @property
    def dlurl(self):
        """URL to the `Curseforge` project download page."""
        return '{}/wow/addons/{}/download'.format(
                self.provider.url_base, self.name)

    @property
    @instance_method_lru_cache()
    def dlinfo(self):
        """Dict contains information from the project download page.

        This property is cached to avoid querying `Curseforge` site
        repeatedly.
        """
        re_zipurl = r'href="(/wow/addons/{}/download/\d+/file)"'.format(
                self.name)
        r = self.provider.session.get(self.dlurl)
        if not r.ok:
            log_and_raise(
                    self.logger.warning,
                    "unable to get {}".format(self.dlurl),
                    RuntimeError
                    )
        s = re.search(re_zipurl, r.text)
        if s is None:
            log_and_raise(
                    self.logger.warning,
                    "unable to get zip file URL from {}".format(self.dlurl),
                    RuntimeError
                    )
        zipurl = urljoin(self.provider.url_base, s.group(1))
        return {'zipurl': zipurl}

    @property
    def zipurl(self):
        """URL to the `Curseforge` project zip file.
        """
        return self.dlinfo['zipurl']

    def sync(self, target):
        """Sync the remote addons to target directory ``target``."""
        self._reset_sync_status()
        self.logger.debug("sync {} to {}".format(self.name, target))
        pattern = "*/*.[tT][oO][cC]"
        tgtdirs = self.synczip(target, pattern)
        self._set_sync_status(
                "success", [os.path.basename(d) for d in tgtdirs])


class LocalDir(AddonProvider):
    """Class that manages addons provided through local filesystem.

    :ivar paths: List of directories that provide addons.
    """

    name = "local"
    """Name of this provider."""

    def __init__(self):
        super().__init__()
        self.paths = []

    @property
    def source_class(self):
        """Class of the sources this provider provides."""
        return LocalAddon

    @property
    def metadata(self):
        """Dict of some useful information.
        """
        return {}

    def setup_sources(self, toc_names):
        """Initialize sources with :attr:`self.paths`.

        .. note::

            The argument `toc_names` is ignored.
        """
        sources = [self.source_class(self, path) for path in self.paths]
        self._finish_setup_sources(sources)


class LocalAddon(AddonSource):
    """Class that provides access to addons provided through a local
    directory.
    """

    def __init__(self, provider, path, info=None):
        """
        :param path: path to the addon.
        :param info: Dict of any metadata to be kept along with.

        .. note::

            `path` should point to the addon folder itself, i.e., it
            should contain the addon's TOC file. This also means
            a :obj:`LocalAddon` always have one TOC.
        """
        self.info = {} if info is None else info
        self.path = expanded_abspath(path)
        super().__init__(provider)
        self.logger.debug("source {} initialized".format(self.name))

    @property
    def name(self):
        """Name to identify this addon `Github` repository."""
        # return self.repo.strip("/ ").split("/")[-1]
        return os.path.basename(self.path)

    @property
    def addons(self):
        """Return the TOC names of addons provided in this `Github`
        repository.
        """
        try:
            return [os.path.dirname(t) for t in glob.glob(
                os.path.join(self.path, '*.[tT][oO][cC]'))]
        except RuntimeError:
            return []

    def sync(self, target):
        """Sync the addon to target directory ``target``."""
        self._reset_sync_status()
        self.logger.debug("start sync to {}".format(target))
        pattern = os.path.join(self.path, "*.[tT][oO][cC]")
        tgtdirs = linkdir(self.path, target, pattern=pattern)
        self._set_sync_status(
                "success", [os.path.basename(d) for d in tgtdirs])
