#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Create Date    :  2017-12-28 10:00
# Git Repo       :  https://github.com/Jerry-Ma
# Email Address  :  jerry.ma.nk@gmail.com
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import sys

from PyQt5.QtCore import QUrl, QUrlQuery
from PyQt5.QtWebEngineWidgets import (
        QWebEngineProfile, QWebEnginePage)
from PyQt5.QtWidgets import QApplication


__all__ = ['Renderer', ]


class Renderer(QWebEnginePage):
    """Class to render a remote site."""

    _UA = ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36"
           " (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36")

    def __init__(self):
        self.logger = logging.getLogger("qwebpage")
        self.html = None
        global _app
        _app = QApplication.instance()
        if _app is None:
            self.logger.debug("create qt app for qwebpage")
            argv = [sys.argv[0], ]
            _app = QApplication(argv)
        QWebEngineProfile.defaultProfile().setHttpUserAgent(self._UA)
        QWebEnginePage.__init__(self)
        self.loadFinished.connect(self._loadFinished)

    def query(self, url, params):
        """Load `url` with `params` and make the contents available
        through :attr:`self.html` upon finishing. This method blocks until
        the content is loaded."""
        u = QUrl(url)
        q = QUrlQuery()
        for k, v in params.items():
            q.addQueryItem(k, v)
        u.setQuery(q)
        self.logger.debug("load url {}".format(u.toDisplayString()))
        self.load(u)
        global _app
        _app.exec_()

    def _loadFinished(self, result):
        # This is an async call, you need to wait for this
        # to be called before closing the app
        self.toHtml(self._callable)

    def _callable(self, data):
        self.html = data
        self.logger.debug("finished loading {} KB data".format(
            len(data) // 1000))
        # Data has been stored, it's safe to quit the app
        global _app
        _app.quit()

    def javaScriptConsoleMessage(self, lvl, msg, line, src):
        """Re-implement to avoid print warnings from the chromium engine."""
        pass
