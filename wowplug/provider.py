#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-30 13:11
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
"""
provider.py
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import requests
import functools
import logging
# import json
import io
import zipfile
import re
import os
# import errno
import posixpath
# from .yaml import yaml
from .config import config


def urljoin(*args):
    return posixpath.join(*[a.strip("/") for a in args])


class AddonProvider(object):

    is_concrete_provider = False
    _providers = []

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.is_concrete_provider:
            cls._providers.append(cls())

    @classmethod
    def providers(cls):
        return cls._providers

    @property
    def name(self):
        return self.__class__.__name__


class GithubProvider(AddonProvider):
    repo_url_base = 'https://api.github.com/repos'
    content_url = "contents"

    @classmethod
    def create(cls, spec):
        logger = logging.getLogger("provider")
        name = spec['repo'].strip("/").split("/")[-1]
        gp = type(name, (cls, ), {
            'is_concrete_provider': True,
            'repo': spec['repo'],
            'addon_path': spec['addon_path'],
            })
        logger.debug("create github provider {}".format(name))
        return gp

    @functools.lru_cache()
    def addons(self):
        url = urljoin(
                self.repo_url_base, self.repo,
                self.content_url, self.addon_path)
        r = requests.get(url)
        if r.status_code == 404 or 'message' in r:
            self.logger.warning("unable to get addon list at {}".format(url))
            return {}
        a = {c['name']: c for c in r.json()}
        self.logger.debug("addons available at {}:\n{}".format(
            url, '\n'.join(a.keys())))
        return a

    def has_addon(self, name):
        return name in self.addons()

    def spec(self):
        return dict(repo=self.repo, addon_path=self.addon_path)


class CurseForge(AddonProvider):
    # search_url = 'https://wow.curseforge.com/search/get-results?'
    is_concrete_provider = True
    url_base = 'https://www.curseforge.com'
    search_url = 'wow/addons/search?'

    def __init__(self):
        super().__init__()
        # methods for querying curseforge site
        self.render_class = None
        self.parser_class = None
        self.fuzzy_match = None
        try:
            from . import qt_web
            from bs4 import BeautifulSoup
            from fuzzywuzzy import process
            self.render_class = qt_web.Render
            self.parser_class = BeautifulSoup
            self.fuzzy_match = process.extract
        except ImportError:
            self.logger.warning(
                    "unable to initialize web renderer modules. "
                    "Curseforge searching will be unavailable. To enable"
                    " this feature, install PyQt5, BeautifulSoup, and"
                    " fuzzywuzzy")

    def has_addon(self, name):
        # query the CurseForge site
        self.logger.debug("search `{}` in CurseForge".format(name))
        cands = self.search(name)
        # do fuzzy search if there is no hit
        if cands is None:
            _cands = []
            keys = self.make_fuzzy_search_keys(name)
            if not keys:
                return False
            self.logger.debug("no hit. try fuzzy search keys: {}".format(
                keys))
            for key in keys:
                cand = self.search(key)
                if cand is not None:
                    _cands.extend(cand)
            # remove duplicates
            seen = set()
            cands = []
            for c in _cands:
                if not c['curse_name'] in seen:
                    cands.append(c)
                    seen.add(c['curse_name'])
            if not cands:
                self.logger.debug("still no hit. give up")
                return False
        # get a fuzzy match to the candidates
        sorted_cursenames = self.fuzzy_match(
                name, [c['curse_name'] for c in cands])
        self.logger.debug("addon candidates for `{}`:\n{}".format(
            name, '\n'.join([n[0] for n in sorted_cursenames])))
        # download the zip file one by one and examine the match
        min_score = config.get("curseforge.match.min_score")
        max_try = config.get("curseforge.match.max_try")
        for i, (curse_name, score) in enumerate(sorted_cursenames):
            if score < min_score or i > max_try:
                break
            addons = self.addons(curse_name)
            if addons is None:
                continue
            addons, addonsinfo = addons
            self.logger.debug("{} contains {}".format(curse_name, addons))
            if name in addons:
                return True
        return False

    @functools.lru_cache()
    def addons(self, name):
        self.logger.debug("looking for addon names in {}".format(name))
        dl_url = '{}/wow/addons/{}/download'.format(self.url_base, name)
        re_file_url = r'href="(/wow/addons/{}/download/\d+/file)"'.format(
                name)
        r = requests.get(dl_url)
        if r.ok:
            file_url = re.search(re_file_url, r.text)
            if file_url is None:
                self.logger.debug("unable to get file url")
                return
            file_url = file_url.group(1)
        else:
            self.logger.debug("unable to get download page")
            return
        # query file
        file_url = urljoin(self.url_base, file_url)
        r = requests.get(file_url)
        if r.ok:
            zn = r.url.split("/")[-1]
            ver = os.path.splitext(zn)[0].rsplit('-', 1)[-1]
            zf = zipfile.ZipFile(io.BytesIO(r.content))
            zf.filename = zn
            self.logger.debug("downloaded zip {}, ver={}".format(zn, ver))
            # get a list of addon names provided
            tocs = [f for f in zf.namelist() if f.lower().endswith('.toc')]
            self.logger.debug("tocs in zip: {}".format(tocs))
            addons = [os.path.split(t)[-2] for t in tocs]
            self.logger.debug("addons in zip: {}".format(addons))
            return addons, {'version': ver, 'zipfile': zf}

    @functools.lru_cache()
    def search(self, key):
        if self.render_class is None:
            return None
        render = self.render_class()
        render.query(urljoin(self.url_base, self.search_url), params={
                    'search': key,
                    # 'providerIdent': 'projects'
                    })
        return self.parse_search_result(render.html, search_key=key)

    def parse_search_result(self, html, **kwargs):
        soup = self.parser_class(html, 'html.parser')
        logger = self.logger
        logger.debug("parse search result for `{}`".format(
            kwargs['search_key']))
        tbl = soup.select("ul.listing.listing-project.project-listing")
        if len(tbl) == 0:
            logger.debug("no table listing found")
            return None
        if len(tbl) > 1:
            logger.debug("multiple addon listing found."
                         " the first one is used.")
        tbl = tbl[0]
        rows = tbl.select("li.project-list-item")
        if len(rows) == 0:
            logger.debug("finish with no results row found")
            return None
        # construct addon info dict
        addons = []
        for row in rows:
            addon = kwargs.copy()
            details = row.select('div.list-item__details')[0]
            link = details.select('a[href^="/wow/addons/"]')[0]
            addon['curse_display_name'] = link.select('.list-item__title'
                                                      )[0].string.strip()
            addon['curse_url'] = link['href']
            addon['curse_name'] = addon['curse_url'].split("/")[-1]
            stats = details.select('p.list-item__stats')[0]
            s_d = stats.select('span.count--download')[0].string.strip()
            s_u = stats.select('span.date--updated abbr.standard-datetime'
                               )[0]['title'].strip()
            s_c = stats.select('span.date--created abbr.standard-datetime'
                               )[0]['title'].strip()
            addon['curse_stats'] = {
                    'count_download': int(s_d.replace(",", '')),
                    'date_updated': s_u,
                    'date_created': s_c,
                    }
            desc = details.select('div.list-item__description')[0]
            addon['curse_description'] = desc.select('p')[0]['title']
            cats = row.select(
                    'div.list-item__categories a.category__item')
            addon['curse_categories'] = [
                    c['href'].split('/')[-1] for c in cats]
            dl = row.select(
                    'div.list-item__actions a.button--download')[0]
            addon['curse_download_url'] = urljoin(self.url_base, dl['href'])
            # addon['curse_download_url_params'] = json.loads(
            #         dl['data-action-value'])
            addons.append(addon)
        return addons

    def make_fuzzy_search_keys(self, name):
        blacklist = config.get('curseforge.search.blacklist')
        if blacklist is None:
            blacklist = []
        blacklist = list(map(str.lower, blacklist))
        name = name.lower()
        norm_name = re.sub(r'(\W|_)+', ' ', name).strip()
        stems = norm_name.split()
        if norm_name not in stems:
            stems.insert(0, norm_name)
        if name in stems:
            stems.remove(name)
        return [s for s in stems if s not in blacklist and s != name]
