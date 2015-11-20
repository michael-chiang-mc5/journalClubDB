#! /usr/bin/env python
"""
This module provides classes for querying Google Scholar and parsing
returned results. It currently *only* processes the first results
page. It is not a recursive crawler.
"""
# ChangeLog
# ---------
#
# 2.9   Fixed Unicode problem in certain queries. Thanks to smidm for
#       this contribution.
#
# 2.8   Improved quotation-mark handling for multi-word phrases in
#       queries. Also, log URLs %-decoded in debugging output, for
#       easier interpretation.
#
# 2.7   Ability to extract content excerpts as reported in search results.
#       Also a fix to -s|--some and -n|--none: these did not yet support
#       passing lists of phrases. This now works correctly if you provide
#       separate phrases via commas.
#
# 2.6   Ability to disable inclusion of patents and citations. This
#       has the same effect as unchecking the two patents/citations
#       checkboxes in the Scholar UI, which are checked by default.
#       Accordingly, the command-line options are --no-patents and
#       --no-citations.
#
# 2.5:  Ability to parse global result attributes. This right now means
#       only the total number of results as reported by Scholar at the
#       top of the results pages (e.g. "About 31 results"). Such
#       global result attributes end up in the new attrs member of the
#       used ScholarQuery class. To render those attributes, you need
#       to use the new --txt-globals flag.
#
#       Rendering global results is currently not supported for CSV
#       (as they don't fit the one-line-per-article pattern). For
#       grepping, you can separate the global results from the
#       per-article ones by looking for a line prefix of "[G]":
#
#       $ scholar.py --txt-globals -a "Einstein"
#       [G]    Results 11900
#
#                Title Can quantum-mechanical description of physical reality be considered complete?
#                  URL http://journals.aps.org/pr/abstract/10.1103/PhysRev.47.777
#                 Year 1935
#            Citations 12804
#             Versions 80
#              Cluster ID 8174092782678430881
#       Citations list http://scholar.google.com/scholar?cites=8174092782678430881&as_sdt=2005&sciodt=0,5&hl=en
#        Versions list http://scholar.google.com/scholar?cluster=8174092782678430881&hl=en&as_sdt=0,5
#
# 2.4:  Bugfixes:
#
#       - Correctly handle Unicode characters when reporting results
#         in text format.
#
#       - Correctly parse citation-only (i.e. linkless) results in
#         Google Scholar results.
#
# 2.3:  Additional features:
#
#       - Direct extraction of first PDF version of an article
#
#       - Ability to pull up an article cluster's results directly.
#
#       This is based on work from @aliparsai on GitHub -- thanks!
#
#       - Suppress missing search results (so far shown as "None" in
#         the textual output form.
#
# 2.2:  Added a logging option that reports full HTML contents, for
#       debugging, as well as incrementally more detailed logging via
#       -d up to -dddd.
#
# 2.1:  Additional features:
#
#       - Improved cookie support: the new --cookie-file options
#         allows the reuse of a cookie across invocations of the tool;
#         this allows higher query rates than would otherwise result
#         when invoking scholar.py repeatedly.
#
#       - Workaround: remove the num= URL-encoded argument from parsed
#         URLs. For some reason, Google Scholar decides to propagate
#         the value from the original query into the URLs embedded in
#         the results.
#
# 2.0:  Thorough overhaul of design, with substantial improvements:
#
#       - Full support for advanced search arguments provided by
#         Google Scholar
#
#       - Support for retrieval of external citation formats, such as
#         BibTeX or EndNote
#
#       - Simple logging framework to track activity during execution
#
# 1.7:  Python 3 and BeautifulSoup 4 compatibility, as well as printing
#       of usage info when no options are given. Thanks to Pablo
#       Oliveira (https://github.com/pablooliveira)!
#
#       Also a bunch of pylinting and code cleanups.
#
# 1.6:  Cookie support, from Matej Smid (https://github.com/palmstrom).
#
# 1.5:  A few changes:
#
#       - Tweak suggested by Tobias Isenberg: use unicode during CSV
#         formatting.
#
#       - The option -c|--count now understands numbers up to 100 as
#         well. Likewise suggested by Tobias.
#
#       - By default, text rendering mode is now active. This avoids
#         confusion when playing with the script, as it used to report
#         nothing when the user didn't select an explicit output mode.
#
# 1.4:  Updates to reflect changes in Scholar's page rendering,
#       contributed by Amanda Hay at Tufts -- thanks!
#
# 1.3:  Updates to reflect changes in Scholar's page rendering.
#
# 1.2:  Minor tweaks, mostly thanks to helpful feedback from Dan Bolser.
#       Thanks Dan!
#
# 1.1:  Made author field explicit, added --author option.
#
# Don't complain about missing docstrings: pylint: disable-msg=C0111
#
# Copyright 2010--2014 Christian Kreibich. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import optparse
import os
import sys
import re
import pdb

try:
    # Try importing for Python 3
    # pylint: disable-msg=F0401
    # pylint: disable-msg=E0611
    from urllib.request import HTTPCookieProcessor, Request, build_opener
    from urllib.parse import quote, unquote
    from http.cookiejar import MozillaCookieJar
except ImportError:
    # Fallback for Python 2
    from urllib2 import Request, build_opener, HTTPCookieProcessor
    from urllib import quote, unquote
    from cookielib import MozillaCookieJar

# Import BeautifulSoup -- try 4 first, fall back to older
try:
    from bs4 import BeautifulSoup
except ImportError:
    try:
        from BeautifulSoup import BeautifulSoup
    except ImportError:
        print('We need BeautifulSoup, sorry...')
        sys.exit(1)

# Support unicode in both Python 2 and 3. In Python 3, unicode is str.
if sys.version_info[0] == 3:
    unicode = str # pylint: disable-msg=W0622
    encode = lambda s: s # pylint: disable-msg=C0103
else:
    def encode(s):
        if isinstance(s, basestring):
            return s.encode('utf-8') # pylint: disable-msg=C0103
        else:
            return str(s)


class Error(Exception):
    """Base class for any Scholar error."""


class FormatError(Error):
    """A query argument or setting was formatted incorrectly."""


class QueryArgumentError(Error):
    """A query did not have a suitable set of arguments."""


class ScholarConf(object):
    """Helper class for global settings."""

    VERSION = '2.9'
    LOG_LEVEL = 1
    MAX_PAGE_RESULTS = 20 # Current maximum for per-page results
    SCHOLAR_SITE = 'http://scholar.google.com'

    # USER_AGENT = 'Mozilla/5.0 (X11; U; FreeBSD i386; en-US; rv:1.9.2.9) Gecko/20100913 Firefox/3.6.9'
    # Let's update at this point (3/14):
    USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:27.0) Gecko/20100101 Firefox/27.0'

    # If set, we will use this file to read/save cookies to enable
    # cookie use across sessions.
    COOKIE_JAR_FILE = None

class ScholarUtils(object):
    """A wrapper for various utensils that come in handy."""

    LOG_LEVELS = {'error': 1,
                  'warn':  2,
                  'info':  3,
                  'debug': 4}

    @staticmethod
    def ensure_int(arg, msg=None):
        try:
            return int(arg)
        except ValueError:
            raise FormatError(msg)

    @staticmethod
    def log(level, msg):
        if level not in ScholarUtils.LOG_LEVELS.keys():
            return
        if ScholarUtils.LOG_LEVELS[level] > ScholarConf.LOG_LEVEL:
            return
        sys.stderr.write('[%5s]  %s' % (level.upper(), msg + '\n'))
        sys.stderr.flush()


class ScholarArticle(object):
    """
    A class representing articles listed on Google Scholar.  The class
    provides basic dictionary-like behavior.
    """
    def __init__(self):
        # The triplets for each keyword correspond to (1) the actual
        # value, (2) a user-suitable label for the item, and (3) an
        # ordering index:
        self.attrs = {
            'title':         [None, 'Title',          0],
            'url':           [None, 'URL',            1],
            'year':          [None, 'Year',           2],
            'num_citations': [0,    'Citations',      3],
            'num_versions':  [0,    'Versions',       4],
            'cluster_id':    [None, 'Cluster ID',     5],
            'url_pdf':       [None, 'PDF link',       6],
            'url_citations': [None, 'Citations list', 7],
            'url_versions':  [None, 'Versions list',  8],
            'url_citation':  [None, 'Citation link',  9],
            'excerpt':       [None, 'Excerpt',       10],
        }

        # The citation data in one of the standard export formats,
        # e.g. BibTeX.
        self.citation_data = None

    def __getitem__(self, key):
        if key in self.attrs:
            return self.attrs[key][0]
        return None

    def __len__(self):
        return len(self.attrs)

    def __setitem__(self, key, item):
        if key in self.attrs:
            self.attrs[key][0] = item
        else:
            self.attrs[key] = [item, key, len(self.attrs)]

    def __delitem__(self, key):
        if key in self.attrs:
            del self.attrs[key]

    def set_citation_data(self, citation_data):
        self.citation_data = citation_data

    def as_txt(self):
        # Get items sorted in specified order:
        items = sorted(list(self.attrs.values()), key=lambda item: item[2])
        # Find largest label length:
        max_label_len = max([len(str(item[1])) for item in items])
        fmt = '%%%ds %%s' % max_label_len
        res = []
        for item in items:
            if item[0] is not None:
                res.append(fmt % (item[1], item[0]))
        return '\n'.join(res)

    def as_csv(self, header=False, sep='|'):
        # Get keys sorted in specified order:
        keys = [pair[0] for pair in \
                sorted([(key, val[2]) for key, val in list(self.attrs.items())],
                       key=lambda pair: pair[1])]
        res = []
        if header:
            res.append(sep.join(keys))
        res.append(sep.join([unicode(self.attrs[key][0]) for key in keys]))
        return '\n'.join(res)

    def as_citation(self):
        """
        Reports the article in a standard citation format. This works only
        if you have configured the querier to retrieve a particular
        citation export format. (See ScholarSettings.)
        """
        return self.citation_data or ''


class ScholarArticleParser(object):
    """
    ScholarArticleParser can parse HTML document strings obtained from
    Google Scholar. This is a base class; concrete implementations
    adapting to tweaks made by Google over time follow below.
    """
    def __init__(self, site=None):
        self.soup = None
        self.article = None
        self.site = site or ScholarConf.SCHOLAR_SITE
        self.year_re = re.compile(r'\b(?:20|19)\d{2}\b')

    def handle_article(self, art):
        """
        The parser invokes this callback on each article parsed
        successfully.  In this base class, the callback does nothing.
        """

    def handle_num_results(self, num_results):
        """
        The parser invokes this callback if it determines the overall
        number of results, as reported on the parsed results page. The
        base class implementation does nothing.
        """

    def parse(self, html):
        """
        This method initiates parsing of HTML content, cleans resulting
        content as needed, and notifies the parser instance of
        resulting instances via the handle_article callback.
        """
        self.soup = BeautifulSoup(html, "html.parser")

        # This parses any global, non-itemized attributes from the page.
        self._parse_globals()

        # Now parse out listed articles:
        for div in self.soup.findAll(ScholarArticleParser._tag_results_checker):
            self._parse_article(div)
            self._clean_article()
            if self.article['title']:
                self.handle_article(self.article)

    def _clean_article(self):
        """
        This gets invoked after we have parsed an article, to do any
        needed cleanup/polishing before we hand off the resulting
        article.
        """
        if self.article['title']:
            self.article['title'] = self.article['title'].strip()

    def _parse_globals(self):
        tag = self.soup.find(name='div', attrs={'id': 'gs_ab_md'})
        if tag is not None:
            raw_text = tag.findAll(text=True)
            # raw text is a list because the body contains <b> etc
            if raw_text is not None and len(raw_text) > 0:
                try:
                    num_results = raw_text[0].split()[1]
                    # num_results may now contain commas to separate
                    # thousands, strip:
                    num_results = num_results.replace(',', '')
                    num_results = int(num_results)
                    self.handle_num_results(num_results)
                except (IndexError, ValueError):
                    pass

    def _parse_article(self, div):
        self.article = ScholarArticle()

        for tag in div:
            if not hasattr(tag, 'name'):
                continue

            if tag.name == 'div' and self._tag_has_class(tag, 'gs_rt') and \
                    tag.h3 and tag.h3.a:
                self.article['title'] = ''.join(tag.h3.a.findAll(text=True))
                self.article['url'] = self._path2url(tag.h3.a['href'])
                if self.article['url'].endswith('.pdf'):
                    self.article['url_pdf'] = self.article['url']

            if tag.name == 'font':
                for tag2 in tag:
                    if not hasattr(tag2, 'name'):
                        continue
                    if tag2.name == 'span' and \
                       self._tag_has_class(tag2, 'gs_fl'):
                        self._parse_links(tag2)

    def _parse_links(self, span):
        for tag in span:
            if not hasattr(tag, 'name'):
                continue
            if tag.name != 'a' or tag.get('href') is None:
                continue

            if tag.get('href').startswith('/scholar?cites'):
                if hasattr(tag, 'string') and tag.string.startswith('Cited by'):
                    self.article['num_citations'] = \
                        self._as_int(tag.string.split()[-1])

                # Weird Google Scholar behavior here: if the original
                # search query came with a number-of-results limit,
                # then this limit gets propagated to the URLs embedded
                # in the results page as well. Same applies to
                # versions URL in next if-block.
                self.article['url_citations'] = \
                    self._strip_url_arg('num', self._path2url(tag.get('href')))

                # We can also extract the cluster ID from the versions
                # URL. Note that we know that the string contains "?",
                # from the above if-statement.
                args = self.article['url_citations'].split('?', 1)[1]
                for arg in args.split('&'):
                    if arg.startswith('cites='):
                        self.article['cluster_id'] = arg[6:]

            if tag.get('href').startswith('/scholar?cluster'):
                if hasattr(tag, 'string') and tag.string.startswith('All '):
                    self.article['num_versions'] = \
                        self._as_int(tag.string.split()[1])
                self.article['url_versions'] = \
                    self._strip_url_arg('num', self._path2url(tag.get('href')))

            if tag.getText().startswith('Import'):
                self.article['url_citation'] = self._path2url(tag.get('href'))


    @staticmethod
    def _tag_has_class(tag, klass):
        """
        This predicate function checks whether a BeatifulSoup Tag instance
        has a class attribute.
        """
        res = tag.get('class') or []
        if type(res) != list:
            # BeautifulSoup 3 can return e.g. 'gs_md_wp gs_ttss',
            # so split -- conveniently produces a list in any case
            res = res.split()
        return klass in res

    @staticmethod
    def _tag_results_checker(tag):
        return tag.name == 'div' \
            and ScholarArticleParser._tag_has_class(tag, 'gs_r')

    @staticmethod
    def _as_int(obj):
        try:
            return int(obj)
        except ValueError:
            return None

    def _path2url(self, path):
        """Helper, returns full URL in case path isn't one."""
        if path.startswith('http://'):
            return path
        if not path.startswith('/'):
            path = '/' + path
        return self.site + path

    def _strip_url_arg(self, arg, url):
        """Helper, removes a URL-encoded argument, if present."""
        parts = url.split('?', 1)
        if len(parts) != 2:
            return url
        res = []
        for part in parts[1].split('&'):
            if not part.startswith(arg + '='):
                res.append(part)
        return parts[0] + '?' + '&'.join(res)


class ScholarArticleParser120201(ScholarArticleParser):
    """
    This class reflects update to the Scholar results page layout that
    Google recently.
    """
    def _parse_article(self, div):
        self.article = ScholarArticle()

        for tag in div:
            if not hasattr(tag, 'name'):
                continue

            if tag.name == 'h3' and self._tag_has_class(tag, 'gs_rt') and tag.a:
                self.article['title'] = ''.join(tag.a.findAll(text=True))
                self.article['url'] = self._path2url(tag.a['href'])
                if self.article['url'].endswith('.pdf'):
                    self.article['url_pdf'] = self.article['url']

            if tag.name == 'div' and self._tag_has_class(tag, 'gs_a'):
                year = self.year_re.findall(tag.text)
                self.article['year'] = year[0] if len(year) > 0 else None

            if tag.name == 'div' and self._tag_has_class(tag, 'gs_fl'):
                self._parse_links(tag)


class ScholarArticleParser120726(ScholarArticleParser):
    """
    This class reflects update to the Scholar results page layout that
    Google made 07/26/12.
    """
    def _parse_article(self, div):
        self.article = ScholarArticle()

        for tag in div:
            if not hasattr(tag, 'name'):
                continue
            if str(tag).lower().find('.pdf'):
                if tag.find('div', {'class': 'gs_ttss'}):
                    self._parse_links(tag.find('div', {'class': 'gs_ttss'}))

            if tag.name == 'div' and self._tag_has_class(tag, 'gs_ri'):
                # There are (at least) two formats here. In the first
                # one, we have a link, e.g.:
                #
                # <h3 class="gs_rt">
                #   <a href="http://dl.acm.org/citation.cfm?id=972384" class="yC0">
                #     <b>Honeycomb</b>: creating intrusion detection signatures using
                #        honeypots
                #   </a>
                # </h3>
                #
                # In the other, there's no actual link -- it's what
                # Scholar renders as "CITATION" in the HTML:
                #
                # <h3 class="gs_rt">
                #   <span class="gs_ctu">
                #     <span class="gs_ct1">[CITATION]</span>
                #     <span class="gs_ct2">[C]</span>
                #   </span>
                #   <b>Honeycomb</b> automated ids signature creation using honeypots
                # </h3>
                #
                # We now distinguish the two.
                try:
                    atag = tag.h3.a
                    self.article['title'] = ''.join(atag.findAll(text=True))
                    self.article['url'] = self._path2url(atag['href'])
                    if self.article['url'].endswith('.pdf'):
                        self.article['url_pdf'] = self.article['url']
                except:
                    # Remove a few spans that have unneeded content (e.g. [CITATION])
                    for span in tag.h3.findAll(name='span'):
                        span.clear()
                    self.article['title'] = ''.join(tag.h3.findAll(text=True))

                if tag.find('div', {'class': 'gs_a'}):
                    year = self.year_re.findall(tag.find('div', {'class': 'gs_a'}).text)
                    self.article['year'] = year[0] if len(year) > 0 else None

                if tag.find('div', {'class': 'gs_fl'}):
                    self._parse_links(tag.find('div', {'class': 'gs_fl'}))

                if tag.find('div', {'class': 'gs_rs'}):
                    # These are the content excerpts rendered into the results.
                    raw_text = tag.find('div', {'class': 'gs_rs'}).findAll(text=True)
                    if len(raw_text) > 0:
                        raw_text = ''.join(raw_text)
                        raw_text = raw_text.replace('\n', '')
                        self.article['excerpt'] = raw_text


class ScholarQuery(object):
    """
    The base class for any kind of results query we send to Scholar.
    """
    def __init__(self):
        self.url = None

        # The number of results requested from Scholar -- not the
        # total number of results it reports (the latter gets stored
        # in attrs, see below).
        self.num_results = ScholarConf.MAX_PAGE_RESULTS

        # Queries may have global result attributes, similar to
        # per-article attributes in ScholarArticle. The exact set of
        # attributes may differ by query type, but they all share the
        # basic data structure:
        self.attrs = {}

    def set_num_page_results(self, num_page_results):
        msg = 'maximum number of results on page must be numeric'
        self.num_results = ScholarUtils.ensure_int(num_page_results, msg)

    def get_url(self):
        """
        Returns a complete, submittable URL string for this particular
        query instance. The URL and its arguments will vary depending
        on the query.
        """
        return None

    def _add_attribute_type(self, key, label, default_value=None):
        """
        Adds a new type of attribute to the list of attributes
        understood by this query. Meant to be used by the constructors
        in derived classes.
        """
        if len(self.attrs) == 0:
            self.attrs[key] = [default_value, label, 0]
            return
        idx = max([item[2] for item in self.attrs.values()]) + 1
        self.attrs[key] = [default_value, label, idx]

    def __getitem__(self, key):
        """Getter for attribute value. Returns None if no such key."""
        if key in self.attrs:
            return self.attrs[key][0]
        return None

    def __setitem__(self, key, item):
        """Setter for attribute value. Does nothing if no such key."""
        if key in self.attrs:
            self.attrs[key][0] = item

    def _parenthesize_phrases(self, query):
        """
        Turns a query string containing comma-separated phrases into a
        space-separated list of tokens, quoted if containing
        whitespace. For example, input
          'some words, foo, bar'
        becomes
          '"some words" foo bar'
        This comes in handy during the composition of certain queries.
        """
        if query.find(',') < 0:
            return query
        phrases = []
        for phrase in query.split(','):
            phrase = phrase.strip()
            if phrase.find(' ') > 0:
                phrase = '"' + phrase + '"'
            phrases.append(phrase)
        return ' '.join(phrases)


class ClusterScholarQuery(ScholarQuery):
    """
    This version just pulls up an article cluster whose ID we already
    know about.
    """
    SCHOLAR_CLUSTER_URL = ScholarConf.SCHOLAR_SITE + '/scholar?' \
        + 'cluster=%(cluster)s' \
        + '&num=%(num)s'

    def __init__(self, cluster=None):
        ScholarQuery.__init__(self)
        self._add_attribute_type('num_results', 'Results', 0)
        self.cluster = None
        self.set_cluster(cluster)

    def set_cluster(self, cluster):
        """
        Sets search to a Google Scholar results cluster ID.
        """
        msg = 'cluster ID must be numeric'
        self.cluster = ScholarUtils.ensure_int(cluster, msg)

    def get_url(self):
        if self.cluster is None:
            raise QueryArgumentError('cluster query needs cluster ID')

        urlargs = {'cluster': self.cluster,
                   'num': self.num_results or ScholarConf.MAX_PAGE_RESULTS}

        for key, val in urlargs.items():
            urlargs[key] = quote(encode(val))

        return self.SCHOLAR_CLUSTER_URL % urlargs


class SearchScholarQuery(ScholarQuery):
    """
    This version represents the search query parameters the user can
    configure on the Scholar website, in the advanced search options.
    """
    SCHOLAR_QUERY_URL = ScholarConf.SCHOLAR_SITE + '/scholar?' \
        + 'as_q=%(words)s' \
        + '&as_epq=%(phrase)s' \
        + '&as_oq=%(words_some)s' \
        + '&as_eq=%(words_none)s' \
        + '&as_occt=%(scope)s' \
        + '&as_sauthors=%(authors)s' \
        + '&as_publication=%(pub)s' \
        + '&as_ylo=%(ylo)s' \
        + '&as_yhi=%(yhi)s' \
        + '&as_sdt=%(patents)s%%2C5' \
        + '&as_vis=%(citations)s' \
        + '&btnG=&hl=en' \
        + '&num=%(num)s'

    def __init__(self):
        ScholarQuery.__init__(self)
        self._add_attribute_type('num_results', 'Results', 0)
        self.words = None # The default search behavior
        self.words_some = None # At least one of those words
        self.words_none = None # None of these words
        self.phrase = None
        self.scope_title = False # If True, search in title only
        self.author = None
        self.pub = None
        self.timeframe = [None, None]
        self.include_patents = True
        self.include_citations = True

    def set_words(self, words):
        """Sets words that *all* must be found in the result."""
        self.words = words

    def set_words_some(self, words):
        """Sets words of which *at least one* must be found in result."""
        self.words_some = words

    def set_words_none(self, words):
        """Sets words of which *none* must be found in the result."""
        self.words_none = words

    def set_phrase(self, phrase):
        """Sets phrase that must be found in the result exactly."""
        self.phrase = phrase

    def set_scope(self, title_only):
        """
        Sets Boolean indicating whether to search entire article or title
        only.
        """
        self.scope_title = title_only

    def set_author(self, author):
        """Sets names that must be on the result's author list."""
        self.author = author

    def set_pub(self, pub):
        """Sets the publication in which the result must be found."""
        self.pub = pub

    def set_timeframe(self, start=None, end=None):
        """
        Sets timeframe (in years as integer) in which result must have
        appeared. It's fine to specify just start or end, or both.
        """
        if start:
            start = ScholarUtils.ensure_int(start)
        if end:
            end = ScholarUtils.ensure_int(end)
        self.timeframe = [start, end]

    def set_include_citations(self, yesorno):
        self.include_citations = yesorno

    def set_include_patents(self, yesorno):
        self.include_patents = yesorno

    def get_url(self):
        if self.words is None and self.words_some is None \
           and self.words_none is None and self.phrase is None \
           and self.author is None and self.pub is None \
           and self.timeframe[0] is None and self.timeframe[1] is None:
            raise QueryArgumentError('search query needs more parameters')

        # If we have some-words or none-words lists, we need to
        # process them so GS understands them. For simple
        # space-separeted word lists, there's nothing to do. For lists
        # of phrases we have to ensure quotations around the phrases,
        # separating them by whitespace.
        words_some = None
        words_none = None

        if self.words_some:
            words_some = self._parenthesize_phrases(self.words_some)
        if self.words_none:
            words_none = self._parenthesize_phrases(self.words_none)

        urlargs = {'words': self.words or '',
                   'words_some': words_some or '',
                   'words_none': words_none or '',
                   'phrase': self.phrase or '',
                   'scope': 'title' if self.scope_title else 'any',
                   'authors': self.author or '',
                   'pub': self.pub or '',
                   'ylo': self.timeframe[0] or '',
                   'yhi': self.timeframe[1] or '',
                   'patents': '0' if self.include_patents else '1',
                   'citations': '0' if self.include_citations else '1',
                   'num': self.num_results or ScholarConf.MAX_PAGE_RESULTS}

        for key, val in urlargs.items():
            urlargs[key] = quote(encode(str(val)))

        return self.SCHOLAR_QUERY_URL % urlargs


class ScholarSettings(object):

    """
    This class lets you adjust the Scholar settings for your
    session. It's intended to mirror the features tunable in the
    Scholar Settings pane, but right now it's a bit basic.
    """
    CITFORM_NONE = 0
    CITFORM_REFWORKS = 1
    CITFORM_REFMAN = 2
    CITFORM_ENDNOTE = 3
    CITFORM_BIBTEX = 4

    def __init__(self):
        self.citform = 0 # Citation format, default none
        self.per_page_results = ScholarConf.MAX_PAGE_RESULTS
        self._is_configured = False

    def set_citation_format(self, citform):
        citform = ScholarUtils.ensure_int(citform)
        if citform < 0 or citform > self.CITFORM_BIBTEX:
            raise FormatError('citation format invalid, is "%s"' \
                              % citform)
        self.citform = citform
        self._is_configured = True

    def set_per_page_results(self, per_page_results):
        msg = 'page results must be integer'
        self.per_page_results = ScholarUtils.ensure_int(per_page_results, msg)
        self.per_page_results = min(self.per_page_results,
                                    ScholarConf.MAX_PAGE_RESULTS)
        self._is_configured = True

    def is_configured(self):
        return self._is_configured


class ScholarQuerier(object):

    """
    ScholarQuerier instances can conduct a search on Google Scholar
    with subsequent parsing of the resulting HTML content.  The
    articles found are collected in the articles member, a list of
    ScholarArticle instances.
    """

    # Default URLs for visiting and submitting Settings pane, as of 3/14
    GET_SETTINGS_URL = ScholarConf.SCHOLAR_SITE + '/scholar_settings?' \
        + 'sciifh=1&hl=en&as_sdt=0,5'

    SET_SETTINGS_URL = ScholarConf.SCHOLAR_SITE + '/scholar_setprefs?' \
        + 'q=' \
        + '&scisig=%(scisig)s' \
        + '&inststart=0' \
        + '&as_sdt=1,5' \
        + '&as_sdtp=' \
        + '&num=%(num)s' \
        + '&scis=%(scis)s' \
        + '%(scisf)s' \
        + '&hl=en&lang=all&instq=&inst=569367360547434339&save='

    # Older URLs:
    # ScholarConf.SCHOLAR_SITE + '/scholar?q=%s&hl=en&btnG=Search&as_sdt=2001&as_sdtp=on

    class Parser(ScholarArticleParser120726):
        def __init__(self, querier):
            ScholarArticleParser120726.__init__(self)
            self.querier = querier

        def handle_num_results(self, num_results):
            if self.querier is not None and self.querier.query is not None:
                self.querier.query['num_results'] = num_results

        def handle_article(self, art):
            self.querier.add_article(art)

    def __init__(self):
        self.articles = []
        self.query = None
        self.cjar = MozillaCookieJar()

        # If we have a cookie file, load it:
        if ScholarConf.COOKIE_JAR_FILE and \
           os.path.exists(ScholarConf.COOKIE_JAR_FILE):
            try:
                self.cjar.load(ScholarConf.COOKIE_JAR_FILE,
                               ignore_discard=True)
                ScholarUtils.log('info', 'loaded cookies file')
            except Exception as msg:
                ScholarUtils.log('warn', 'could not load cookies file: %s' % msg)
                self.cjar = MozillaCookieJar() # Just to be safe

        self.opener = build_opener(HTTPCookieProcessor(self.cjar))
        self.settings = None # Last settings object, if any

    def apply_settings(self, settings):
        """
        Applies settings as provided by a ScholarSettings instance.
        """
        if settings is None or not settings.is_configured():
            return True

        self.settings = settings

        # This is a bit of work. We need to actually retrieve the
        # contents of the Settings pane HTML in order to extract
        # hidden fields before we can compose the query for updating
        # the settings.
        #html = self._get_http_response(url=self.GET_SETTINGS_URL,
        #                               log_msg='dump of settings form HTML',
        #                               err_msg='requesting settings failed')
        html = '<!doctype html><html><head><title>Google Scholar Settings</title><meta http-equiv="Content-Type" content="text/html;charset=UTF-8"><meta http-equiv="X-UA-Compatible" content="IE=Edge"><meta name="referrer" content="origin-when-crossorigin"><meta name="viewport" content="width=device-width,initial-scale=1,minimum-scale=1,maximum-scale=2"><style>@viewport{width:device-width;min-zoom:1;max-zoom:2;}</style><meta name="format-detection" content="telephone=no"><link rel="shortcut icon" href="/favicon-png.ico"><style>html,body,form,table,div,h1,h2,h3,h4,h5,h6,img,ol,ul,li,button{margin:0;padding:0;border:0;}table{border-collapse:collapse;border-width:0;empty-cells:show;}#gs_top{position:relative;min-width:964px;-webkit-tap-highlight-color:rgba(0,0,0,0);}#gs_top>*:not(#x){-webkit-tap-highlight-color:rgba(204,204,204,.5);}.gs_el_ph #gs_top,.gs_el_ta #gs_top{min-width:300px;}body,td,input{font-size:13px;font-family:Arial,sans-serif;line-height:1.24}body{background:#fff;color:#222;-webkit-text-size-adjust:100%;-moz-text-size-adjust:none;}.gs_gray{color:#777777}.gs_red{color:#dd4b39}.gs_grn{color:#006621}.gs_lil{font-size:11px}.gs_med{font-size:16px}.gs_hlt{font-weight:bold;}a:link{color:#1a0dab;text-decoration:none}a:visited{color:#660099;text-decoration:none}a:hover,a:active,a:hover .gs_lbl,a:active .gs_lbl,a .gs_lbl:active{text-decoration:underline;outline:none;}a:active,a:active .gs_lbl,a .gs_lbl:active{color:#d14836}.gs_a,.gs_a a:link,.gs_a a:visited{color:#006621}.gs_a a:active{color:#d14836}a.gs_fl:link,.gs_fl a:link{color:#1a0dab}a.gs_fl:visited,.gs_fl a:visited{color:#660099}a.gs_fl:active,.gs_fl a:active{color:#d14836}.gs_fl{color:#777777}.gs_ctc,.gs_ctu{vertical-align:middle;font-size:11px;font-weight:bold}.gs_ctc{color:#1a0dab}.gs_ctg,.gs_ctg2{font-size:13px;font-weight:bold}.gs_ctg{color:#1a0dab}a.gs_pda,.gs_pda a{padding:7px 0 5px 0}.gs_alrt{background:#f9edbe;border:1px solid #f0c36d;padding:0 16px;text-align:center;-webkit-box-shadow:0 2px 4px rgba(0,0,0,.2);-moz-box-shadow:0 2px 4px rgba(0,0,0,.2);box-shadow:0 2px 4px rgba(0,0,0,.2);-webkit-border-radius:2px;-moz-border-radius:2px;border-radius:2px;}.gs_spc{display:inline-block;width:12px}.gs_br{width:0;font-size:0}.gs_ibl{display:inline-block;}.gs_scl:after{content:"";display:table;clear:both;}.gs_ind{padding-left:8px;text-indent:-8px}.gs_ico,.gs_icm{display:inline-block;background:no-repeat url(/intl/en/scholar/images/sprite.png);width:21px;height:21px;font-size:0;}.gs_el_ta .gs_nta,.gs_ota,.gs_el_ph .gs_nph,.gs_oph{display:none}.gs_el_ta .gs_ota,.gs_el_ph .gs_oph{display:inline}.gs_el_ta div.gs_ota,.gs_el_ph div.gs_oph{display:block}#gs_ftr{margin:32px 0 0 0;text-align:center;clear:both;}#gs_ftr a{display:inline-block;margin:0 12px;padding:7px 0 8px 0;}#gs_ftr a:link,#gs_ftr a:visited{color:#1a0dab}#gs_ftr a:active{color:#d14836}.gs_in_txt{color:black;background:#fff;font-size:16px;height:23px;line-height:23px;border:1px solid #d9d9d9;border-top:1px solid #c0c0c0;padding:3px 6px 1px 8px;-webkit-border-radius:1px;-moz-border-radius:1px;border-radius:1px;outline:none;vertical-align:middle;-webkit-appearance:none;-moz-appearance:none;}.gs_el_tc .gs_in_txt{font-size:18px;}.gs_in_txt:hover{border:1px solid #b9b9b9;border-top:1px solid #a0a0a0;-webkit-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.1);-moz-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.1);box-shadow:inset 0px 1px 2px rgba(0,0,0,0.1);}.gs_in_txte,.gs_in_txte:hover{border:1px solid #DD4B39;}.gs_in_txt:focus{border:1px solid #4d90fe;-webkit-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.3);-moz-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.3);box-shadow:inset 0px 1px 2px rgba(0,0,0,0.3);}input.gs_mini{font-size:13px;height:16px;line-height:16px;padding:3px 6px;}.gs_el_tc input.gs_mini{font-size:13px;height:21px;line-height:21px;}.gs_in_txtf{margin-right:16px}.gs_in_txtm{margin-right:14px}.gs_in_txtf .gs_in_txt,.gs_in_txtm .gs_in_txt{width:100%;}.gs_in_txts{font-size:13px;line-height:18px;}button{position:relative; z-index:1; -moz-box-sizing:border-box;-webkit-box-sizing:border-box;box-sizing:border-box;font-size:11px;font-weight:bold;cursor:default;height:29px;min-width:72px;overflow:visible;color:#444;border:1px solid #dcdcdc;border:1px solid rgba(0,0,0,.1);-webkit-border-radius:2px;-moz-border-radius:2px;border-radius:2px;text-align:center;background-color:#f5f5f5;background-image:-webkit-gradient(linear,left top,left bottom,from(#f5f5f5),to(#f1f1f1));background-image:-webkit-linear-gradient(top,#f5f5f5,#f1f1f1);background-image:-moz-linear-gradient(top,#f5f5f5,#f1f1f1);background-image:-o-linear-gradient(top,#f5f5f5,#f1f1f1);background-image:linear-gradient(to bottom,#f5f5f5,#f1f1f1);-webkit-transition:all .218s;-moz-transition:all .218s;-o-transition:all .218s;transition:all .218s;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;}button .gs_wr{line-height:27px;}button.gs_btn_mini{min-width:26px;height:26px;}.gs_btn_mini .gs_wr{line-height:24px;}.gs_btn_half,.gs_el_ph .gs_btn_hph{min-width:36px;}>. }}.gs_btn_slt{-webkit-border-radius:2px 0 0 2px;-moz-border-radius:2px 0 0 2px;border-radius:2px 0 0 2px;}.gs_btn_srt{margin-left:-1px;-webkit-border-radius:0 2px 2px 0;-moz-border-radius:0 2px 2px 0;border-radius:0 2px 2px 0;}.gs_btn_smd{margin-left:-1px;-webkit-border-radius:0;-moz-border-radius:0;border-radius:0;}button:hover{z-index:2;color:#222;border:1px solid #c6c6c6;-webkit-box-shadow:0px 1px 1px rgba(0,0,0,.1);-moz-box-shadow:0px 1px 1px rgba(0,0,0,.1);box-shadow:0px 1px 1px rgba(0,0,0,.1);background-color:#f8f8f8;background-image:-webkit-gradient(linear,left top,left bottom,from(#f8f8f8),to(#f1f1f1));background-image:-webkit-linear-gradient(top,#f8f8f8,#f1f1f1);background-image:-moz-linear-gradient(top,#f8f8f8,#f1f1f1);background-image:-o-linear-gradient(top,#f8f8f8,#f1f1f1);background-image:linear-gradient(to bottom,#f8f8f8,#f1f1f1);-webkit-transition:all 0s;-moz-transition:all 0s;-o-transition:all 0s;transition:all 0s;}button.gs_sel{color:#333;border:1px solid #ccc;-webkit-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);-moz-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);box-shadow:inset 0 1px 2px rgba(0,0,0,.1);background-color:#e8e8e8;background-image:-webkit-gradient(linear,left top,left bottom,from(#eee),to(#e0e0e0));background-image:-webkit-linear-gradient(top,#eee,#e0e0e0);background-image:-moz-linear-gradient(top,#eee,#e0e0e0);background-image:-o-linear-gradient(top,#eee,#e0e0e0);background-image:linear-gradient(to bottom,#eee,#e0e0e0);}button:active{z-index:2;color:#333;background-color:#f6f6f6;background-image:-webkit-gradient(linear,left top,left bottom,from(#f6f6f6),to(#f1f1f1));background-image:-webkit-linear-gradient(top,#f6f6f6,#f1f1f1);background-image:-moz-linear-gradient(top,#f6f6f6,#f1f1f1);background-image:-o-linear-gradient(top,#f6f6f6,#f1f1f1);background-image:linear-gradient(to bottom,#f6f6f6,#f1f1f1);-webkit-box-shadow:inset 0px 1px 2px rgba(0,0,0,.1);-moz-box-shadow:inset 0px 1px 2px rgba(0,0,0,.1);box-shadow:inset 0px 1px 2px rgba(0,0,0,.1);}button:focus{z-index:2;outline:none;border:1px solid #4d90fe;}button::-moz-focus-inner{padding:0;border:0}button .gs_lbl{padding:0px 8px;}a.gs_in_ib{position:relative;display:inline-block;line-height:16px;padding:5px 0 6px 0;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;}a.gs_btn_mini{height:24px;line-height:24px;padding:0;}a .gs_lbl,button .gs_lbl{vertical-align:baseline;}a.gs_in_ib .gs_lbl{display:inline-block;padding-left:21px}button.gs_in_ib .gs_lbl{padding-left:29px;}button.gs_btn_mini .gs_lbl,button.gs_btn_half .gs_lbl,button.gs_btn_eml .gs_lbl{padding:11px;}.gs_el_ph .gs_btn_hph .gs_lbl,.gs_el_ph .gs_btn_cph .gs_lbl{padding:11px;font-size:0;visibility:hidden;}.gs_in_ib .gs_ico{position:absolute;top:2px;left:8px;}.gs_btn_mini .gs_ico{top:1px;left:2px;}.gs_btn_half .gs_ico,.gs_el_ph .gs_btn_hph .gs_ico{left:7px}.gs_btn_eml .gs_ico,.gs_el_ph .gs_btn_cph .gs_ico{left:25px}a.gs_in_ib .gs_ico{top:3px;left:0}a.gs_in_ib.gs_md_li .gs_ico{left:14px}.gs_el_tc a.gs_in_ib.gs_md_li .gs_ico{top:11px}a.gs_btn_mini .gs_ico{top:1px;left:0}button.gs_btn_act{color:#fff;-webkit-font-smoothing:antialiased;border:1px solid #3079ed;background-color:#4d90fe;background-image:-webkit-gradient(linear,left top,left bottom,from(#4d90fe),to(#4787ed));background-image:-webkit-linear-gradient(top,#4d90fe,#4787ed);background-image:-moz-linear-gradient(top,#4d90fe,#4787ed);background-image:-o-linear-gradient(top,#4d90fe,#4787ed);background-image:linear-gradient(to bottom,#4d90fe,#4787ed);}button.gs_btn_act:hover{color:#fff;border:1px solid #2f5bb7;background-color:#357ae8;background-image:-webkit-gradient(linear,left top,left bottom,from(#4d90fe),to(#357ae8));background-image:-webkit-linear-gradient(top,#4d90fe,#357ae8);background-image:-moz-linear-gradient(top,#4d90fe,#357ae8);background-image:-o-linear-gradient(top,#4d90fe,#357ae8);background-image:linear-gradient(to bottom,#4d90fe,#357ae8);-webkit-box-shadow:inset 0px 1px 1px rgba(0,0,0,.1);-moz-box-shadow:inset 0px 1px 1px rgba(0,0,0,.1);box-shadow:inset 0px 1px 1px rgba(0,0,0,.1);}button.gs_btnG{width:70px;min-width:0;}button.gs_btn_act:focus{-webkit-box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);-moz-box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);}button.gs_btn_act:focus{border-color:#404040;}button.gs_btn_act:active{border:1px solid #315da3;background-color:#2f6de1;background-image:-webkit-gradient(linear,left top,left bottom,from(#4d90fe),to(#2f6de1));background-image:-webkit-linear-gradient(top,#4d90fe,#2f6de1);background-image:-moz-linear-gradient(top,#4d90fe,#2f6de1);background-image:-o-linear-gradient(top,#4d90fe,#2f6de1);background-image:linear-gradient(to bottom,#4d90fe,#2f6de1);}button.gs_btn_act:active{-webkit-box-shadow:inset 0 1px 2px rgba(0,0,0,.3);-moz-box-shadow:inset 0 1px 2px rgba(0,0,0,.3);box-shadow:inset 0 1px 2px rgba(0,0,0,.3);}button.gs_dis,button.gs_dis:hover,button.gs_dis:active{color:#b8b8b8;border:1px solid #f3f3f3;border:1px solid rgba(0,0,0,.05);background:none;-webkit-box-shadow:none;-moz-box-shadow:none;box-shadow:none;z-index:0;}button.gs_btn_act.gs_dis{color:white;border-color:#98bcf6;background:#a6c8ff;}button.gs_dis:active:not(#x){-webkit-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);-moz-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);box-shadow:inset 0 1px 2px rgba(0,0,0,.1);z-index:2;}a.gs_dis{cursor:default}.gs_ttp{position:absolute;top:100%;right:50%;z-index:10;pointer-events:none;visibility:hidden;opacity:0;-webkit-transition:visibility 0s .13s,opacity .13s ease-out;-moz-transition:visibility 0s .13s,opacity .13s ease-out;-o-transition:visibility 0s .13s,opacity .13s ease-out;transition:visibility 0s .13s,opacity .13s ease-out;}button:hover .gs_ttp,button:focus .gs_ttp,a:hover .gs_ttp,a:focus .gs_ttp{-webkit-transition:visibility 0s .3s,opacity .13s ease-in .3s;-moz-transition:visibility 0s .3s,opacity .13s ease-in .3s;-o-transition:visibility 0s .3s,opacity .13s ease-in .3s;transition:visibility 0s .3s,opacity .13s ease-in .3s;visibility:visible;opacity:1;}.gs_ttp .gs_aro,.gs_ttp .gs_aru{position:absolute;top:-2px;right:-5px;width:0;height:0;line-height:0;font-size:0;border:5px solid transparent;border-top:none;border-bottom-color:#2a2a2a;z-index:1;}.gs_ttp .gs_aro{top:-3px;right:-6px;border-width:6px;border-top:none;border-bottom-color:white;}.gs_ttp .gs_txt{display:block;position:relative;top:2px;right:-50%;padding:7px 9px;background:#2a2a2a;color:white;font-size:11px;font-weight:bold;line-height:normal;white-space:nowrap;border:1px solid white;-webkit-box-shadow:inset 0 1px 4px rgba(0,0,0,.2);-moz-box-shadow:inset 0 1px 4px rgba(0,0,0,.2);box-shadow:inset 0 1px 4px rgba(0,0,0,.2);}.gs_in_se,.gs_tan{-ms-touch-action:none;touch-action:none;}.gs_in_se .gs_lbl{padding-left:8px;padding-right:22px;}.gs_in_se .gs_icm{position:absolute;top:8px;right:8px;width:7px;height:11px;margin:0;background-position:-63px -115px;}a.gs_in_se .gs_icm{background-position:-100px -26px;}.gs_in_se:hover .gs_icm{background-position:-166px -110px;}.gs_in_se:active .gs_icm,.gs_in_se .gs_icm:active{background-position:-89px -26px;}.gs_in_se :active~.gs_icm{background-position:-89px -26px;}.gs_el_ph .gs_btn_hph .gs_icm,.gs_el_ph .gs_btn_cph .gs_icm{display:none}.gs_btn_mnu .gs_icm{height:7px;background-position:-63px -119px;}.gs_btn_mnu:hover .gs_icm{background-position:-166px -114px;}.gs_btn_mnu:active .gs_icm,.gs_btn_mnu .gs_icm:active{background-position:-89px -30px;}.gs_btn_mnu :active~.gs_icm{background-position:-89px -30px;}.gs_md_se,.gs_md_wn,.gs_el_ph .gs_md_wp{position:absolute;top:0;left:0;border:1px solid #ccc;border-color:rgba(0,0,0,.2);background:white;-webkit-box-shadow:0px 2px 4px rgba(0,0,0,.2);-moz-box-shadow:0px 2px 4px rgba(0,0,0,.2);box-shadow:0px 2px 4px rgba(0,0,0,.2);z-index:1100; display:none;opacity:0;-webkit-transition:opacity .13s;-moz-transition:opacity .13s;-o-transition:opacity .13s;transition:opacity .13s;}.gs_md_se.gs_vis,.gs_md_wn.gs_vis,.gs_el_ph .gs_md_wp.gs_vis{opacity:1;-webkit-transition:all 0s;-moz-transition:all 0s;-o-transition:all 0s;transition:all 0s;}.gs_el_tc .gs_md_se,.gs_el_tc .gs_md_wn,.gs_el_ph.gs_el_tc .gs_md_wp{-webkit-transform-origin:100% 0;-moz-transform-origin:100% 0;-o-transform-origin:100% 0;transform-origin:100% 0;-webkit-transform:scale(1,0);-moz-transform:scale(1,0);-o-transform:scale(1,0);transform:scale(1,0);-webkit-transition:opacity .218s ease-out,-webkit-transform 0s .218s;-moz-transition:opacity .218s ease-out,-moz-transform: 0s .218s;-o-transition:opacity .218s ease-out,-o-transform: 0s .218s;transition:opacity .218s ease-out,transform 0s .218s;}.gs_el_ios .gs_md_se,.gs_el_ios .gs_md_wn,.gs_el_ph.gs_el_ios .gs_md_wp{-webkit-backface-visibility:hidden;}.gs_el_tc .gs_md_wn.gs_ttss,.gs_el_ph.gs_el_tc .gs_md_wp.gs_ttss{-webkit-transform:scale(0,1);-moz-transform:scale(0,1);-o-transform:scale(0,1);transform:scale(0,1);}.gs_el_tc .gs_md_wn.gs_ttzi,.gs_el_ph.gs_el_tc .gs_md_wp.gs_ttzi{-webkit-transform-origin:50% 50%;-moz-transform-origin:50% 50%;-o-transform-origin:50% 50%;transform-origin:50% 50%;-webkit-transform:scale(0,0);-moz-transform:scale(0,0);-o-transform:scale(0,0);transform:scale(0,0);}.gs_el_tc .gs_md_se.gs_vis,.gs_el_tc .gs_md_wn.gs_vis,.gs_el_ph.gs_el_tc .gs_md_wp.gs_vis{-webkit-transform:scale(1,1);-moz-transform:scale(1,1);-o-transform:scale(1,1);transform:scale(1,1);-webkit-transition:-webkit-transform .218s ease-out;-moz-transition:-moz-transform .218s ease-out;-o-transition:-o-transform .218s ease-out;transition:transform .218s ease-out;}.gs_md_se{white-space:nowrap}.gs_md_se ul{list-style-type:none;word-wrap:break-word;display:inline-block;vertical-align:top;}.gs_md_se li,.gs_md_li,.gs_md_li:link,.gs_md_li:visited{display:block;padding:6px 44px 6px 16px;font-size:13px;line-height:16px;color:#222;cursor:default;text-decoration:none;background:white;-moz-transition:background .13s;-o-transition:background .13s;-webkit-transition:background .13s;transition:background .13s;}a.gs_md_li:hover .gs_lbl,a.gs_md_li:active .gs_lbl{text-decoration:none}.gs_el_tc .gs_md_se li,.gs_el_tc .gs_md_li{padding-top:14px;padding-bottom:10px;}.gs_md_se li:hover,.gs_md_li:hover,.gs_md_li:focus{background:#f1f1f1;-moz-transition:background 0s;-o-transition:background 0s;-webkit-transition:background 0s;transition:background 0s;}.gs_md_se li.gs_sel{color:#dd4b39}.gs_md_wn:focus,.gs_md_se li:focus,.gs_md_li:focus{outline:none}button.gs_btnG .gs_ico{width:14px;height:13px;top:7px;left:27px;background-position:-152px -68px;}a.gs_in_cb:link,a.gs_in_cb:visited,a.gs_in_cb:active,a.gs_in_cb:hover,a.gs_in_cb.gs_dis:active .gs_lbl{cursor:default;color:#222;text-decoration:none;}.gs_in_cb,.gs_in_ra{position:relative;line-height:16px;display:inline-block;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;-webkit-touch-callout:none;}.gs_in_cb.gs_md_li{padding:6px 44px 6px 16px;}.gs_in_cb input,.gs_in_ra input{position:absolute;top:1px;left:1px;width:15px;height:15px;margin:0;padding:0;-moz-opacity:0;opacity:0;filter:alpha(opacity=0);-ms-filter:"alpha(opacity=0)";z-index:2;}.gs_in_ra input{top:0;left:0}.gs_el_tc .gs_in_cb input{top:9px}.gs_el_tc .gs_in_ra input{top:8px}.gs_in_cb.gs_in_cbj input{top:15px;left:15px}.gs_in_cb label,.gs_in_cb .gs_lbl,.gs_in_ra label{display:inline-block;padding-left:21px;min-height:16px;}.gs_el_tc .gs_in_cb label,.gs_el_tc .gs_in_cb .gs_lbl,.gs_el_tc .gs_in_ra label{padding-top:8px;padding-bottom:5px;}.gs_in_cb.gs_in_cbj label,.gs_in_cb.gs_in_cbj .gs_lbl{padding:13px 0 12px 41px;}.gs_in_cb .gs_cbx,.gs_in_ra .gs_cbx{position:absolute}.gs_in_cb .gs_cbx{top:2px;left:2px;width:11px;height:11px;border:1px solid #c6c6c6;-webkit-border-radius:1px;-moz-border-radius:1px;border-radius:1px;}.gs_md_li .gs_cbx{top:8px;left:18px}.gs_el_tc .gs_in_cb .gs_cbx{top:10px}.gs_el_tc .gs_md_li .gs_cbx{top:16px}.gs_in_cb.gs_in_cbj .gs_cbx{top:15px;left:15px}.gs_in_ra .gs_cbx{top:0;left:0;width:15px;height:15px;background:no-repeat url(/intl/en/scholar/images/sprite.png) -42px -110px;}.gs_el_tc .gs_in_ra .gs_cbx{top:8px}.gs_in_ra .gs_cbx:not(#x){background:transparent;border:1px solid #c6c6c6;width:13px;height:13px;-webkit-border-radius:7px;-moz-border-radius:7px;border-radius:7px;}.gs_in_cb:hover .gs_cbx{border-color:#666;-webkit-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);-moz-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);}.gs_in_ra:hover .gs_cbx{background-position:-187px -89px;}.gs_in_ra:hover .gs_cbx:not(#x){border-color:#666;background:transparent;-webkit-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);-moz-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);}.gs_in_cb:focus .gs_cbx,.gs_in_cb :focus~.gs_cbx,.gs_in_ra :focus~.gs_cbx:not(#x){border-color:#4d90fe;}.gs_in_cb :active~.gs_cbx{border-color:#666;background:#ebebeb;}.gs_in_cb:active .gs_cbx{border-color:#666;background:#ebebeb;}.gs_in_ra:active .gs_cbx:not(#x),.gs_in_ra :active~.gs_cbx:not(#x){border-color:#666;background:#ebebeb;}.gs_in_ra :active~.gs_cbx,.gs_in_ra:active .gs_cbx{background-position:-21px -66px;}.gs_in_cb :disabled~.gs_cbx,.gs_in_ra :disabled~.gs_cbx{border-color:#f1f1f1;background:transparent;-webkit-box-shadow:none;-moz-box-shadow:none;box-shadow:none;}.gs_in_cb.gs_dis .gs_cbx,.gs_in_ra.gs_dis .gs_cbx{border-color:#f1f1f1;background:transparent;}.gs_in_ra.gs_dis .gs_cbx{background-position:-130px -89px;}.gs_in_cb :disabled~label,.gs_in_ra :disabled~label{color:#b8b8b8;}.gs_in_cb.gs_dis label,.gs_in_ra.gs_dis label{color:#b8b8b8;}.gs_in_cb.gs_err .gs_cbx{border-color:#eda29b;}.gs_in_cb .gs_chk,.gs_in_ra .gs_chk{position:absolute;z-index:1; top:-3px;left:-2px;width:21px;height:21px;}.gs_md_li .gs_chk{top:3px;left:14px}.gs_el_tc .gs_in_cb .gs_chk{top:5px}.gs_el_tc .gs_md_li .gs_chk{top:11px}.gs_in_cb.gs_in_cbj .gs_chk{top:10px;left:10px}.gs_in_ra .gs_chk{top:4px;left:4px;width:7px;height:7px;}.gs_el_tc .gs_in_ra .gs_chk{top:12px}.gs_in_cb input:checked~.gs_chk{ background:no-repeat url(/intl/en/scholar/images/sprite.png) -166px -89px;}.gs_in_ra input:checked~.gs_chk{-webkit-border-radius:4px;-moz-border-radius:4px;border-radius:4px;background:#666;}.gs_in_cb.gs_sel .gs_chk{background:no-repeat url(/intl/en/scholar/images/sprite.png) -166px -89px;}.gs_in_ra.gs_sel .gs_chk{background:no-repeat url(/intl/en/scholar/images/sprite.png) -166px -131px;}.gs_in_cb.gs_par .gs_chk{background:no-repeat url(/intl/en/scholar/images/sprite.png) -188px -265px;}.gs_in_cb input:checked:disabled~.gs_chk{background-position:-209px -67px;}.gs_in_cb.gs_dis.gs_sel .gs_chk{background-position:-209px -67px;}.gs_btnPL .gs_ico{background-position:-68px -47px;}.gs_btnPL:hover .gs_ico{background-position:0 0;}.gs_btnPL:active .gs_ico,.gs_btnPL .gs_ico:active,.gs_btnPL :active~.gs_ico{background-position:-89px -58px;}.gs_btnPL .gs_ico.gs_ico_dis,.gs_btnPL:hover .gs_ico_dis{background-position:-84px -152px;}.gs_btnPR .gs_ico{background-position:-131px -47px;}.gs_btnPR:hover .gs_ico{background-position:0 -126px;}.gs_btnPR:active .gs_ico,.gs_btnPR .gs_ico:active,.gs_btnPR :active~.gs_ico{background-position:-110px -68px;}.gs_btnPR .gs_ico.gs_ico_dis,.gs_btnPR:hover .gs_ico_dis{background-position:-105px -152px;}.gs_btnMNU .gs_ico{background-position:-189px -286px;}.gs_btnMNU:hover .gs_ico{background-position:-210px -286px;}.gs_btnMNU:active .gs_ico,.gs_btnMNU .gs_ico:active,.gs_btnMNU :active~.gs_ico{background-position:-210px -265px;}#gs_hdr{position:relative;z-index:900;height:58px;white-space:nowrap;clear:both;}#gs_hdr_bg{position:absolute;top:0;left:0;width:100%;height:57px;border-bottom:1px solid #e5e5e5;z-index:-1;background-color:#f5f5f5;}#gs_hdr_lt{position:absolute;top:0;left:0;width:100%;height:57px;}#gs_hdr_lt .gs_ico_ggl{position:absolute;left:0;top:14px;margin-left:32px;}.gs_el_sm #gs_hdr_lt .gs_ico_ggl{margin-left:16px;}#gs_hdr_lt .gs_ico_ggl a{display:block;width:100%;height:100%;}#gs_hdr_md{position:relative;height:29px;vertical-align:top;margin-left:172px;padding-top:15px;}.gs_el_sm #gs_hdr_md{margin-left:140px;}.gs_el_ta #gs_hdr_md{margin-left:127px;}.gs_el_ph #gs_hdr_md{margin-left:8px;padding-top:9px;}#gs_hdr_frm{position:relative;}.gs_el_ta #gs_hdr_frm{margin-right:94px;max-width:567px;}.gs_el_ph #gs_hdr_frm{margin-right:43px;max-width:736px;}#gs_hdr_frm_in{position:relative;display:inline-block;z-index:10;}.gs_el_ph #gs_hdr_frm_in,.gs_el_ta #gs_hdr_frm_in{display:block;margin-right:16px;width:auto;}#gs_hdr_frm_in_txt{vertical-align:top;width:537px;padding-right:25px;}.gs_el_tc #gs_hdr_frm_in_txt{width:556px;padding-right:6px;}.gs_el_ph #gs_hdr_frm_in_txt,.gs_el_ta #gs_hdr_frm_in_txt{width:100%;padding-left:8px;padding-right:6px;}.gs_el_ph #gs_hdr_frm_in_txt{height:34px;line-height:34px;-webkit-border-radius:2px 0 0 2px;border-radius:2px 0 0 2px;}.gs_el_ta #gs_hdr_frm_ac{right:-16px;}.gs_el_ph #gs_hdr_frm_ac{top:39px;right:-51px;}.gs_el_ph #gs_hdr_arw,.gs_el_ta #gs_hdr_arw,.gs_el_tc #gs_hdr_arw{display:none;}#gs_hdr_tsb{vertical-align:top;margin:0 17px;}.gs_el_ta #gs_hdr_tsb,.gs_el_ph #gs_hdr_tsb{position:absolute;top:0;right:-85px;margin:0;}.gs_el_ph #gs_hdr_tsb{right:-35px;width:36px;height:40px;-webkit-border-radius:0 2px 2px 0;border-radius:0 2px 2px 0;}.gs_el_ta #gs_hdr_tsb .gs_ico{left:28px;}.gs_el_ph #gs_hdr_tsb .gs_ico{left:11px;top:12px;}#gs_hdr_rt{position:absolute;top:0;right:0;height:29px;line-height:27px;color:#666;margin-right:32px;padding-top:15px;}.gs_el_sm #gs_hdr_rt{margin-right:16px;}.gs_el_ta #gs_hdr_rt,.gs_el_ph #gs_hdr_rt{display:none;}#gs_hdr_rt a:link,#gs_hdr_rt a:visited{color:#666}#gs_hdr_rt a:active{color:#d14836}.gs_ico_ggl{width:92px;height:30px;background:no-repeat url(\'/intl/en/scholar/images/1x/googlelogo_color_92x30dp.png\');background-size:92px 30px;}@media(-webkit-min-device-pixel-ratio:1.5),(min-resolution:144dpi){.gs_ico_ggl{background-image:url(\'/intl/en/scholar/images/2x/googlelogo_color_92x30dp.png\');}}.gs_el_ph .gs_ico_ggl{display:none}#gs_ab{position:relative;z-index:800;height:57px;border-bottom:1px solid #DEDEDE;white-space:nowrap;}.gs_el_sm #gs_ab{height:43px}#gs_ab_na{position:absolute;color:#DD4B39;text-decoration:none;top:19px;font-size:16px;margin-left:31px;}.gs_el_sm #gs_ab_na{top:13px;font-size:16px;margin-left:15px;}.gs_el_ph #gs_ab_na{top:12px;font-size:18px;margin-left:8px;}#gs_ab_na .gs_ico{display:none;}#gs_ab_md{position:absolute;color:#999;top:23px;margin-left:181px;}.gs_el_sm #gs_ab_md{top:16px;margin-left:149px;}.gs_el_ta #gs_ab_md{margin-left:127px;}.gs_el_ph #gs_ab_md{display:none;}#gs_ab_md button{position:relative;top:-9px;margin-right:16px}.gs_el_sm #gs_ab_md button{margin-right:8px}#gs_ab_rt{position:relative;float:right;padding-top:14px;padding-right:32px;}.gs_el_sm #gs_ab_rt{padding-top:7px;padding-right:16px;}.gs_el_ta #gs_ab_rt,.gs_el_ph #gs_ab_rt{padding-right:8px;}#gs_ab_rt button{margin-left:16px;vertical-align:top}.gs_el_sm #gs_ab_rt button{margin-left:8px}.gs_el_tc #gs_ab_rt button{margin-left:16px}#gs_bdy{position:relative;z-index:500;clear:both; margin-top:21px;padding-bottom:13px;}#gs_lnv{position:absolute;top:1px;left:0;width:164px;}.gs_el_sm #gs_lnv{width:132px}.gs_el_ta #gs_lnv,.gs_el_ph #gs_lnv{position:relative;top:0;margin-top:-21px;width:auto;border-bottom:1px solid #dedede;}.gs_el_ph #gs_lnv_mnu{display:block;position:absolute;top:0;right:0;z-index:1;padding:5px 8px;background:white;}#gs_lnv_mnu,.gs_lnv_opn #gs_lnv_mnu{display:none}#gs_lnv ul{list-style-type:none;word-wrap:break-word}.gs_el_ta #gs_lnv_pri{margin:0 8px}.gs_el_ph #gs_lnv_pri{margin-right:29px;position:relative;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;height:34px;}.gs_el_ph .gs_lnv_trs #gs_lnv_pri{-webkit-transition:-webkit-transform .13s ease-out;-moz-transition:-moz-transform .13s ease-out;-o-transition:-o-transform .13s ease-out;transition:transform .13s ease-out;}.gs_el_ph.gs_el_tc .gs_lnv_trs #gs_lnv_pri{-webkit-transition:-webkit-transform .218s ease-out;-moz-transition:-moz-transform .218s ease-out;-o-transition:-o-transform .218s ease-out;transition:transform .218s ease-out;}.gs_el_ph .gs_lnv_opn #gs_lnv_pri{margin-right:0;white-space:normal;height:auto;-webkit-transform-origin:0 0;-moz-transform-origin:0 0;-ms-transform-origin:0 0;-o-transform-origin:0 0;transform-origin:0 0;-webkit-transform:scale(1,.25);-moz-transform:scale(1,.25);-ms-transform:scale(1,.25);-o-transform:scale(1,.25);transform:scale(1,.25);}.gs_el_ph .gs_lnv_opn.gs_vis #gs_lnv_pri{-webkit-transform:scale(1,1);-moz-transform:scale(1,1);-ms-transform:scale(1,1);-o-transform:scale(1,1);transform:scale(1,1);}.gs_el_ta #gs_lnv_pri li,.gs_el_ph #gs_lnv_pri li{display:inline-block;}.gs_el_ph .gs_lnv_opn #gs_lnv_pri li{display:block;}#gs_lnv .gs_pad{padding-left:32px}.gs_el_sm #gs_lnv .gs_pad{padding-left:16px}.gs_el_ta #gs_lnv .gs_pad,.gs_el_ph #gs_lnv .gs_pad{padding:0 8px}#gs_lnv .gs_ind,#gs_lnv .gs_inw{margin-bottom:4px}.gs_el_tc #gs_lnv .gs_ind,.gs_el_tc #gs_lnv .gs_inw{margin-bottom:0}#gs_lnv .gs_hr{border-bottom:1px solid #efefef;margin:14px 4px 14px 0;}#gs_lnv a:link,#gs_lnv a:visited{color:#222}#gs_lnv a:active{color:#d14836}#gs_lnv a.gs_in_cb:active{color:#222}#gs_lnv li.gs_sel a:link,#gs_lnv li.gs_sel a:visited,#gs_lnv li.gs_sel a:active,#gs_lnv li.gs_sel a:hover{color:#d14836;text-decoration:none;}#gs_lnv_pri li{line-height:0}#gs_lnv_pri a{display:block;padding:7px 0 6px 32px;line-height:16px;outline:none;}.gs_el_sm #gs_lnv_pri a{padding-left:16px}.gs_el_ta #gs_lnv_pri a,.gs_el_ph #gs_lnv_pri a{padding:7px 8px 11px 8px;}#gs_lnv_pri a:hover,#gs_lnv_pri a:focus{text-decoration:none;background:#eeeeee}#gs_lnv_pri .gs_sel a{border-left:5px solid #dd4b39;padding-left:27px;}.gs_el_sm #gs_lnv_pri .gs_sel a{padding-left:11px}.gs_el_ta #gs_lnv_pri .gs_sel a,.gs_el_ph #gs_lnv_pri .gs_sel a{border-left:none;border-bottom:5px solid #DD4B39;padding:7px 8px 6px 8px;}#gs_ccl{position:relative;padding:0 8px;margin-left:164px;}.gs_el_sm #gs_ccl{margin-left:132px}.gs_el_ph #gs_ccl,.gs_el_ta #gs_ccl{margin:0}.gs_el_ph #gs_hdr{display:none}#gs_settings_ccl{max-width:680px;margin-bottom:48px;line-height:29px;}.gs_el_ta #gs_settings_ccl{padding:0 8px;}#gs_settings_ccl p{line-height:1.5;}.gs_settings_section{border-bottom:1px solid #EEE;padding:1px 20px 10px 0;}.gs_el_ta .gs_settings_section{padding:1px 20px 0 0;}.gs_el_ph .gs_settings_section{padding:1px 0 0 0;}.gs_settings_section h3{margin:11px 0 16px 0;font-size:13px;font-weight:bold;}.gs_settings_section:first-child h3{margin-top:0;}.gs_el_ta .gs_settings_section h3,.gs_el_ph .gs_settings_section h3{margin:8px 0;}.gs_settings_value{margin-bottom:12px;position:relative;line-height:1.5;}#gs_num_table td{vertical-align:middle;}#gs_num_help{padding-left:12px;}.gs_el_ph #gs_num_help{display:none}.gs_el_ph #gs_scisf_md{left:auto;right:0;}#gs_hl-bd{min-width:140px;}#gs_settings_langs_lr{margin-top:8px;}#gs_settings_langs_lr td{padding-left:21px;vertical-align:top;}.gs_el_ph #gs_settings_langs_lr tr,.gs_el_ph #gs_settings_langs_lr td,.gs_el_ph #gs_hl-md ul{display:block;}#gs_settings_liblinks_find{position:relative;margin-right:88px;}#gs_settings_liblinks_find button{position:absolute;right:-80px;top:0;}#gs_settings_liblinks_lst{padding:16px 0;}.gs_el_ph #gs_settings_liblinks_lst .gs_settings_ind{padding-bottom:8px;border-bottom:1px solid #f1f1f1;margin:8px 0;}#gs_settings_account_links{list-style-type:none;margin-top:16px;}#gs_settings_account_links li{padding:7px 0 5px 0;margin:8px 0;}.gs_settings_account_link{padding:7px 0 5px 0;}#gs_settings_button p{line-height:1.24;margin:24px 0;}#gs_settings_buttons{margin:16px 0 32px 0;text-align:right;}#gs_settings_buttons button{margin-left:16px;}</style><script>var gs_ie_ver=100;</script><!--[if lte IE 8]><script>gs_ie_ver=8;</script><![endif]--><script>function gs_id(i){return document.getElementById(i)}function gs_ch(e,t){return e?e.getElementsByTagName(t):[]}function gs_ech(e){return e.children||e.childNodes}function gs_atr(e,a){return e.getAttribute(a)}function gs_hatr(e,a){var n=e.getAttributeNode(a);return n&&n.specified}function gs_xatr(e,a,v){e.setAttribute(a,v)}function gs_uatr(e,a){e.removeAttribute(a)}function gs_catr(e,a,v){gs_hatr(e,a)&&gs_xatr(e,a,v)}function gs_ctai(e,v){gs_hatr(e,"tabindex")&&(e.tabIndex=v)}function gs_uas(s){return (navigator.userAgent||"").indexOf(s)>=0}var gs_is_tc=/[?&]tc=([01])/.exec(window.location.search||""),gs_is_ios=gs_uas("iPhone")||gs_uas("iPod")||gs_uas("iPad");if(gs_is_tc){gs_is_tc=parseInt(gs_is_tc[1]);}else if(window.matchMedia&&matchMedia("(pointer),(-moz-touch-enabled),(-moz-touch-enabled:0)").matches){gs_is_tc=matchMedia("(pointer:coarse),(-moz-touch-enabled)").matches;}else{gs_is_tc=0||(\'ontouchstart\' in window)||(navigator.msMaxTouchPoints||0)>0;}var gs_re_sp=/\\s+/,gs_re_sel=/(?:^|\\s)gs_sel(?!\\S)/g,gs_re_par=/(?:^|\\s)gs_par(?!\\S)/g,gs_re_dis=/(?:^|\\s)gs_dis(?!\\S)/g,gs_re_vis=/(?:^|\\s)gs_vis(?!\\S)/g,gs_re_bsp=/(?:^|\\s)gs_bsp(?!\\S)/g,gs_re_err=/(?:^|\\s)gs_err(?!\\S)/g,gs_re_cb=/(?:^|\\s)gs_in_cb(?!\\S)/,gs_re_ra=/(?:^|\\s)gs_in_ra(?!\\S)/,gs_re_qsp=/[\\s\\u0000-\\u002f\\u003a-\\u0040\\u005b-\\u0060\\u007b-\\u00bf\\u2000-\\u206f\\u2e00-\\u2e42\\u3000-\\u303f\\uff00-\\uff0f\\uff1a-\\uff20\\uff3b-\\uff40\\uff5b-\\uff65]+/;function gs_xcls(e,c){gs_scls(e,e.className+" "+c)}function gs_ucls(e,r){gs_scls(e,e.className.replace(r,""))}function gs_scls(e,c){return e.className!=c&&(e.className=c,true)}function gs_usel(e){gs_ucls(e,gs_re_sel)}function gs_xsel(e){gs_usel(e);gs_xcls(e,"gs_sel")}function gs_tsel(e){return e.className.match(gs_re_sel)}function gs_isel(e){(gs_tsel(e)?gs_usel:gs_xsel)(e)}function gs_upar(e){gs_ucls(e,gs_re_par)}function gs_xpar(e){gs_upar(e);gs_xcls(e,"gs_par")}function gs_udis(e){gs_ucls(e,gs_re_dis)}function gs_xdis(e){gs_udis(e);gs_xcls(e,"gs_dis")}function gs_tdis(e){return e.className.match(gs_re_dis)}function gs_uvis(e){gs_ucls(e,gs_re_vis)}function gs_xvis(e){gs_uvis(e);gs_xcls(e,"gs_vis")}function gs_ubsp(e){gs_ucls(e,gs_re_bsp)}function gs_xbsp(e){gs_ubsp(e);gs_xcls(e,"gs_bsp")}function gs_uerr(e){gs_ucls(e,gs_re_err)}function gs_xerr(e){gs_uerr(e);gs_xcls(e,"gs_err")}var gs_gcs=window.getComputedStyle?function(e){return getComputedStyle(e,null)}:function(e){return e.currentStyle};var gs_ctd=function(){var s=document.documentElement.style,p,l=[\'OT\',\'MozT\',\'webkitT\',\'t\'],i=l.length;function f(s){return Math.max.apply(null,(s||"").split(",").map(parseFloat))||0;}do{p=l[--i]+\'ransition\'}while(i&&!(p in s));return i?function(e){var s=gs_gcs(e);return f(s[p+"Delay"])+f(s[p+"Duration"]);}:function(){return 0};}();var gs_vis=function(){var X,P=0;return function(e,v,c){var s=e&&e.style,h,f;if(s){gs_catr(e,"aria-hidden",v?"false":"true");if(v){s.display=v===2?"inline":"block";gs_ctd(e);gs_xvis(e);f=gs_ctd(e);gs_uas("AppleWebKit")&&f&&gs_evt_one(e,"transitionend webkitTransitionEnd",function(){var t=pageYOffset+e.getBoundingClientRect().bottom;X=X||gs_id("gs_top");++P;t>X.offsetHeight&&(X.style.minHeight=t+"px");});c&&(f?setTimeout(c,1000*f):c());}else{gs_uvis(e);h=function(){s.display="none";if(P&&!--P){X.style.minHeight="";}c&&c();};f=gs_ctd(e);f?setTimeout(h,1000*f):h();}}};}();function gs_visi(i,v,c){gs_vis(gs_id(i),v,c)}function gs_sel_clk(p,t){var l=gs_ch(gs_id(p),"li"),i=l.length,c,x,s;while(i--){if((c=gs_ch(x=l[i],"a")).length){s=c[0]===t;(s?gs_xsel:gs_usel)(x);gs_catr(c[0],"aria-selected",s?"true":"false");}}return false;}function gs_efl(f){if(typeof f=="string"){var c=f.charAt(0),x=f.slice(1);if(c==="#")f=function(t){return t.id===x};else if(c===".")f=function(t){return (" "+t.className+" ").indexOf(" "+x+" ")>=0};else{c=f.toLowerCase();f=function(t){return t.nodeName.toLowerCase()===c};}}return f;}function gs_dfcn(d){return (d?"last":"first")+"Child"}function gs_dnsn(d){return (d?"previous":"next")+"Sibling"}var gs_trv=function(){function h(r,x,f,s,n,c){var t,p;while(x){if(x.nodeType===1){if(f(x)){if(c)return x;}else{for(p=x[s];p;p=p[n])if(t=h(p,p,f,s,n,1))return t;}}c=1;while(1){if(x===r)return;p=x.parentNode;if(x=x[n])break;x=p;}}}return function(r,x,f,d){return h(r,x,gs_efl(f),gs_dfcn(d),gs_dnsn(d))};}();function gs_bind(){var a=Array.prototype.slice.call(arguments),f=a.shift();return function(){return f.apply(null,a.concat(Array.prototype.slice.call(arguments)))};}function gs_evt1(e,n,f){e.addEventListener(n,f,false)}function gs_uevt1(e,n,f){e.removeEventListener(n,f,false)}if(!window.addEventListener){gs_evt1=function(e,n,f){e.attachEvent("on"+n,f)};gs_uevt1=function(e,n,f){e.detachEvent("on"+n,f)};}function gs_evtX(e,n,f,w){var i,a;typeof n==="string"&&(n=n.split(" "));for(i=n.length;i--;)(a=n[i])&&w(e,a,f);}function gs_evt(e,n,f){gs_evtX(e,n,f,gs_evt1)}function gs_uevt(e,n,f){gs_evtX(e,n,f,gs_uevt1)}function gs_evt_one(e,n,f){function g(E){gs_uevt(e,n,g);f(E);}gs_evt(e,n,g);}function gs_evt_all(l,n,f){for(var i=l.length;i--;){gs_evt(l[i],n,gs_bind(f,l[i]))}}function gs_evt_dlg(p,c,n,f){p!==c&&(c=gs_efl(c));gs_evt(p,n,p===c?function(e){f(p,e)}:function(e){var t=gs_evt_tgt(e);while(t){if(c(t))return f(t,e);if(t===p)return;t=t.parentNode;}});}function gs_evt_sms(v){var L=[],l=["mousedown","click"],i=l.length;function s(e){for(var l=L,n=l.length,i=0,x=e.clientX,y=e.clientY;i<n;i+=2){if(Math.abs(x-l[i])<10&&Math.abs(y-l[i+1])<10){gs_evt_ntr(e);break;}}}while(i--)document.addEventListener(l[i],s,true);gs_evt_sms=function(e){var l=e.changedTouches||[],h=l[0]||{};L.push(h.clientX,h.clientY);setTimeout(function(){L.splice(0,2)},2000);};gs_evt_sms(v);v=0;}function gs_evt_clk(e,f,w,k){return gs_evt_dlg_clk(e,e,function(t,e){f(e)},w,k);}function gs_evt_dlg_clk(p,c,f,w,k){k=","+(k||[13,32]).join(",")+",";return gs_evt_dlg_xclk(p,c,function(t,e){if(e.type=="keydown"){if(k.indexOf(","+e.keyCode+",")<0)return;gs_evt_ntr(e);}f(t,e);},w);}function gs_evt_xclk(e,f,w){return gs_evt_dlg_xclk(e,e,function(t,e){f(e)},w);}function gs_evt_dlg_xclk(p,c,f,w){var T,S=0,X=0,Y=0,O=0,V=0;function u(t,e){var n=e.type,h,l;if(t!==T){T=t;S=0;}if(!gs_evt_spk(e)){if(n==="mousedown"){if(w!==2)return S=0;S=1;}else if(n==="click"){if(S){gs_evt_ntr(e);return S=0;}}else if(n==="touchstart"&&w){if(e.timeStamp-V<200){gs_evt_ntr(e);return S=0;}if(w===2){S=0;}else{if((l=e.touches).length!==1)return S=-3;h=l[0];X=h.pageX;Y=h.pageY;O=pageYOffset;return S=3;}}else if(n==="touchcancel"){return S=0;}else if(n==="touchend"&&w){gs_evt_sms(e);V=e.timeStamp;if(w===2){gs_evt_ntr(e);return S=0;}if(S!==3||(l=e.changedTouches).length!==1||Math.abs(X-(h=l[0]).pageX)>10||Math.abs(Y-h.pageY)>10||Math.abs(O-pageYOffset)>1){return S=(e.touches.length?-4:0);}S=0;}else if(n==="keydown"){f(t,e);return;}else if(n==="keyup"){e.keyCode===32&&gs_evt_pdf(e);return;}else{return}gs_evt_ntr(e);f(t,e);}}gs_evt_dlg(p,c,["keydown","keyup","click"].concat(w?["mousedown"].concat((w===2?1:0)?["touchstart","touchend","touchcancel"]:[]):[]),u);return u;}function gs_evt_inp(e,f){gs_evt(e,["input","keyup","cut","paste","change"],function(){setTimeout(f,0)});}function gs_evt_fcs(e,f){e.addEventListener("focus",f,true)}function gs_evt_blr(e,f){e.addEventListener("blur",f,true)}if("onfocusin" in document){gs_evt_fcs=function(e,f){gs_evt(e,"focusin",f)};gs_evt_blr=function(e,f){gs_evt(e,"focusout",f)};}function gs_evt_stp(e){e.cancelBubble=true;e.stopPropagation&&e.stopPropagation();return false;}function gs_evt_pdf(e){e.returnValue=false;e.preventDefault&&e.preventDefault();}function gs_evt_ntr(e){gs_evt_stp(e);gs_evt_pdf(e);}function gs_evt_tgt(e){var t=e.target||e.srcElement;t&&t.nodeType===3&&(t=t.parentNode);return t;}function gs_evt_spk(e){return (e.ctrlKey?1:0)|(e.altKey?2:0)|(e.metaKey?4:0)|(e.shiftKey?8:0);}function gs_tfcs(t){if(!gs_is_tc||(gs_uas("Windows")&&!gs_uas("IEMobile"))){t.focus();t.value=t.value;}}var gs_raf=window.requestAnimationFrame||window.webkitRequestAnimationFrame||window.mozRequestAnimationFrame||function(c){setTimeout(c,33)};var gs_evt_rdy=function(){var d=document,l=[],h=function(){var n=l.length,i=0;while(i<n)l[i++]();l=[];};gs_evt(d,"DOMContentLoaded",h);gs_evt(d,"readystatechange",function(){var s=d.readyState;(s=="complete"||(s=="interactive"&&gs_id("gs_rdy")))&&h();});gs_evt(window,"load",h);return function(f){l.push(f)};}();function gs_evt_raf(e,n){var l=[],t=0,h=function(){var x=l,n=x.length,i=0;while(i<n)x[i++]();t=0;};return function(f){l.length||gs_evt(e,n,function(){!t++&&gs_raf(h)});l.push(f);};}var gs_evt_wsc=gs_evt_raf(window,"scroll"),gs_evt_wre=gs_evt_raf(window,"resize");var gs_md_st=[],gs_md_lv={},gs_md_fc={},gs_md_if,gs_md_is=0;function gs_md_ifc(d,f){gs_md_fc[d]=f}function gs_md_sif(){gs_md_if=1;setTimeout(function(){gs_md_if=0},0);}function gs_md_plv(n){var l=gs_md_lv,x=0;while(n&&!x){x=l[n.id]||0;n=n.parentNode;}return x;}gs_evt(document,"click",function(e){var m=gs_md_st.length;if(m&&!gs_evt_spk(e)&&m>gs_md_plv(gs_evt_tgt(e))){(gs_md_st.pop())();gs_evt_pdf(e);}});gs_evt(document,"keydown",function(e){e.keyCode==27&&!gs_evt_spk(e)&&gs_md_st.length&&(gs_md_st.pop())();});gs_evt(document,"selectstart",function(e){gs_md_is&&gs_evt_pdf(e)});gs_evt_fcs(document,function(e){var l=gs_md_lv,m=gs_md_st.length,x,k,v,d;if(m&&!gs_md_if){x=gs_md_plv(gs_evt_tgt(e));while(x<m){v=0;for(k in l)l.hasOwnProperty(k)&&l[k]>v&&(v=l[d=k]);if(v=gs_md_fc[d]){gs_evt_stp(e);gs_id(v).focus();break;}else{(gs_md_st.pop())(1);--m;!gs_md_is++&&setTimeout(function(){gs_md_is=0},1000);}}}});function gs_md_cls(d,e){var x=gs_md_lv[d]||1e6;while(gs_md_st.length>=x)(gs_md_st.pop())();return gs_evt_stp(e);}function gs_md_shw(d,e,o,c){if(!gs_md_lv[d]){var x=gs_md_plv(gs_id(d));while(gs_md_st.length>x)(gs_md_st.pop())();o&&o();gs_md_st.push(function(u){gs_md_lv[d]=0;c&&c(u);});gs_md_lv[d]=gs_md_st.length;return gs_evt_stp(e);}}function gs_md_opn(d,e,c,z){var a=document.activeElement;return gs_md_shw(d,e,gs_bind(gs_visi,d,1),function(u){gs_visi(d,0,z);try{u||a.focus()}catch(_){}c&&c(u);});}function gs_evt_md_mnu(d,b,f,a,w){var O,X;d=gs_id(d);b=gs_id(b);f=f?gs_efl(f):function(t){return (gs_hatr(t,"data-a")||t.nodeName==="A"&&t.href)&&t.offsetWidth;};a=a||function(t){var c=gs_atr(t,"data-a");c?eval(c):t.nodeName==="A"&&t.href&&(location=t.href);};function u(e){if(e.type=="keydown"){var k=e.keyCode;if(k==38||k==40){if(O){try{gs_trv(d,d,f,k==38).focus()}catch(_){}gs_evt_ntr(e);return;}}else if(k!=13&&k!=32){return;}gs_evt_pdf(e);}if(O){gs_md_cls(d.id,e);}else{gs_md_sif();O=1;gs_xsel(b);gs_md_opn(d.id,e,function(){O=0;gs_usel(b);try{X.blur()}catch(_){}});w&&w();}}function c(x,r){var p=x.parentNode,c=gs_ech(p),i=c.length,l="offsetLeft";if(p!==d){while(c[--i]!==x);p=p[gs_dnsn(r)]||p.parentNode[gs_dfcn(r)];c=gs_ech(p);if(i=Math.min(i+1,c.length)){p=c[i-1];if(p.nodeType==1&&f(p)&&p[l]!=x[l])return p;}}}function g(t,e){function m(x){if(x){gs_evt_ntr(e);x.focus();}}if(O){if(e.type=="keydown"){var k=e.keyCode;if(k==13||k==32){}else{if(k==38||k==40){m(gs_trv(d,t,f,k==38)||gs_trv(d,d,f,k==38));}else if(k==37||k==39){m(c(t,k==37));}return;}}gs_md_cls(d.id,e);gs_evt_pdf(e);gs_md_sif();a(t);}}gs_evt_xclk(b,u,2);gs_evt_fcs(d,function(e){var x=gs_evt_tgt(e);if(x&&f(x)){gs_ctai(x,0);X=x;}});gs_evt_blr(d,function(e){var x=gs_evt_tgt(e);if(x&&f(x)){gs_ctai(x,-1);X=0;}});gs_evt_dlg_xclk(d,f,g,1);return u;}function gs_evt_md_sel(d,b,h,c,s,u){h=gs_id(h);c=gs_id(c);s=gs_id(s);return gs_evt_md_mnu(d,b,function(t){return gs_hatr(t,"data-v")},function(t){h.innerHTML=t.innerHTML;c.value=gs_atr(t,"data-v");if(t!==s){gs_usel(s);gs_uatr(s,"aria-selected");gs_xsel(s=t);gs_xatr(s,"aria-selected","true");}u&&u();},function(){s.focus()});}function gs_xhr(){if(window.XMLHttpRequest)return new XMLHttpRequest();var c=["Microsoft.XMLHTTP","MSXML2.XMLHTTP","MSXML2.XMLHTTP.3.0","MSXML2.XMLHTTP.6.0"],i=c.length;while(i--)try{return new ActiveXObject(c[i])}catch(e){}}function gs_ajax(u,d,c){var r=gs_xhr();r.onreadystatechange=function(){r.readyState==4&&c(r.status,r.responseText);};r.open(d?"POST":"GET",u,true);d&&r.setRequestHeader("Content-Type","application/x-www-form-urlencoded");d?r.send(d):r.send();}var gs_json_parse="JSON" in window?function(s){return JSON.parse(s)}:function(s){return eval("("+s+")")};function gs_frm_ser(e,f){var i=e.length,r=[],x,n,t;while(i--){x=e[i];n=encodeURIComponent(x.name||"");t=x.type;n&&(!f||f(x))&&!x.disabled&&((t!="checkbox"&&t!="radio")||x.checked)&&r.push(n+"="+encodeURIComponent(x.value||""));}return r.join("&");}var gs_rlst,gs_wlst;!function(U){var L={},S;try{S=window.localStorage}catch(_){}gs_rlst=function(k,s){if(s||!(k in L)){var v=S&&S[k];if(v)try{v=JSON.parse(v)}catch(_){v=U}else v=U;L[k]=v;}return L[k];};gs_wlst=function(k,v){L[k]=v;try{S&&(S[k]=JSON.stringify(v))}catch(_){}};}();function gs_ac_nrm(q,t){q=(q||"").toLowerCase().split(gs_re_qsp).join(" ");q[0]==" "&&(q=q.substr(1));var s=q.length-1;t&&q[s]==" "&&(q=q.substr(0,s));return q;}function gs_ac_get(Q){var h=gs_rlst("H:"+Q),t={"":1},i=0,j=0,n,v,q;(h instanceof Array)||(h=[]);for(n=h.length;i<n;i++){((v=h[i]) instanceof Array)&&v.length==3||(v=h[i]=[0,0,""]);v[0]=+v[0]||0;v[1]=+v[1]||0;q=v[2]=gs_ac_nrm(""+v[2],1);t[q]||(t[q]=1,h[j++]=v);}h.splice(Math.min(j,50),n);return h;}function gs_ac_fre(t){return Math.exp(.0231*((Math.max(t-1422777600,0)/86400)|0));}function gs_ac_add(Q,q,d){var h=gs_ac_get(Q),n=h.length,t=1e-3*(new Date()),m=0,x;if(q=gs_ac_nrm(q,1)){d=d||t;while(m<n&&h[m][2]!=q)++m;m<n||h.push([0,0,q]);if(d-h[m][0]>1){h[m][0]=d;h[m][1]=Math.min(h[m][1]+gs_ac_fre(d),10*gs_ac_fre(t));while(m&&h[m][1]>h[m-1][1]){x=h[m];h[m]=h[m-1];h[--m]=x;}h.splice(50,h.length);gs_wlst("H:"+Q,h);}}}var gs_evt_el=function(W,D,L){function p(){var r=D.documentElement,w=W.innerWidth||r.offsetWidth,h=W.innerHeight||r.offsetHeight,m="",n,i;if(w&&h){if(w<600)m="gs_el_sm gs_el_ph";else if(w<982)m="gs_el_sm gs_el_ta";else if(w<1060||h<590)m="gs_el_sm";else if(w<1252||h<640)m="gs_el_me";gs_is_tc&&(m+=" gs_el_tc");gs_is_ios&&(m+=" gs_el_ios");if(gs_scls(r,m))for(n=L.length,i=0;i<n;)L[i++]();}}p();gs_evt_wre(p);gs_evt(W,["pageshow","load"],p);return function(f){f();L.push(f)};}(window,document,[]);!function(B,U){gs_evt(document,(B&&"1"?[]:["mousedown","touchstart"]).concat(["contextmenu","click"]),function(e){var t=gs_evt_tgt(e),a="data-clk",w=window,r=document.documentElement,p="http://scholar.google.com"||"http://"+location.host,n,h,c,u;while(t){n=t.nodeName;if(n==="A"&&(h=gs_ie_ver<=8?t.getAttribute("href",2):gs_atr(t,"href"))&&(c=gs_atr(t,a))){u="/scholar_url?url="+encodeURIComponent(h)+"&"+c+"&ws="+(w.innerWidth||r.offsetWidth||0)+"x"+(w.innerHeight||r.offsetHeight||0);if(c.indexOf("&scisig=")>0){gs_xatr(t,"href",p+u);gs_uatr(t,a);}else if(B){B.call(navigator,u);}else if(u!=U.src){(U=new Image()).src=u;setTimeout(function(){U={};},1000);}break;}t=(n==="SPAN"||n==="B"||n==="I"||n==="EM")&&t.parentNode;}});}(navigator.sendBeacon,{});function gs_is_cb(e){var n=e.className||"";return n.match(gs_re_cb)||n.match(gs_re_ra);}function gs_ssel(e){}(function(d){function c(){var v=l,i=v.length,k=p,e,x=gs_id("gs_top");if(x&&!r){gs_evt(x,"click",function(){});r=1;if(!s){clearInterval(t);t=null}}p=i;while(i-->k)gs_is_cb((e=v[i]).parentNode)&&gs_ssel(e);}var s=gs_ie_ver<=8,l=[],p=0,t=setInterval(c,200),r;gs_evt_rdy(function(){c();l=[];clearInterval(t)});if(!s&&gs_is_tc){s=/AppleWebKit\\/([0-9]+)/.exec(navigator.userAgent||"");s=s&&parseInt(s[1])<535;}if(!s)return;l=gs_ch(d,"input");gs_ssel=function(e){var p=e.parentNode,l,i,r;(e.checked?gs_xsel:gs_usel)(p);if(p.className.match(gs_re_ra)){l=e.form.elements[e.name]||[];for(i=l.length;i--;)((r=l[i]).checked?gs_xsel:gs_usel)(r.parentNode);}};gs_evt(d,"click",function(e){var x=gs_evt_tgt(e),p=x.parentNode;gs_is_cb(p)&&x.nodeName==="INPUT"&&gs_ssel(x);});})(document);</script><script>gs_evt_rdy(function(){var d=gs_id("gs_lnv"),p=gs_id("gs_lnv_pri");function f(t){var n=t.nodeName;return ((n==="A"&&t.href)||n==="INPUT"||n==="BUTTON")&&t.offsetWidth;}gs_evt_clk(gs_id("gs_lnv_mnu").firstChild,function(e){var a=document.activeElement;gs_md_shw(d.id,e,function(){gs_scls(d,"gs_lnv_opn");gs_ctd(d);setTimeout(gs_bind(gs_scls,d,"gs_lnv_opn gs_lnv_trs gs_vis"),0);try{gs_trv(p,p,".gs_sel").firstChild.focus()}catch(_){}},function(u){gs_scls(d,"gs_lnv_opn gs_lnv_trs");setTimeout(gs_bind(gs_scls,d,""),1000*gs_ctd(p));try{u||a.focus()}catch(_){}});});gs_evt(p,"keydown",function(e){var k=e.keyCode,x;if(document.documentElement.className.indexOf("gs_el_ph")>=0&&d.className.indexOf("gs_lnv_opn")>=0){if(!gs_evt_spk(e)&&(k==38||k==40)){x=gs_trv(p,document.activeElement,f,k==38)||gs_trv(p,p,f,k==38);try{x.focus()}catch(_){}gs_evt_ntr(e);}else if(k==9){gs_md_cls(d.id,e);gs_evt_pdf(e);}}});});</script></head><body><div id="gs_top"><style>#gs_gb{position:relative;height:30px;background:#2d2d2d;z-index:950;font-size:13px;line-height:16px;-webkit-backface-visibility:hidden;}#gs_gb_lt,#gs_gb_rt,#gs_gb_lp{position:absolute;top:0;white-space:nowrap;}#gs_gb_lt{left:22px}.gs_el_sm #gs_gb_lt{left:6px}.gs_el_ph #gs_gb_lt{display:none}#gs_gb_lp{display:none}#gs_gb_lp:hover,#gs_gb_lp:focus,#gs_gb_lp:active{-webkit-filter:brightness(100%);}.gs_el_ph #gs_gb_lp{display:block;z-index:1;cursor:pointer;top:8px;left:8px;width:48px;height:16px;background:no-repeat url(\'/intl/en/scholar/images/1x/googlelogo_bbb_color_48x16dp.png\');background-size:48px 16px;}@media(-webkit-min-device-pixel-ratio:1.5),(min-resolution:144dpi){.gs_el_ph #gs_gb_lp{background-image:url(\'/intl/en/scholar/images/2x/googlelogo_bbb_color_48x16dp.png\');}}#gs_gb_rt{right:22px}.gs_el_sm #gs_gb_rt{right:6px}.gs_el_ta #gs_gb_rt,.gs_el_ph #gs_gb_rt{right:0}#gs_gb_lt a:link,#gs_gb_lt a:visited,#gs_gb_rt a:link,#gs_gb_rt a:visited{display:inline-block;vertical-align:top;height:29px;line-height:27px;padding:2px 10px 0 10px;font-weight:bold;color:#bbb;cursor:pointer;text-decoration:none;}#gs_gb_rt a:link,#gs_gb_rt a:visited{padding:2px 8px 0 8px}#gs_gb_lt a:hover,#gs_gb_lt a:focus,#gs_gb_lt a:active,#gs_gb_rt a:hover,#gs_gb_rt a:focus,#gs_gb_rt a:active{color:white;outline:none;}#gs_gb_ac{top:30px;left:auto;right:6px;width:288px;white-space:normal;}#gs_gb_aw,#gs_gb_ap,.gs_gb_am,#gs_gb_ab{display:block;padding:10px 20px;word-wrap:break-word;}#gs_gb_aw{background:#fef9db;font-size:11px;}#gs_gb_ap,.gs_gb_am{border-bottom:1px solid #ccc;}#gs_gb_aa:link,#gs_gb_aa:visited{float:right;margin-left:8px;color:#1a0dab;}#gs_gb_aa:active{color:#d14836}.gs_gb_am:link,.gs_gb_am:visited{color:#222;text-decoration:none;background:#fbfbfb;}.gs_gb_am:hover,.gs_gb_am:focus{background:#f1f1f1}.gs_gb_am:active{background:#eee}#gs_gb_ab{background:#fbfbfb;overflow:auto;}#gs_gb_aab{float:left}#gs_gb_aso{float:right}</style><div id="gs_gb" role="navigation"><div id="gs_gb_lt"><a href="//www.google.com/webhp?hl=en&amp;">Web</a><a href="//www.google.com/imghp?hl=en&amp;">Images</a><a href="//www.google.com/intl/en/options/">More&hellip;</a></div><a id="gs_gb_lp" aria-label="Web" href="//www.google.com/webhp?hl=en&"></a><div id="gs_gb_rt"><a href="https://accounts.google.com/Login?hl=en&amp;continue=http://scholar.google.com/scholar_settings%3Fsciifh%3D1%26hl%3Den%26as_sdt%3D0,5">Sign in</a></div></div><!--[if lte IE 7]><div class="gs_alrt" style="padding:16px"><div>Sorry, some features may not work in this version of Internet Explorer.</div><div>Please use <a href="//www.google.com/chrome/">Google Chrome</a> or <a href="//www.mozilla.com/firefox/">Mozilla Firefox</a> for the best experience.</div></div><![endif]--><div id="gs_hdr" role="banner"><div id="gs_hdr_bg"></div><div id="gs_hdr_lt"><div class="gs_ico gs_ico_ggl"><a href="/schhp?hl=en&amp;as_sdt=0,5" aria-label="Scholar Home"></a></div></div></div><form action="/scholar_setprefs" id="gs_settings_form"><input type=hidden name=sciifh value="1"><input type="hidden" name="scisig" value="AAGBfm0AAAAAVk46usLDhXI7dbd2vvD7eseXSzaqxjaI"><input type="hidden" name="inststart" value="0"><input type="image" border="0" name="nosubmit" src="/scholar/images/cleardot.gif" tabindex="-1" style="position:absolute;top:0;left:0;width:1px;height:1px"><div id="gs_ab"><a id="gs_ab_na" href="/schhp?hl=en&amp;as_sdt=0,5">Scholar Settings</a></div><div id="gs_bdy" role="main"><script>gs_evt_rdy(function(){var p=gs_id("gs_lnv_pri"),l=gs_ch(p,"a");function g(u){var n=parseInt(u.substr(u.indexOf("#")+1),10),t;isNaN(n)&&(n=0);if(t=l[n]){gs_visi("gs_settings_search",n==0);gs_visi("gs_settings_langs",n==1);gs_visi("gs_settings_liblinks",n==2);gs_visi("gs_settings_account",n==3);gs_visi("gs_settings_button",n==4);n==2&&gs_tfcs(gs_id("gs_instq"));gs_md_cls("gs_lnv",{});gs_sel_clk("gs_lnv_pri",t);}}g(location+"");gs_evt(window,"hashchange",function(){g(location+"")});("onhashchange" in window)||gs_evt_dlg(p,"a","click",function(t){g(t.href)});});</script><div id="gs_lnv"><ul id="gs_lnv_pri" role="tablist"><li class="gs_sel"><a href="#0" role="tab" aria-controls="gs_settings_search" aria-selected="true">Search results</a></li><li><a href="#1" role="tab" aria-controls="gs_settings_langs" aria-selected="false">Languages</a></li><li><a href="#2" role="tab" aria-controls="gs_settings_liblinks" aria-selected="false">Library links</a></li><li><a href="#3" role="tab" aria-controls="gs_settings_account" aria-selected="false">Account</a></li><li><a href="#4" role="tab" aria-controls="gs_settings_button" aria-selected="false">Button</a></li></ul><span id="gs_lnv_mnu"><a href="#" role="button" class="gs_btnMNU gs_in_ib gs_btn_mini"><span class="gs_lbl"></span><span class="gs_ico"></span></a></span></div><div id="gs_ccl"><div id="gs_settings_ccl"><div class="gs_alrt">Your cookies seem to be disabled. <br> Setting preferences will not work until you enable cookies in your browser.<br><a href="//support.google.com/accounts/answer/61416?hl=en">How do I enable cookies?</a></div><div id="gs_settings_search" role="tabpanel" aria-hidden="false"><div class="gs_settings_section"><h3>Collections</h3><div class="gs_settings_value"><div class="gs_settings_ind"><span class="gs_in_ra" onclick="void(0)"><input type="radio" name="as_sdt" value="1,5" id="as_sdt1" checked><label for="as_sdt1">Search articles</label><span class="gs_chk"></span><span class="gs_cbx"></span></span> (<span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="as_sdtp" id="as_sdtp" value="" checked><label for="as_sdtp">include patents</label><span class="gs_chk"></span><span class="gs_cbx"></span></span>).</div><div class="gs_settings_ind"><span class="gs_in_ra" onclick="void(0)"><input type="radio" name="as_sdt" value="2006" id="as_sdt2"><label for="as_sdt2">Search case law</label><span class="gs_chk"></span><span class="gs_cbx"></span></span>.</div><script>gs_evt(gs_id("as_sdt2"),"click",function(){var p=gs_id("as_sdtp");p.checked=false;gs_ssel(p);});gs_evt(gs_id("as_sdtp"),"click",function(){var y=gs_id("as_sdt1"),n=gs_id("as_sdt2");y.checked=true;n.checked=false;gs_ssel(y);gs_ssel(n);});</script></div></div><div class="gs_settings_section"><h3>Results per page</h3><div class="gs_settings_value" style="z-index:90"><table cellpadding="0" id="gs_num_table"><tr><td><input type="hidden" name="num" id="gs_num" value="10"><button type="button" id="gs_num-bd" aria-controls="gs_num-md" aria-haspopup="true" class=" gs_in_se"><span class="gs_wr"><span class="gs_lbl" id="gs_num-ds">10</span><span class="gs_icm"></span></span></button><div id="gs_num-md" class="gs_md_se" role="listbox" aria-hidden="true"><ul><li role="option" tabindex="-1" onclick="" data-v="10" id="gs_num-0" class="gs_sel" aria-selected="true">10</li><li role="option" tabindex="-1" onclick="" data-v="20">20</li></ul></div><script>gs_evt_md_sel("gs_num-md","gs_num-bd","gs_num-ds","gs_num","gs_num-0");</script></td><td id="gs_num_help">Google&#39;s default (10 results) provides the fastest results.</td></tr></table></div></div><div class="gs_settings_section"><h3>Where results open</h3><div class="gs_settings_value gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="newwindow" id="gs_nw" value="1"><label for="gs_nw">Open each selected result in a new browser window.</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div></div><div class="gs_settings_section"><h3>Bibliography manager</h3><div class="gs_settings_value" style="z-index:50"><div class="gs_settings_ind"><span class="gs_in_ra" onclick="void(0)"><input type="radio" name="scis" value="no" id="scis0" checked><label for="scis0">Don\'t show any citation import links.</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div id="gs_sil" class="gs_settings_ind"><span class="gs_in_ra" onclick="void(0)"><input type="radio" name="scis" value="yes" id="scis1"><label for="scis1">Show links to import citations into </label><span class="gs_chk"></span><span class="gs_cbx"></span></span><div class="gs_ibl" style="position:relative;vertical-align:middle;text-indent:0"><input type="hidden" name="scisf" id="gs_scisf" value="4"><button type="button" id="gs_scisf-bd" aria-controls="gs_scisf-md" aria-haspopup="true" class=" gs_in_se"><span class="gs_wr"><span class="gs_lbl" id="gs_scisf-ds">BibTeX</span><span class="gs_icm"></span></span></button><div id="gs_scisf-md" class="gs_md_se" role="listbox" aria-hidden="true"><ul><li role="option" tabindex="-1" onclick="" data-v="4" id="gs_scisf-0" class="gs_sel" aria-selected="true">BibTeX</li><li role="option" tabindex="-1" onclick="" data-v="3">EndNote</li><li role="option" tabindex="-1" onclick="" data-v="2">RefMan</li><li role="option" tabindex="-1" onclick="" data-v="1">RefWorks</li></ul></div><script>gs_evt_md_sel("gs_scisf-md","gs_scisf-bd","gs_scisf-ds","gs_scisf","gs_scisf-0");</script></div>.</div><script>gs_evt_all(gs_ch(gs_id("gs_scisf-md"),"li"),"click",function(){var y=gs_id("scis1"),n=gs_id("scis0");n.checked=false;y.checked=true;gs_ssel(n);gs_ssel(y);});</script></div></div></div><div id="gs_settings_langs" role="tabpanel" style="display:none" aria-hidden="true"><div class="gs_settings_section"><h3>For Google text</h3><div class="gs_settings_value" style="z-index:90"><p>Display Google tips and messages in: </p><input type="hidden" name="hl" id="gs_hl" value="en"><button type="button" id="gs_hl-bd" aria-controls="gs_hl-md" aria-haspopup="true" class=" gs_in_se"><span class="gs_wr"><span class="gs_lbl" id="gs_hl-ds">English</span><span class="gs_icm"></span></span></button><div id="gs_hl-md" class="gs_md_se" role="listbox" aria-hidden="true"><ul><li role="option" tabindex="-1" onclick="" data-v="ar">Arabic</li><li role="option" tabindex="-1" onclick="" data-v="bg">Bulgarian</li><li role="option" tabindex="-1" onclick="" data-v="ca">Catalan</li><li role="option" tabindex="-1" onclick="" data-v="zh-CN">Chinese (Simplified)</li><li role="option" tabindex="-1" onclick="" data-v="zh-TW">Chinese (Traditional)</li><li role="option" tabindex="-1" onclick="" data-v="hr">Croatian</li><li role="option" tabindex="-1" onclick="" data-v="cs">Czech</li><li role="option" tabindex="-1" onclick="" data-v="da">Danish</li><li role="option" tabindex="-1" onclick="" data-v="nl">Dutch</li><li role="option" tabindex="-1" onclick="" data-v="en" id="gs_hl-9" class="gs_sel" aria-selected="true">English</li></ul><ul><li role="option" tabindex="-1" onclick="" data-v="tl">Filipino</li><li role="option" tabindex="-1" onclick="" data-v="fi">Finnish</li><li role="option" tabindex="-1" onclick="" data-v="fr">French</li><li role="option" tabindex="-1" onclick="" data-v="de">German</li><li role="option" tabindex="-1" onclick="" data-v="el">Greek</li><li role="option" tabindex="-1" onclick="" data-v="iw">Hebrew</li><li role="option" tabindex="-1" onclick="" data-v="hi">Hindi</li><li role="option" tabindex="-1" onclick="" data-v="hu">Hungarian</li><li role="option" tabindex="-1" onclick="" data-v="id">Indonesian</li><li role="option" tabindex="-1" onclick="" data-v="it">Italian</li></ul><ul><li role="option" tabindex="-1" onclick="" data-v="ja">Japanese</li><li role="option" tabindex="-1" onclick="" data-v="ko">Korean</li><li role="option" tabindex="-1" onclick="" data-v="lv">Latvian</li><li role="option" tabindex="-1" onclick="" data-v="lt">Lithuanian</li><li role="option" tabindex="-1" onclick="" data-v="no">Norwegian</li><li role="option" tabindex="-1" onclick="" data-v="fa">Persian</li><li role="option" tabindex="-1" onclick="" data-v="pl">Polish</li><li role="option" tabindex="-1" onclick="" data-v="pt-BR">Portuguese (Brazil)</li><li role="option" tabindex="-1" onclick="" data-v="pt-PT">Portuguese (Portugal)</li><li role="option" tabindex="-1" onclick="" data-v="ro">Romanian</li></ul><ul><li role="option" tabindex="-1" onclick="" data-v="ru">Russian</li><li role="option" tabindex="-1" onclick="" data-v="sr">Serbian</li><li role="option" tabindex="-1" onclick="" data-v="sk">Slovak</li><li role="option" tabindex="-1" onclick="" data-v="sl">Slovenian</li><li role="option" tabindex="-1" onclick="" data-v="es">Spanish</li><li role="option" tabindex="-1" onclick="" data-v="sv">Swedish</li><li role="option" tabindex="-1" onclick="" data-v="th">Thai</li><li role="option" tabindex="-1" onclick="" data-v="tr">Turkish</li><li role="option" tabindex="-1" onclick="" data-v="uk">Ukrainian</li><li role="option" tabindex="-1" onclick="" data-v="vi">Vietnamese</li></ul></div><script>gs_evt_md_sel("gs_hl-md","gs_hl-bd","gs_hl-ds","gs_hl","gs_hl-9");</script></div></div><div class="gs_settings_section"><h3>For search results</h3><div class="gs_settings_value"><div class="gs_settings_ind"><span class="gs_in_ra" onclick="void(0)"><input type="radio" name="lang" value="all" id="gs_alc" checked><label for="gs_alc">Search for pages written in any language</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_ra" onclick="void(0)"><input type="radio" name="lang" value="some" id="gs_slc"><label for="gs_slc">Search only for pages written in these language(s): </label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><table id="gs_settings_langs_lr"><tr><td><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_zh-CN" value="lang_zh-CN"><label for="gs_lr_zh-CN">Chinese (Simplified)</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_zh-TW" value="lang_zh-TW"><label for="gs_lr_zh-TW">Chinese (Traditional)</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_nl" value="lang_nl"><label for="gs_lr_nl">Dutch</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_en" value="lang_en"><label for="gs_lr_en">English</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_fr" value="lang_fr"><label for="gs_lr_fr">French</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div></td><td><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_de" value="lang_de"><label for="gs_lr_de">German</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_it" value="lang_it"><label for="gs_lr_it">Italian</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_ja" value="lang_ja"><label for="gs_lr_ja">Japanese</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_ko" value="lang_ko"><label for="gs_lr_ko">Korean</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_pl" value="lang_pl"><label for="gs_lr_pl">Polish</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div></td><td><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_pt" value="lang_pt"><label for="gs_lr_pt">Portuguese</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_es" value="lang_es"><label for="gs_lr_es">Spanish</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="lr" id="gs_lr_tr" value="lang_tr"><label for="gs_lr_tr">Turkish</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div></td></tr></table><script>function gs_settings_lrs(){return gs_ch(gs_id("gs_settings_langs_lr"),"input")}gs_evt(gs_id("gs_alc"),"click",function(){var l=gs_settings_lrs(),i=l.length;while(i--){l[i].checked=false;gs_ssel(l[i])}});gs_evt_all(gs_settings_lrs(),"click",function(){var l=gs_settings_lrs(),i=l.length,c=0,a=gs_id("gs_alc"),s=gs_id("gs_slc");while(i--){l[i].checked&&c++}a.checked=(c<=0);s.checked=(c>0);gs_ssel(a);gs_ssel(s);});</script></div></div></div><div id="gs_settings_liblinks" role="tabpanel" style="display:none" aria-hidden="true"><div class="gs_settings_section"><h3>Show library access links for (choose up to five libraries):</h3><div class="gs_settings_value"><div id="gs_settings_liblinks_find"><div class="gs_in_txtf"><input type="text" class="gs_in_txt" name="instq" value="" id="gs_instq" maxlength="80" autocapitalize="off" aria-label="Search"></div><button type="submit" name="instfind" aria-label="Find Library" class="gs_btnG gs_in_ib gs_btn_act gs_btn_eml"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico"></span></span></button></div><div class="gs_gray">e.g., <i>Harvard</i></div><div id="gs_settings_liblinks_lst"><div class="gs_settings_ind"><span class="gs_in_cb" onclick="void(0)"><input type="checkbox" name="inst" id="gs_lib_569367360547434339" value="569367360547434339" checked><label for="gs_lib_569367360547434339">Open WorldCat - Library Search</label><span class="gs_chk"></span><span class="gs_cbx"></span></span></div></div><div role="navigation"><span></span></div><p>Online access to library subscriptions is usually restricted to patrons of that library.  You may need to login with your library password, use a campus computer, or configure your browser to use a library proxy. Please visit your library&#39;s website or ask a local librarian for assistance.</p><script>function gs_settings_libs(){return gs_ch(gs_id("gs_settings_liblinks_lst"),"input");}gs_evt_all(gs_settings_libs(),"click",function(t){var l=gs_settings_libs(),i=l.length,c=0;while(i--){l[i].checked&&c++}if(c>5){t.checked=false;gs_ssel(t)}});</script></div></div></div><div id="gs_settings_account" role="tabpanel" style="display:none" aria-hidden="true"><div class="gs_settings_section"><h3>Account</h3><div class="gs_settings_value"><div>You\'re not signed in to your Google account.</div><ul id="gs_settings_account_links"><li><a href="https://accounts.google.com/Login?hl=en&amp;continue=/scholar_settings%3Fhl%3Den%26as_sdt%3D0,5%26sciifh%3D1%233" class="gs_settings_account_link">Sign in</a></li><li><a href="/citations?view_op=delete_account_options&amp;continue=/scholar_settings%3Fhl%3Den%26as_sdt%3D0,5%26sciifh%3D1%233&amp;hl=en&amp;oi=settings" class="gs_settings_account_link">Delete or recover your Scholar account</a></li></ul></div></div></div><div id="gs_settings_button" role="tabpanel" style="display:none" aria-hidden="true"><div class="gs_settings_section"><h3>Scholar Button for your browser</h3><div class="gs_settings_value"><style>#gsb_promo_ping{position:absolute;top:0;left:0;width:1px;height:1px;}#gsb_top{max-width:368px;}#gsb_top{border:1px solid #ccc;}#gsb_box{background:#f1f1f1;padding:8px 16px;border-bottom:1px solid #ccc;}#gsb_box_url{color:#777;background:#fff;border:1px solid #ccc;border-radius:2px;margin-right:34px;padding:2px 4px;line-height:15px;overflow:hidden;white-space:nowrap;}#gsb_box_button{float:right;width:19px;height:19px;background-color:#fff;border-radius:50%;padding:4px 3px 3px 4px;margin:-4px -3px -3px -4px;box-shadow:0 2px 4px rgba(0,0,0,.5);}#gsb_content{position:relative;padding:0 8px 16px 8px;}#gsb_panel{position:absolute;z-index:1;top:5px;right:8px;padding:6px 8px;background:#3d9400;border:1px solid #2e7000;border-radius:4px;color:#fff;box-shadow:0px 2px 4px rgba(0,0,0,.5);font-size:15px;line-height:19px;font-weight:bold;}#gsb_panel_arrow,#gsb_panel_arrow2{position:absolute;width:0;height:0;top:-11px;right:6px;border:11px solid transparent;border-top:none;border-bottom-color:#358000;z-index:1;}#gsb_panel_arrow2{top:-9px;right:8px;border:9px solid transparent;border-top:none;border-bottom-color:#3d9400;}.gsb_panel_item{display:inline-block;margin:0 8px;min-width:25px;vertical-align:middle;text-align:center;white-space:nowrap;}.gsb_panel_item img{vertical-align:middle;}.gsb_panel_quote{display:inline-block;font-size:17px;line-height:19px;margin-top:-2px;}#gsb_top h3{padding:16px 0;font-size:16px;font-weight:normal;}#gsb_top ol{list-style:decimal outside;}#gsb_top li{margin-left:20px;}.gsb_sel{background:#ffc;color:#000;}#gsb_status img{width:16px;height:16px;vertical-align:text-bottom;}#gsb_status>a,#gsb_status>span{display:none;}.gsb_not_installed #gsb_status>a,.gsb_installed #gsb_status>span{display:inline;}</style><div id="gsb_promo"><div id="gsb_top"><div id="gsb_box"><img id="gsb_box_button" alt="Google Scholar Button" src="/intl/en/scholar/images/scholar19-tb.png"><div id="gsb_box_url">https://www.example.edu/paper.pdf</div></div><div id="gsb_content"><div id="gsb_panel"><div id="gsb_panel_arrow"></div><div id="gsb_panel_arrow2"></div><span class="gsb_panel_item"><img alt="Search" src="/intl/en/scholar/images/sprite/search-shared.png"></span><span class="gsb_panel_item">[PDF]</span><span class="gsb_panel_item"><span class="gsb_panel_quote">&#8220;</span>Cite<span class="gsb_panel_quote">&#8221;</span></span></div><h3>Bibliography</h3><ol><li><span dir="ltr">Einstein, A., B. Podolsky, and N. Rosen, 1935, &#8220;<span class="gsb_sel">Can quantum-mechanical description of physical reality be considered complete?</span>&#8221;, Phys. Rev. <b>47</b>, 777-780.</span></li></ol></div></div><p>Sorry, Scholar Button is not available for this browser. It works in recent versions of <a href="https://chrome.google.com/webstore/detail/google-scholar-button/ldipcbpaocekfooobnbcddclnhejkcpn?hl=en">Chrome</a>, <a href="https://addons.mozilla.org/en-US/firefox/addon/google-scholar-button/">Firefox</a>, and Safari.</p></div><script></script></div></div></div><div id="gs_settings_buttons"><button type="submit" name="save" class=" gs_btn_act"><span class="gs_wr"><span class="gs_lbl">Save</span></span></button><button type="button" onclick="window.location=\'/schhp?hl\\x3den\\x26as_sdt\\x3d0,5\'" class=""><span class="gs_wr"><span class="gs_lbl">Cancel</span></span></button><p class="gs_gray">To retain settings, you must turn on <a href="//support.google.com/accounts/answer/61416?hl=en">cookies</a></p></div><div id="gs_ftr" role="contentinfo"><a href="/intl/en/scholar/about.html">About Google Scholar</a> <a href="//www.google.com/intl/en/policies/privacy/">Privacy</a> <a href="//www.google.com/intl/en/policies/terms/">Terms</a> <a href="//support.google.com/scholar/contact/general">Provide feedback</a></div></div></div></div></form></div><div id="gs_rdy"></div></body></html>'

        pdb.set_trace()

        if html is None:
            return False

        # Now parse the required stuff out of the form. We require the
        # "scisig" token to make the upload of our settings acceptable
        # to Google.
        soup = BeautifulSoup(html, "html.parser")

        tag = soup.find(name='form', attrs={'id': 'gs_settings_form'})
        if tag is None:
            ScholarUtils.log('info', 'parsing settings failed: no form')
            return False

        tag = tag.find('input', attrs={'type':'hidden', 'name':'scisig'})
        if tag is None:
            ScholarUtils.log('info', 'parsing settings failed: scisig')
            return False

        urlargs = {'scisig': tag['value'],
                   'num': settings.per_page_results,
                   'scis': 'no',
                   'scisf': ''}

        if settings.citform != 0:
            urlargs['scis'] = 'yes'
            urlargs['scisf'] = '&scisf=%d' % settings.citform
        #pdb.set_trace()
        html = self._get_http_response(url=self.SET_SETTINGS_URL % urlargs,
                                       log_msg='dump of settings result HTML',
                                       err_msg='applying setttings failed')
        if html is None:
            return False

        ScholarUtils.log('info', 'settings applied')
        return True

    def apply_settings_html(self, settings, html_get_settings, html_set_settings):
        """
        Applies settings as provided by a ScholarSettings instance.
        """
        if settings is None or not settings.is_configured():
            return True

        self.settings = settings

        # This is a bit of work. We need to actually retrieve the
        # contents of the Settings pane HTML in order to extract
        # hidden fields before we can compose the query for updating
        # the settings.
        html = html_get_settings
        if html is None:
            return False

        # Now parse the required stuff out of the form. We require the
        # "scisig" token to make the upload of our settings acceptable
        # to Google.
        soup = BeautifulSoup(html, "html.parser")

        tag = soup.find(name='form', attrs={'id': 'gs_settings_form'})
        if tag is None:
            ScholarUtils.log('info', 'parsing settings failed: no form')
            return False

        tag = tag.find('input', attrs={'type':'hidden', 'name':'scisig'})
        if tag is None:
            ScholarUtils.log('info', 'parsing settings failed: scisig')
            return False

        urlargs = {'scisig': tag['value'],
                   'num': settings.per_page_results,
                   'scis': 'no',
                   'scisf': ''}

        if settings.citform != 0:
            urlargs['scis'] = 'yes'
            urlargs['scisf'] = '&scisf=%d' % settings.citform
        pdb.set_trace()
        html = self._get_http_response(url=self.SET_SETTINGS_URL % urlargs,
                                       log_msg='dump of settings result HTML',
                                       err_msg='applying setttings failed')
        if html is None:
            return False

        ScholarUtils.log('info', 'settings applied')
        return True

    def send_query(self, query):
        """
        This method initiates a search query (a ScholarQuery instance)
        with subsequent parsing of the response.
        """
        self.clear_articles()
        self.query = query
        html = self._get_http_response(url=query.get_url(),
                                       log_msg='dump of query response HTML',
                                       err_msg='results retrieval failed')
        if html is None:
            return

        self.parse(html)

    def send_query_html(self, query, html):
        """
        This method initiates a search query (a ScholarQuery instance)
        with subsequent parsing of the response.
        """
        print(query.get_url())
        self.clear_articles()
        self.query = query
        if html is None:
            return
        self.parse(html)

    def get_citation_data(self, article):
        """
        Given an article, retrieves citation link. Note, this requires that
        you adjusted the settings to tell Google Scholar to actually
        provide this information, *prior* to retrieving the article.
        """
        if article['url_citation'] is None:
            return False
        if article.citation_data is not None:
            return True

        ScholarUtils.log('info', 'retrieving citation export data')
        pdb.set_trace()
        data = self._get_http_response(url=article['url_citation'],
                                       log_msg='citation data response',
                                       err_msg='requesting citation data failed')
        if data is None:
            return False

        article.set_citation_data(data)
        return True

    def parse(self, html):
        """
        This method allows parsing of provided HTML content.
        """
        parser = self.Parser(self)
        parser.parse(html)

    def add_article(self, art):
        self.get_citation_data(art)
        self.articles.append(art)

    def clear_articles(self):
        """Clears any existing articles stored from previous queries."""
        self.articles = []

    def save_cookies(self):
        """
        This stores the latest cookies we're using to disk, for reuse in a
        later session.
        """
        if ScholarConf.COOKIE_JAR_FILE is None:
            return False
        try:
            self.cjar.save(ScholarConf.COOKIE_JAR_FILE,
                           ignore_discard=True)
            ScholarUtils.log('info', 'saved cookies file')
            return True
        except Exception as msg:
            ScholarUtils.log('warn', 'could not save cookies file: %s' % msg)
            return False

    def _get_http_response(self, url, log_msg=None, err_msg=None):
        pdb.set_trace()
        """
        Helper method, sends HTTP request and returns response payload.
        """
        if log_msg is None:
            log_msg = 'HTTP response data follow'
        if err_msg is None:
            err_msg = 'request failed'
        try:
            ScholarUtils.log('info', 'requesting %s' % unquote(url))

            req = Request(url=url, headers={'User-Agent': ScholarConf.USER_AGENT})
            hdl = self.opener.open(req)
            html = hdl.read()

            ScholarUtils.log('debug', log_msg)
            ScholarUtils.log('debug', '>>>>' + '-'*68)
            ScholarUtils.log('debug', 'url: %s' % hdl.geturl())
            ScholarUtils.log('debug', 'result: %s' % hdl.getcode())
            ScholarUtils.log('debug', 'headers:\n' + str(hdl.info()))
            ScholarUtils.log('debug', 'data:\n' + html.decode('utf-8')) # For Python 3
            ScholarUtils.log('debug', '<<<<' + '-'*68)

            return html
        except Exception as err:
            ScholarUtils.log('info', err_msg + ': %s' % err)
            return None


def txt(querier, with_globals):
    if with_globals:
        # If we have any articles, check their attribute labels to get
        # the maximum length -- makes for nicer alignment.
        max_label_len = 0
        if len(querier.articles) > 0:
            items = sorted(list(querier.articles[0].attrs.values()),
                           key=lambda item: item[2])
            max_label_len = max([len(str(item[1])) for item in items])

        # Get items sorted in specified order:
        items = sorted(list(querier.query.attrs.values()), key=lambda item: item[2])
        # Find largest label length:
        max_label_len = max([len(str(item[1])) for item in items] + [max_label_len])
        fmt = '[G] %%%ds %%s' % max(0, max_label_len-4)
        for item in items:
            if item[0] is not None:
                print(fmt % (item[1], item[0]))
        if len(items) > 0:
            print

    articles = querier.articles
    for art in articles:
        print(encode(art.as_txt()) + '\n')

def csv(querier, header=False, sep='|'):
    articles = querier.articles
    for art in articles:
        result = art.as_csv(header=header, sep=sep)
        print(encode(result))
        header = False

def citation_export(querier):
    articles = querier.articles
    for art in articles:
        print(art.as_citation() + '\n')


def main():
    usage = """scholar.py [options] <query string>
A command-line interface to Google Scholar.
Examples:
# Retrieve one article written by Einstein on quantum theory:
scholar.py -c 1 --author "albert einstein" --phrase "quantum theory"
# Retrieve a BibTeX entry for that quantum theory paper:
scholar.py -c 1 -C 17749203648027613321 --citation bt
# Retrieve five articles written by Einstein after 1970 where the title
# does not contain the words "quantum" and "theory":
scholar.py -c 5 -a "albert einstein" -t --none "quantum theory" --after 1970"""

    fmt = optparse.IndentedHelpFormatter(max_help_position=50, width=100)
    parser = optparse.OptionParser(usage=usage, formatter=fmt)
    group = optparse.OptionGroup(parser, 'Query arguments',
                                 'These options define search query arguments and parameters.')
    group.add_option('-a', '--author', metavar='AUTHORS', default=None,
                     help='Author name(s)')
    group.add_option('-A', '--all', metavar='WORDS', default=None, dest='allw',
                     help='Results must contain all of these words')
    group.add_option('-s', '--some', metavar='WORDS', default=None,
                     help='Results must contain at least one of these words. Pass arguments in form -s "foo bar baz" for simple words, and -s "a phrase, another phrase" for phrases')
    group.add_option('-n', '--none', metavar='WORDS', default=None,
                     help='Results must contain none of these words. See -s|--some re. formatting')
    group.add_option('-p', '--phrase', metavar='PHRASE', default=None,
                     help='Results must contain exact phrase')
    group.add_option('-t', '--title-only', action='store_true', default=False,
                     help='Search title only')
    group.add_option('-P', '--pub', metavar='PUBLICATIONS', default=None,
                     help='Results must have appeared in this publication')
    group.add_option('--after', metavar='YEAR', default=None,
                     help='Results must have appeared in or after given year')
    group.add_option('--before', metavar='YEAR', default=None,
                     help='Results must have appeared in or before given year')
    group.add_option('--no-patents', action='store_true', default=False,
                     help='Do not include patents in results')
    group.add_option('--no-citations', action='store_true', default=False,
                     help='Do not include citations in results')
    group.add_option('-C', '--cluster-id', metavar='CLUSTER_ID', default=None,
                     help='Do not search, just use articles in given cluster ID')
    group.add_option('-c', '--count', type='int', default=None,
                     help='Maximum number of results')
    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, 'Output format',
                                 'These options control the appearance of the results.')
    group.add_option('--txt', action='store_true',
                     help='Print article data in text format (default)')
    group.add_option('--txt-globals', action='store_true',
                     help='Like --txt, but first print global results too')
    group.add_option('--csv', action='store_true',
                     help='Print article data in CSV form (separator is "|")')
    group.add_option('--csv-header', action='store_true',
                     help='Like --csv, but print header with column names')
    group.add_option('--citation', metavar='FORMAT', default=None,
                     help='Print article details in standard citation format. Argument Must be one of "bt" (BibTeX), "en" (EndNote), "rm" (RefMan), or "rw" (RefWorks).')
    parser.add_option_group(group)

    group = optparse.OptionGroup(parser, 'Miscellaneous')
    group.add_option('--cookie-file', metavar='FILE', default=None,
                     help='File to use for cookie storage. If given, will read any existing cookies if found at startup, and save resulting cookies in the end.')
    group.add_option('-d', '--debug', action='count', default=0,
                     help='Enable verbose logging to stderr. Repeated options increase detail of debug output.')
    group.add_option('-v', '--version', action='store_true', default=False,
                     help='Show version information')
    parser.add_option_group(group)

    options, _ = parser.parse_args()

    # Show help if we have neither keyword search nor author name
    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    if options.debug > 0:
        options.debug = min(options.debug, ScholarUtils.LOG_LEVELS['debug'])
        ScholarConf.LOG_LEVEL = options.debug
        ScholarUtils.log('info', 'using log level %d' % ScholarConf.LOG_LEVEL)

    if options.version:
        print('This is scholar.py %s.' % ScholarConf.VERSION)
        return 0

    if options.cookie_file:
        ScholarConf.COOKIE_JAR_FILE = options.cookie_file

    # Sanity-check the options: if they include a cluster ID query, it
    # makes no sense to have search arguments:
    if options.cluster_id is not None:
        if options.author or options.allw or options.some or options.none \
           or options.phrase or options.title_only or options.pub \
           or options.after or options.before:
            print('Cluster ID queries do not allow additional search arguments.')
            return 1

    querier = ScholarQuerier()
    settings = ScholarSettings()

    if options.citation == 'bt':
        settings.set_citation_format(ScholarSettings.CITFORM_BIBTEX)
    elif options.citation == 'en':
        settings.set_citation_format(ScholarSettings.CITFORM_ENDNOTE)
    elif options.citation == 'rm':
        settings.set_citation_format(ScholarSettings.CITFORM_REFMAN)
    elif options.citation == 'rw':
        settings.set_citation_format(ScholarSettings.CITFORM_REFWORKS)
    elif options.citation is not None:
        print('Invalid citation link format, must be one of "bt", "en", "rm", or "rw".')
        return 1

    querier.apply_settings(settings)

    if options.cluster_id:
        query = ClusterScholarQuery(cluster=options.cluster_id)
    else:
        query = SearchScholarQuery()
        if options.author:
            query.set_author(options.author)
        if options.allw:
            query.set_words(options.allw)
        if options.some:
            query.set_words_some(options.some)
        if options.none:
            query.set_words_none(options.none)
        if options.phrase:
            query.set_phrase(options.phrase)
        if options.title_only:
            query.set_scope(True)
        if options.pub:
            query.set_pub(options.pub)
        if options.after or options.before:
            query.set_timeframe(options.after, options.before)
        if options.no_patents:
            query.set_include_patents(False)
        if options.no_citations:
            query.set_include_citations(False)

    if options.count is not None:
        options.count = min(options.count, ScholarConf.MAX_PAGE_RESULTS)
        query.set_num_page_results(options.count)

    html='<!doctype html><html><head><title>allintitle: -quantum -theory author:albert author:einstein - Google Scholar</title><meta http-equiv="Content-Type" content="text/html;charset=UTF-8"><meta http-equiv="X-UA-Compatible" content="IE=Edge"><meta name="referrer" content="origin-when-crossorigin"><meta name="viewport" content="width=device-width,initial-scale=1,minimum-scale=1,maximum-scale=2"><style>@viewport{width:device-width;min-zoom:1;max-zoom:2;}</style><meta name="format-detection" content="telephone=no"><link rel="shortcut icon" href="/favicon-png.ico"><script>var gs_ts=Number(new Date());</script><style>html,body,form,table,div,h1,h2,h3,h4,h5,h6,img,ol,ul,li,button{margin:0;padding:0;border:0;}table{border-collapse:collapse;border-width:0;empty-cells:show;}#gs_top{position:relative;min-width:964px;-webkit-tap-highlight-color:rgba(0,0,0,0);}#gs_top>*:not(#x){-webkit-tap-highlight-color:rgba(204,204,204,.5);}.gs_el_ph #gs_top,.gs_el_ta #gs_top{min-width:300px;}body,td,input{font-size:13px;font-family:Arial,sans-serif;line-height:1.24}body{background:#fff;color:#222;-webkit-text-size-adjust:100%;-moz-text-size-adjust:none;}.gs_gray{color:#777777}.gs_red{color:#dd4b39}.gs_grn{color:#006621}.gs_lil{font-size:11px}.gs_med{font-size:16px}.gs_hlt{font-weight:bold;}a:link{color:#1a0dab;text-decoration:none}a:visited{color:#660099;text-decoration:none}a:hover,a:active,a:hover .gs_lbl,a:active .gs_lbl,a .gs_lbl:active{text-decoration:underline;outline:none;}a:active,a:active .gs_lbl,a .gs_lbl:active{color:#d14836}.gs_a,.gs_a a:link,.gs_a a:visited{color:#006621}.gs_a a:active{color:#d14836}a.gs_fl:link,.gs_fl a:link{color:#1a0dab}a.gs_fl:visited,.gs_fl a:visited{color:#660099}a.gs_fl:active,.gs_fl a:active{color:#d14836}.gs_fl{color:#777777}.gs_ctc,.gs_ctu{vertical-align:middle;font-size:11px;font-weight:bold}.gs_ctc{color:#1a0dab}.gs_ctg,.gs_ctg2{font-size:13px;font-weight:bold}.gs_ctg{color:#1a0dab}a.gs_pda,.gs_pda a{padding:7px 0 5px 0}.gs_alrt{background:#f9edbe;border:1px solid #f0c36d;padding:0 16px;text-align:center;-webkit-box-shadow:0 2px 4px rgba(0,0,0,.2);-moz-box-shadow:0 2px 4px rgba(0,0,0,.2);box-shadow:0 2px 4px rgba(0,0,0,.2);-webkit-border-radius:2px;-moz-border-radius:2px;border-radius:2px;}.gs_spc{display:inline-block;width:12px}.gs_br{width:0;font-size:0}.gs_ibl{display:inline-block;}.gs_scl:after{content:"";display:table;clear:both;}.gs_ind{padding-left:8px;text-indent:-8px}.gs_ico,.gs_icm{display:inline-block;background:no-repeat url(/intl/en/scholar/images/sprite.png);width:21px;height:21px;font-size:0;}.gs_el_ta .gs_nta,.gs_ota,.gs_el_ph .gs_nph,.gs_oph{display:none}.gs_el_ta .gs_ota,.gs_el_ph .gs_oph{display:inline}.gs_el_ta div.gs_ota,.gs_el_ph div.gs_oph{display:block}#gs_ftr{margin:32px 0 0 0;text-align:center;clear:both;}#gs_ftr a{display:inline-block;margin:0 12px;padding:7px 0 8px 0;}#gs_ftr a:link,#gs_ftr a:visited{color:#1a0dab}#gs_ftr a:active{color:#d14836}.gs_in_txt{color:black;background:#fff;font-size:16px;height:23px;line-height:23px;border:1px solid #d9d9d9;border-top:1px solid #c0c0c0;padding:3px 6px 1px 8px;-webkit-border-radius:1px;-moz-border-radius:1px;border-radius:1px;outline:none;vertical-align:middle;-webkit-appearance:none;-moz-appearance:none;}.gs_el_tc .gs_in_txt{font-size:18px;}.gs_in_txt:hover{border:1px solid #b9b9b9;border-top:1px solid #a0a0a0;-webkit-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.1);-moz-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.1);box-shadow:inset 0px 1px 2px rgba(0,0,0,0.1);}.gs_in_txte,.gs_in_txte:hover{border:1px solid #DD4B39;}.gs_in_txt:focus{border:1px solid #4d90fe;-webkit-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.3);-moz-box-shadow:inset 0px 1px 2px rgba(0,0,0,0.3);box-shadow:inset 0px 1px 2px rgba(0,0,0,0.3);}input.gs_mini{font-size:13px;height:16px;line-height:16px;padding:3px 6px;}.gs_el_tc input.gs_mini{font-size:13px;height:21px;line-height:21px;}.gs_in_txtf{margin-right:16px}.gs_in_txtm{margin-right:14px}.gs_in_txtf .gs_in_txt,.gs_in_txtm .gs_in_txt{width:100%;}.gs_in_txts{font-size:13px;line-height:18px;}button{position:relative; z-index:1; -moz-box-sizing:border-box;-webkit-box-sizing:border-box;box-sizing:border-box;font-size:11px;font-weight:bold;cursor:default;height:29px;min-width:72px;overflow:visible;color:#444;border:1px solid #dcdcdc;border:1px solid rgba(0,0,0,.1);-webkit-border-radius:2px;-moz-border-radius:2px;border-radius:2px;text-align:center;background-color:#f5f5f5;background-image:-webkit-gradient(linear,left top,left bottom,from(#f5f5f5),to(#f1f1f1));background-image:-webkit-linear-gradient(top,#f5f5f5,#f1f1f1);background-image:-moz-linear-gradient(top,#f5f5f5,#f1f1f1);background-image:-o-linear-gradient(top,#f5f5f5,#f1f1f1);background-image:linear-gradient(to bottom,#f5f5f5,#f1f1f1);-webkit-transition:all .218s;-moz-transition:all .218s;-o-transition:all .218s;transition:all .218s;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;}button .gs_wr{line-height:27px;}button.gs_btn_mini{min-width:26px;height:26px;}.gs_btn_mini .gs_wr{line-height:24px;}.gs_btn_half,.gs_el_ph .gs_btn_hph{min-width:36px;}>. }}.gs_btn_slt{-webkit-border-radius:2px 0 0 2px;-moz-border-radius:2px 0 0 2px;border-radius:2px 0 0 2px;}.gs_btn_srt{margin-left:-1px;-webkit-border-radius:0 2px 2px 0;-moz-border-radius:0 2px 2px 0;border-radius:0 2px 2px 0;}.gs_btn_smd{margin-left:-1px;-webkit-border-radius:0;-moz-border-radius:0;border-radius:0;}button:hover{z-index:2;color:#222;border:1px solid #c6c6c6;-webkit-box-shadow:0px 1px 1px rgba(0,0,0,.1);-moz-box-shadow:0px 1px 1px rgba(0,0,0,.1);box-shadow:0px 1px 1px rgba(0,0,0,.1);background-color:#f8f8f8;background-image:-webkit-gradient(linear,left top,left bottom,from(#f8f8f8),to(#f1f1f1));background-image:-webkit-linear-gradient(top,#f8f8f8,#f1f1f1);background-image:-moz-linear-gradient(top,#f8f8f8,#f1f1f1);background-image:-o-linear-gradient(top,#f8f8f8,#f1f1f1);background-image:linear-gradient(to bottom,#f8f8f8,#f1f1f1);-webkit-transition:all 0s;-moz-transition:all 0s;-o-transition:all 0s;transition:all 0s;}button.gs_sel{color:#333;border:1px solid #ccc;-webkit-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);-moz-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);box-shadow:inset 0 1px 2px rgba(0,0,0,.1);background-color:#e8e8e8;background-image:-webkit-gradient(linear,left top,left bottom,from(#eee),to(#e0e0e0));background-image:-webkit-linear-gradient(top,#eee,#e0e0e0);background-image:-moz-linear-gradient(top,#eee,#e0e0e0);background-image:-o-linear-gradient(top,#eee,#e0e0e0);background-image:linear-gradient(to bottom,#eee,#e0e0e0);}button:active{z-index:2;color:#333;background-color:#f6f6f6;background-image:-webkit-gradient(linear,left top,left bottom,from(#f6f6f6),to(#f1f1f1));background-image:-webkit-linear-gradient(top,#f6f6f6,#f1f1f1);background-image:-moz-linear-gradient(top,#f6f6f6,#f1f1f1);background-image:-o-linear-gradient(top,#f6f6f6,#f1f1f1);background-image:linear-gradient(to bottom,#f6f6f6,#f1f1f1);-webkit-box-shadow:inset 0px 1px 2px rgba(0,0,0,.1);-moz-box-shadow:inset 0px 1px 2px rgba(0,0,0,.1);box-shadow:inset 0px 1px 2px rgba(0,0,0,.1);}button:focus{z-index:2;outline:none;border:1px solid #4d90fe;}button::-moz-focus-inner{padding:0;border:0}button .gs_lbl{padding:0px 8px;}a.gs_in_ib{position:relative;display:inline-block;line-height:16px;padding:5px 0 6px 0;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;}a.gs_btn_mini{height:24px;line-height:24px;padding:0;}a .gs_lbl,button .gs_lbl{vertical-align:baseline;}a.gs_in_ib .gs_lbl{display:inline-block;padding-left:21px}button.gs_in_ib .gs_lbl{padding-left:29px;}button.gs_btn_mini .gs_lbl,button.gs_btn_half .gs_lbl,button.gs_btn_eml .gs_lbl{padding:11px;}.gs_el_ph .gs_btn_hph .gs_lbl,.gs_el_ph .gs_btn_cph .gs_lbl{padding:11px;font-size:0;visibility:hidden;}.gs_in_ib .gs_ico{position:absolute;top:2px;left:8px;}.gs_btn_mini .gs_ico{top:1px;left:2px;}.gs_btn_half .gs_ico,.gs_el_ph .gs_btn_hph .gs_ico{left:7px}.gs_btn_eml .gs_ico,.gs_el_ph .gs_btn_cph .gs_ico{left:25px}a.gs_in_ib .gs_ico{top:3px;left:0}a.gs_in_ib.gs_md_li .gs_ico{left:14px}.gs_el_tc a.gs_in_ib.gs_md_li .gs_ico{top:11px}a.gs_btn_mini .gs_ico{top:1px;left:0}button.gs_btn_act{color:#fff;-webkit-font-smoothing:antialiased;border:1px solid #3079ed;background-color:#4d90fe;background-image:-webkit-gradient(linear,left top,left bottom,from(#4d90fe),to(#4787ed));background-image:-webkit-linear-gradient(top,#4d90fe,#4787ed);background-image:-moz-linear-gradient(top,#4d90fe,#4787ed);background-image:-o-linear-gradient(top,#4d90fe,#4787ed);background-image:linear-gradient(to bottom,#4d90fe,#4787ed);}button.gs_btn_act:hover{color:#fff;border:1px solid #2f5bb7;background-color:#357ae8;background-image:-webkit-gradient(linear,left top,left bottom,from(#4d90fe),to(#357ae8));background-image:-webkit-linear-gradient(top,#4d90fe,#357ae8);background-image:-moz-linear-gradient(top,#4d90fe,#357ae8);background-image:-o-linear-gradient(top,#4d90fe,#357ae8);background-image:linear-gradient(to bottom,#4d90fe,#357ae8);-webkit-box-shadow:inset 0px 1px 1px rgba(0,0,0,.1);-moz-box-shadow:inset 0px 1px 1px rgba(0,0,0,.1);box-shadow:inset 0px 1px 1px rgba(0,0,0,.1);}button.gs_btnG{width:70px;min-width:0;}button.gs_btn_act:focus{-webkit-box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);-moz-box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);}button.gs_btn_act:focus{border-color:#404040;}button.gs_btn_act:active{border:1px solid #315da3;background-color:#2f6de1;background-image:-webkit-gradient(linear,left top,left bottom,from(#4d90fe),to(#2f6de1));background-image:-webkit-linear-gradient(top,#4d90fe,#2f6de1);background-image:-moz-linear-gradient(top,#4d90fe,#2f6de1);background-image:-o-linear-gradient(top,#4d90fe,#2f6de1);background-image:linear-gradient(to bottom,#4d90fe,#2f6de1);}button.gs_btn_act:active{-webkit-box-shadow:inset 0 1px 2px rgba(0,0,0,.3);-moz-box-shadow:inset 0 1px 2px rgba(0,0,0,.3);box-shadow:inset 0 1px 2px rgba(0,0,0,.3);}button.gs_dis,button.gs_dis:hover,button.gs_dis:active{color:#b8b8b8;border:1px solid #f3f3f3;border:1px solid rgba(0,0,0,.05);background:none;-webkit-box-shadow:none;-moz-box-shadow:none;box-shadow:none;z-index:0;}button.gs_btn_act.gs_dis{color:white;border-color:#98bcf6;background:#a6c8ff;}button.gs_dis:active:not(#x){-webkit-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);-moz-box-shadow:inset 0 1px 2px rgba(0,0,0,.1);box-shadow:inset 0 1px 2px rgba(0,0,0,.1);z-index:2;}a.gs_dis{cursor:default}.gs_ttp{position:absolute;top:100%;right:50%;z-index:10;pointer-events:none;visibility:hidden;opacity:0;-webkit-transition:visibility 0s .13s,opacity .13s ease-out;-moz-transition:visibility 0s .13s,opacity .13s ease-out;-o-transition:visibility 0s .13s,opacity .13s ease-out;transition:visibility 0s .13s,opacity .13s ease-out;}button:hover .gs_ttp,button:focus .gs_ttp,a:hover .gs_ttp,a:focus .gs_ttp{-webkit-transition:visibility 0s .3s,opacity .13s ease-in .3s;-moz-transition:visibility 0s .3s,opacity .13s ease-in .3s;-o-transition:visibility 0s .3s,opacity .13s ease-in .3s;transition:visibility 0s .3s,opacity .13s ease-in .3s;visibility:visible;opacity:1;}.gs_ttp .gs_aro,.gs_ttp .gs_aru{position:absolute;top:-2px;right:-5px;width:0;height:0;line-height:0;font-size:0;border:5px solid transparent;border-top:none;border-bottom-color:#2a2a2a;z-index:1;}.gs_ttp .gs_aro{top:-3px;right:-6px;border-width:6px;border-top:none;border-bottom-color:white;}.gs_ttp .gs_txt{display:block;position:relative;top:2px;right:-50%;padding:7px 9px;background:#2a2a2a;color:white;font-size:11px;font-weight:bold;line-height:normal;white-space:nowrap;border:1px solid white;-webkit-box-shadow:inset 0 1px 4px rgba(0,0,0,.2);-moz-box-shadow:inset 0 1px 4px rgba(0,0,0,.2);box-shadow:inset 0 1px 4px rgba(0,0,0,.2);}.gs_in_se,.gs_tan{-ms-touch-action:none;touch-action:none;}.gs_in_se .gs_lbl{padding-left:8px;padding-right:22px;}.gs_in_se .gs_icm{position:absolute;top:8px;right:8px;width:7px;height:11px;margin:0;background-position:-63px -115px;}a.gs_in_se .gs_icm{background-position:-100px -26px;}.gs_in_se:hover .gs_icm{background-position:-166px -110px;}.gs_in_se:active .gs_icm,.gs_in_se .gs_icm:active{background-position:-89px -26px;}.gs_in_se :active~.gs_icm{background-position:-89px -26px;}.gs_el_ph .gs_btn_hph .gs_icm,.gs_el_ph .gs_btn_cph .gs_icm{display:none}.gs_btn_mnu .gs_icm{height:7px;background-position:-63px -119px;}.gs_btn_mnu:hover .gs_icm{background-position:-166px -114px;}.gs_btn_mnu:active .gs_icm,.gs_btn_mnu .gs_icm:active{background-position:-89px -30px;}.gs_btn_mnu :active~.gs_icm{background-position:-89px -30px;}.gs_md_se,.gs_md_wn,.gs_el_ph .gs_md_wp{position:absolute;top:0;left:0;border:1px solid #ccc;border-color:rgba(0,0,0,.2);background:white;-webkit-box-shadow:0px 2px 4px rgba(0,0,0,.2);-moz-box-shadow:0px 2px 4px rgba(0,0,0,.2);box-shadow:0px 2px 4px rgba(0,0,0,.2);z-index:1100; display:none;opacity:0;-webkit-transition:opacity .13s;-moz-transition:opacity .13s;-o-transition:opacity .13s;transition:opacity .13s;}.gs_md_se.gs_vis,.gs_md_wn.gs_vis,.gs_el_ph .gs_md_wp.gs_vis{opacity:1;-webkit-transition:all 0s;-moz-transition:all 0s;-o-transition:all 0s;transition:all 0s;}.gs_el_tc .gs_md_se,.gs_el_tc .gs_md_wn,.gs_el_ph.gs_el_tc .gs_md_wp{-webkit-transform-origin:100% 0;-moz-transform-origin:100% 0;-o-transform-origin:100% 0;transform-origin:100% 0;-webkit-transform:scale(1,0);-moz-transform:scale(1,0);-o-transform:scale(1,0);transform:scale(1,0);-webkit-transition:opacity .218s ease-out,-webkit-transform 0s .218s;-moz-transition:opacity .218s ease-out,-moz-transform: 0s .218s;-o-transition:opacity .218s ease-out,-o-transform: 0s .218s;transition:opacity .218s ease-out,transform 0s .218s;}.gs_el_ios .gs_md_se,.gs_el_ios .gs_md_wn,.gs_el_ph.gs_el_ios .gs_md_wp{-webkit-backface-visibility:hidden;}.gs_el_tc .gs_md_wn.gs_ttss,.gs_el_ph.gs_el_tc .gs_md_wp.gs_ttss{-webkit-transform:scale(0,1);-moz-transform:scale(0,1);-o-transform:scale(0,1);transform:scale(0,1);}.gs_el_tc .gs_md_wn.gs_ttzi,.gs_el_ph.gs_el_tc .gs_md_wp.gs_ttzi{-webkit-transform-origin:50% 50%;-moz-transform-origin:50% 50%;-o-transform-origin:50% 50%;transform-origin:50% 50%;-webkit-transform:scale(0,0);-moz-transform:scale(0,0);-o-transform:scale(0,0);transform:scale(0,0);}.gs_el_tc .gs_md_se.gs_vis,.gs_el_tc .gs_md_wn.gs_vis,.gs_el_ph.gs_el_tc .gs_md_wp.gs_vis{-webkit-transform:scale(1,1);-moz-transform:scale(1,1);-o-transform:scale(1,1);transform:scale(1,1);-webkit-transition:-webkit-transform .218s ease-out;-moz-transition:-moz-transform .218s ease-out;-o-transition:-o-transform .218s ease-out;transition:transform .218s ease-out;}.gs_md_se{white-space:nowrap}.gs_md_se ul{list-style-type:none;word-wrap:break-word;display:inline-block;vertical-align:top;}.gs_md_se li,.gs_md_li,.gs_md_li:link,.gs_md_li:visited{display:block;padding:6px 44px 6px 16px;font-size:13px;line-height:16px;color:#222;cursor:default;text-decoration:none;background:white;-moz-transition:background .13s;-o-transition:background .13s;-webkit-transition:background .13s;transition:background .13s;}a.gs_md_li:hover .gs_lbl,a.gs_md_li:active .gs_lbl{text-decoration:none}.gs_el_tc .gs_md_se li,.gs_el_tc .gs_md_li{padding-top:14px;padding-bottom:10px;}.gs_md_se li:hover,.gs_md_li:hover,.gs_md_li:focus{background:#f1f1f1;-moz-transition:background 0s;-o-transition:background 0s;-webkit-transition:background 0s;transition:background 0s;}.gs_md_se li.gs_sel{color:#dd4b39}.gs_md_wn:focus,.gs_md_se li:focus,.gs_md_li:focus{outline:none}button.gs_btnG .gs_ico{width:14px;height:13px;top:7px;left:27px;background-position:-152px -68px;}a.gs_in_cb:link,a.gs_in_cb:visited,a.gs_in_cb:active,a.gs_in_cb:hover,a.gs_in_cb.gs_dis:active .gs_lbl{cursor:default;color:#222;text-decoration:none;}.gs_in_cb,.gs_in_ra{position:relative;line-height:16px;display:inline-block;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;-webkit-touch-callout:none;}.gs_in_cb.gs_md_li{padding:6px 44px 6px 16px;}.gs_in_cb input,.gs_in_ra input{position:absolute;top:1px;left:1px;width:15px;height:15px;margin:0;padding:0;-moz-opacity:0;opacity:0;filter:alpha(opacity=0);-ms-filter:"alpha(opacity=0)";z-index:2;}.gs_in_ra input{top:0;left:0}.gs_el_tc .gs_in_cb input{top:9px}.gs_el_tc .gs_in_ra input{top:8px}.gs_in_cb.gs_in_cbj input{top:15px;left:15px}.gs_in_cb label,.gs_in_cb .gs_lbl,.gs_in_ra label{display:inline-block;padding-left:21px;min-height:16px;}.gs_el_tc .gs_in_cb label,.gs_el_tc .gs_in_cb .gs_lbl,.gs_el_tc .gs_in_ra label{padding-top:8px;padding-bottom:5px;}.gs_in_cb.gs_in_cbj label,.gs_in_cb.gs_in_cbj .gs_lbl{padding:13px 0 12px 41px;}.gs_in_cb .gs_cbx,.gs_in_ra .gs_cbx{position:absolute}.gs_in_cb .gs_cbx{top:2px;left:2px;width:11px;height:11px;border:1px solid #c6c6c6;-webkit-border-radius:1px;-moz-border-radius:1px;border-radius:1px;}.gs_md_li .gs_cbx{top:8px;left:18px}.gs_el_tc .gs_in_cb .gs_cbx{top:10px}.gs_el_tc .gs_md_li .gs_cbx{top:16px}.gs_in_cb.gs_in_cbj .gs_cbx{top:15px;left:15px}.gs_in_ra .gs_cbx{top:0;left:0;width:15px;height:15px;background:no-repeat url(/intl/en/scholar/images/sprite.png) -42px -110px;}.gs_el_tc .gs_in_ra .gs_cbx{top:8px}.gs_in_ra .gs_cbx:not(#x){background:transparent;border:1px solid #c6c6c6;width:13px;height:13px;-webkit-border-radius:7px;-moz-border-radius:7px;border-radius:7px;}.gs_in_cb:hover .gs_cbx{border-color:#666;-webkit-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);-moz-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);}.gs_in_ra:hover .gs_cbx{background-position:-187px -89px;}.gs_in_ra:hover .gs_cbx:not(#x){border-color:#666;background:transparent;-webkit-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);-moz-box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);box-shadow:inset 0px 1px 1px rgba(0,0,0,0.1);}.gs_in_cb:focus .gs_cbx,.gs_in_cb :focus~.gs_cbx,.gs_in_ra :focus~.gs_cbx:not(#x){border-color:#4d90fe;}.gs_in_cb :active~.gs_cbx{border-color:#666;background:#ebebeb;}.gs_in_cb:active .gs_cbx{border-color:#666;background:#ebebeb;}.gs_in_ra:active .gs_cbx:not(#x),.gs_in_ra :active~.gs_cbx:not(#x){border-color:#666;background:#ebebeb;}.gs_in_ra :active~.gs_cbx,.gs_in_ra:active .gs_cbx{background-position:-21px -66px;}.gs_in_cb :disabled~.gs_cbx,.gs_in_ra :disabled~.gs_cbx{border-color:#f1f1f1;background:transparent;-webkit-box-shadow:none;-moz-box-shadow:none;box-shadow:none;}.gs_in_cb.gs_dis .gs_cbx,.gs_in_ra.gs_dis .gs_cbx{border-color:#f1f1f1;background:transparent;}.gs_in_ra.gs_dis .gs_cbx{background-position:-130px -89px;}.gs_in_cb :disabled~label,.gs_in_ra :disabled~label{color:#b8b8b8;}.gs_in_cb.gs_dis label,.gs_in_ra.gs_dis label{color:#b8b8b8;}.gs_in_cb.gs_err .gs_cbx{border-color:#eda29b;}.gs_in_cb .gs_chk,.gs_in_ra .gs_chk{position:absolute;z-index:1; top:-3px;left:-2px;width:21px;height:21px;}.gs_md_li .gs_chk{top:3px;left:14px}.gs_el_tc .gs_in_cb .gs_chk{top:5px}.gs_el_tc .gs_md_li .gs_chk{top:11px}.gs_in_cb.gs_in_cbj .gs_chk{top:10px;left:10px}.gs_in_ra .gs_chk{top:4px;left:4px;width:7px;height:7px;}.gs_el_tc .gs_in_ra .gs_chk{top:12px}.gs_in_cb input:checked~.gs_chk{ background:no-repeat url(/intl/en/scholar/images/sprite.png) -166px -89px;}.gs_in_ra input:checked~.gs_chk{-webkit-border-radius:4px;-moz-border-radius:4px;border-radius:4px;background:#666;}.gs_in_cb.gs_sel .gs_chk{background:no-repeat url(/intl/en/scholar/images/sprite.png) -166px -89px;}.gs_in_ra.gs_sel .gs_chk{background:no-repeat url(/intl/en/scholar/images/sprite.png) -166px -131px;}.gs_in_cb.gs_par .gs_chk{background:no-repeat url(/intl/en/scholar/images/sprite.png) -188px -265px;}.gs_in_cb input:checked:disabled~.gs_chk{background-position:-209px -67px;}.gs_in_cb.gs_dis.gs_sel .gs_chk{background-position:-209px -67px;}.gs_ico_X{background-position:-166px -26px;}.gs_ico_X:hover{background-position:-131px 0;}.gs_ico_X:active{background-position:0 -63px;}.gs_el_tc .gs_ico_Xt:not(#x){-webkit-background-origin:content;background-origin:content-box;-webkit-background-clip:content;background-clip:content-box;padding:10px 6px 10px 14px;}.gs_btnP .gs_ico{background-position:-89px 0;}a.gs_btnP .gs_ico{background-position:-47px -47px;}.gs_btnP:hover .gs_ico{background-position:-145px -89px;}.gs_btnP:active .gs_ico,.gs_btnP .gs_ico:active,.gs_btnP :active~.gs_ico{background-position:-21px -89px;}.gs_btnC .gs_ico{background-position:-145px -131px;}a.gs_btnC .gs_ico{background-position:0 -42px;}.gs_btnC:hover .gs_ico{background-position:0 -105px;}.gs_btnC:active .gs_ico,.gs_btnC .gs_ico:active,.gs_btnC :active~.gs_ico{background-position:-42px -89px;}.gs_ico_LB{background-position:-84px -265px;height:16px;}.gs_btnJ .gs_ico{background-position:0 -152px;}a.gs_btnJ .gs_ico{background-position:-21px -152px;}.gs_btnJ:hover .gs_ico{background-position:-42px -152px;}.gs_btnJ:active .gs_ico,.gs_btnJ .gs_ico:active,.gs_btnJ :active~.gs_ico{background-position:-63px -152px;}.gs_btnM .gs_ico{background-position:-131px -26px;}a.gs_btnM .gs_ico{background-position:-145px -110px;}.gs_btnM:hover .gs_ico{background-position:-173px -110px;}.gs_btnM:active .gs_ico,.gs_btnM .gs_ico:active,.gs_btnM :active~.gs_ico{background-position:-166px -47px;}.gs_btnSB .gs_ico{background-position:-105px -265px;}a.gs_btnSB .gs_ico{background-position:-126px -265px;}.gs_btnSB:hover .gs_ico{background-position:-147px -265px;}.gs_btnSB:active .gs_ico,.gs_btnSB .gs_ico:active,.gs_btnSB :active~.gs_ico{background-position:-168px -265px;}.gs_btnPL .gs_ico{background-position:-68px -47px;}.gs_btnPL:hover .gs_ico{background-position:0 0;}.gs_btnPL:active .gs_ico,.gs_btnPL .gs_ico:active,.gs_btnPL :active~.gs_ico{background-position:-89px -58px;}.gs_btnPL .gs_ico.gs_ico_dis,.gs_btnPL:hover .gs_ico_dis{background-position:-84px -152px;}.gs_btnPR .gs_ico{background-position:-131px -47px;}.gs_btnPR:hover .gs_ico{background-position:0 -126px;}.gs_btnPR:active .gs_ico,.gs_btnPR .gs_ico:active,.gs_btnPR :active~.gs_ico{background-position:-110px -68px;}.gs_btnPR .gs_ico.gs_ico_dis,.gs_btnPR:hover .gs_ico_dis{background-position:-105px -152px;}.gs_btnFI .gs_ico{background-position:-168px -152px;}.gs_btnFI:hover .gs_ico{background-position:-189px -152px;}.gs_btnFI:active .gs_ico,.gs_btnFI .gs_ico:active,.gs_btnFI :active~.gs_ico{background-position:-210px -152px;}.gs_btnAD .gs_ico{background-position:-47px -68px;}.gs_btnAD:hover .gs_ico{background-position:-47px -26px;}.gs_btnAD:active .gs_ico,.gs_btnAD .gs_ico:active,.gs_btnAD :active~.gs_ico{background-position:0 -84px;}button.gs_btnUB,button.gs_btnUR{border:none;background:none;-webkit-box-shadow:none;-moz-box-shadow:none;box-shadow:none;}button.gs_btnUB .gs_lbl,button.gs_btnUR .gs_lbl{padding:0;}button.gs_btnUR .gs_lbl{color:#fff;text-shadow:0px 1px rgba(0,0,0,.1);}button.gs_btnUR{-webkit-font-smoothing:antialiased;}.gs_btnUB .gs_ico,.gs_btnUR .gs_ico{top:-3px;left:-1px;width:38px;height:34px;z-index:-1;background-position:0 -194px;}.gs_btnUR .gs_ico{background-position:0 -228px;}.gs_btnUB:hover .gs_ico{background-position:-38px -194px;}.gs_btnUR:hover .gs_ico{background-position:-38px -228px;}.gs_btnUB:focus .gs_ico{background-position:-114px -194px;}.gs_btnUR:focus .gs_ico{background-position:-114px -228px;}.gs_btnUB:focus:hover .gs_ico{background-position:-152px -194px;}.gs_btnUR:focus:hover .gs_ico{background-position:-152px -228px;}.gs_btnUB:active .gs_ico,.gs_btnUB .gs_ico:active,.gs_btnUB :active~.gs_ico{background-position:-76px -194px;}.gs_btnUR:active .gs_ico,.gs_btnUR .gs_ico:active,.gs_btnUR :active~.gs_ico{background-position:-76px -228px;}.gs_btnUB:focus:active .gs_ico{background-position:-190px -194px;}.gs_btnUR:focus:active .gs_ico{background-position:-190px -228px;}.gs_ico_nav_previous{background-position:0 -328px;width:53px;height:40px;}.gs_ico_nav_first{background-position:-24px -328px;width:28px;height:40px;}.gs_ico_nav_current{background-position:-53px -328px;width:20px;height:40px;}.gs_ico_nav_next{background-position:-96px -328px;width:71px;height:40px;}.gs_ico_nav_last{background-position:-96px -328px;width:45px;height:40px;}.gs_ico_nav_page{background-position:-74px -328px;width:20px;height:40px;}#gs_hdr{position:relative;z-index:900;height:58px;white-space:nowrap;clear:both;}#gs_hdr_bg{position:absolute;top:0;left:0;width:100%;height:57px;border-bottom:1px solid #e5e5e5;z-index:-1;background-color:#f5f5f5;}#gs_hdr_lt{position:absolute;top:0;left:0;width:100%;height:57px;}#gs_hdr_lt .gs_ico_ggl{position:absolute;left:0;top:14px;margin-left:32px;}.gs_el_sm #gs_hdr_lt .gs_ico_ggl{margin-left:16px;}#gs_hdr_lt .gs_ico_ggl a{display:block;width:100%;height:100%;}#gs_hdr_md{position:relative;height:29px;vertical-align:top;margin-left:172px;padding-top:15px;}.gs_el_sm #gs_hdr_md{margin-left:140px;}.gs_el_ta #gs_hdr_md{margin-left:127px;}.gs_el_ph #gs_hdr_md{margin-left:8px;padding-top:9px;}#gs_hdr_frm{position:relative;}.gs_el_ta #gs_hdr_frm{margin-right:94px;max-width:567px;}.gs_el_ph #gs_hdr_frm{margin-right:43px;max-width:736px;}#gs_hdr_frm_in{position:relative;display:inline-block;z-index:10;}.gs_el_ph #gs_hdr_frm_in,.gs_el_ta #gs_hdr_frm_in{display:block;margin-right:16px;width:auto;}#gs_hdr_frm_in_txt{vertical-align:top;width:537px;padding-right:25px;}.gs_el_tc #gs_hdr_frm_in_txt{width:556px;padding-right:6px;}.gs_el_ph #gs_hdr_frm_in_txt,.gs_el_ta #gs_hdr_frm_in_txt{width:100%;padding-left:8px;padding-right:6px;}.gs_el_ph #gs_hdr_frm_in_txt{height:34px;line-height:34px;-webkit-border-radius:2px 0 0 2px;border-radius:2px 0 0 2px;}.gs_el_ta #gs_hdr_frm_ac{right:-16px;}.gs_el_ph #gs_hdr_frm_ac{top:39px;right:-51px;}.gs_el_ph #gs_hdr_arw,.gs_el_ta #gs_hdr_arw,.gs_el_tc #gs_hdr_arw{display:none;}#gs_hdr_tsb{vertical-align:top;margin:0 17px;}.gs_el_ta #gs_hdr_tsb,.gs_el_ph #gs_hdr_tsb{position:absolute;top:0;right:-85px;margin:0;}.gs_el_ph #gs_hdr_tsb{right:-35px;width:36px;height:40px;-webkit-border-radius:0 2px 2px 0;border-radius:0 2px 2px 0;}.gs_el_ta #gs_hdr_tsb .gs_ico{left:28px;}.gs_el_ph #gs_hdr_tsb .gs_ico{left:11px;top:12px;}#gs_hdr_rt{position:absolute;top:0;right:0;height:29px;line-height:27px;color:#666;margin-right:32px;padding-top:15px;}.gs_el_sm #gs_hdr_rt{margin-right:16px;}.gs_el_ta #gs_hdr_rt,.gs_el_ph #gs_hdr_rt{display:none;}#gs_hdr_rt a:link,#gs_hdr_rt a:visited{color:#666}#gs_hdr_rt a:active{color:#d14836}.gs_ico_ggl{width:92px;height:30px;background:no-repeat url(\'/intl/en/scholar/images/1x/googlelogo_color_92x30dp.png\');background-size:92px 30px;}@media(-webkit-min-device-pixel-ratio:1.5),(min-resolution:144dpi){.gs_ico_ggl{background-image:url(\'/intl/en/scholar/images/2x/googlelogo_color_92x30dp.png\');}}.gs_el_ph .gs_ico_ggl{display:none}#gs_ab{position:relative;z-index:800;height:57px;border-bottom:1px solid #DEDEDE;white-space:nowrap;}.gs_el_sm #gs_ab{height:43px}#gs_ab_na{position:absolute;color:#DD4B39;text-decoration:none;top:19px;font-size:16px;margin-left:31px;}.gs_el_sm #gs_ab_na{top:13px;font-size:16px;margin-left:15px;}.gs_el_ph #gs_ab_na{top:12px;font-size:18px;margin-left:8px;}#gs_ab_na .gs_ico{display:none;}#gs_ab_md{position:absolute;color:#999;top:23px;margin-left:181px;}.gs_el_sm #gs_ab_md{top:16px;margin-left:149px;}.gs_el_ta #gs_ab_md{margin-left:127px;}.gs_el_ph #gs_ab_md{display:none;}#gs_ab_md button{position:relative;top:-9px;margin-right:16px}.gs_el_sm #gs_ab_md button{margin-right:8px}#gs_ab_rt{position:relative;float:right;padding-top:14px;padding-right:32px;}.gs_el_sm #gs_ab_rt{padding-top:7px;padding-right:16px;}.gs_el_ta #gs_ab_rt,.gs_el_ph #gs_ab_rt{padding-right:8px;}#gs_ab_rt button{margin-left:16px;vertical-align:top}.gs_el_sm #gs_ab_rt button{margin-left:8px}.gs_el_tc #gs_ab_rt button{margin-left:16px}#gs_bdy{position:relative;z-index:500;clear:both; margin-top:21px;padding-bottom:13px;}#gs_lnv{position:absolute;top:1px;left:0;width:164px;}.gs_el_sm #gs_lnv{width:132px}.gs_el_ph #gs_lnv,.gs_el_ta #gs_lnv{display:none}#gs_lnv ul{list-style-type:none;word-wrap:break-word}#gs_lnv .gs_pad{padding-left:32px}.gs_el_sm #gs_lnv .gs_pad{padding-left:16px}#gs_lnv .gs_ind,#gs_lnv .gs_inw{margin-bottom:4px}.gs_el_tc #gs_lnv .gs_ind,.gs_el_tc #gs_lnv .gs_inw{margin-bottom:0}#gs_lnv .gs_hr{border-bottom:1px solid #efefef;margin:14px 4px 14px 0;}#gs_lnv a:link,#gs_lnv a:visited{color:#222}#gs_lnv a:active{color:#d14836}#gs_lnv a.gs_in_cb:active{color:#222}#gs_lnv li.gs_sel a:link,#gs_lnv li.gs_sel a:visited,#gs_lnv li.gs_sel a:active,#gs_lnv li.gs_sel a:hover{color:#d14836;text-decoration:none;}#gs_lnv_pri li{line-height:0}#gs_lnv_pri a{display:block;padding:7px 0 6px 32px;line-height:16px;outline:none;}.gs_el_sm #gs_lnv_pri a{padding-left:16px}#gs_lnv_pri a:hover,#gs_lnv_pri a:focus{text-decoration:none;background:#eeeeee}#gs_lnv_pri .gs_sel a{border-left:5px solid #dd4b39;padding-left:27px;}.gs_el_sm #gs_lnv_pri .gs_sel a{padding-left:11px}#gs_ccl{position:relative;padding:0 8px;margin-left:164px;}.gs_el_sm #gs_ccl{margin-left:132px}.gs_el_ph #gs_ccl,.gs_el_ta #gs_ccl{margin:0}#gs_hdr_adv{top:49px;left:0;width:552px;}.gs_el_ta #gs_hdr_adv{width:90%;max-width:546px;}.gs_el_ph #gs_hdr_adv{width:90%;max-width:512px;}#gs_ylo_dd,#gs_ad_dd{position:relative}#gs_ylo_dd{display:none}.gs_el_ta #gs_ylo_dd,.gs_el_ph #gs_ylo_dd,#gs_ad_dd{display:inline-block;}#gs_ylo_md,#gs_ad_md{left:auto;right:0;top:29px;}.gs_el_ph #gs_ylo_md,.gs_el_ph #gs_ad_md{top:0;}#gs_ylo_md a.gs_cur,#gs_ylo_md a:active,#gs_ad_md a.gs_cur,#gs_ad_md a:active{color:#d14836;}#gs_ylo_md .gs_hr,#gs_ad_md .gs_hr{border-bottom:1px solid #efefef;margin:7px 0;}.gs_ad_nlnv{display:none}.gs_el_ta .gs_ad_nlnv,.gs_el_ph .gs_ad_nlnv{display:block}.gs_el_ta #gs_ab_rt .gs_btnC,.gs_el_ph #gs_ab_rt .gs_btnC{display:none}.gs_el_ta #gs_ad_md .gs_btnC,.gs_el_ph #gs_ad_md .gs_btnC{display:block}.gs_btnAD,.gs_btnFI{-ms-touch-action:none;touch-action:none;}.gs_el_ph #gs_lnv,.gs_el_ta #gs_lnv{display:none}.gs_el_tc #gs_lnv_ylo li,.gs_el_tc #gs_lnv_ylo a,.gs_el_tc #gs_lnv_lr li,.gs_el_tc #gs_lnv_lr a,.gs_el_tc #gs_lnv_stype li,.gs_el_tc #gs_lnv_stype a{padding-top:8px;padding-bottom:5px;margin:0;}#gs_lnv_yloc td{padding:5px 0}.gs_el_tc #gs_lnv_yloc td{padding:10px 0}#gs_lnv_yloc .gs_in_txt{width:2.75em}.gs_el_sm #gs_ccl{max-width:980px}.gs_el_ta #gs_ccl{max-width:780px}.gs_r{position:relative;margin:1em 0}.gs_rt{position:relative;font-weight:normal;font-size:17px;line-height:19px}.gs_rt2{font-size:13px;font-weight:normal}.gs_rt a:link,.gs_rt a:link b,.gs_rt2 a:link,.gs_rt2 a:link b{color:#1a0dab}.gs_rt a:visited,.gs_rt a:visited b,.gs_rt2 a:visited,.gs_rt2 a:visited b{color:#660099}.gs_rt a:active,.gs_rt a:active b,.gs_rt2 a:active,.gs_rt2 a:active b{color:#d14836}.gs_ggs{position:absolute;top:0;left:720px;white-space:nowrap;font-size:17px;line-height:19px;}.gs_el_sm .gs_ggs{position:relative;left:0;z-index:1;float:right;padding-left:12px;padding-right:8px;text-align:right;}.gs_el_ph .gs_ggs,.gs_el_ta .gs_ggs{padding-right:0}.gs_ggsL{display:inline}.gs_ggsS{display:none}.gs_el_sm .gs_ggsL{display:none}.gs_el_sm .gs_ggsS{display:inline}.gs_el_tc .gs_ggs .gs_br,.gs_el_ph .gs_ggs .gs_br{height:7px}.gs_el_tc .gs_ggs a,.gs_el_ph .gs_ggs a{display:inline-block;line-height:18px;margin-top:-7px;padding:7px 0 4px 0;}.gs_btnFI{display:none}.gs_el_ph .gs_btnFI{display:inline-block}.gs_el_ph .gs_ggs .gs_md_wp{left:auto;right:0;padding:8px;padding-left:16px;}.gs_ct1{display:inline}.gs_ct2{display:none}.gs_el_ph .gs_ct1{display:none}.gs_el_ph .gs_ct2{display:inline;font-size:13px;font-weight:normal}.gs_ri{max-width:712px}.gs_a a:link,.gs_a a:visited{text-decoration:underline}.gs_ri .gs_fl a,.gs_a a{white-space:nowrap}.gs_ri .gs_fl a.gs_wno{white-space:normal}.gs_svm{display:none}.gs_ri .gs_fl{font-size:1px}.gs_ri .gs_fl a,.gs_svm{font-size:13px;margin-right:12px}.gs_ri .gs_svm a{margin:0}.gs_ri .gs_fl a:last-child,.gs_svm:last-child{margin:0}.gs_nvi,.gs_mvi .gs_mor{display:none}.gs_mvi .gs_nvi,.gs_mvi .gs_nph,.gs_mvi .gs_nta{display:inline}.gs_rs{margin:1px 0}.gs_el_tc .gs_rs{margin:0}.gs_el_ta .gs_rs{margin-right:10%}.gs_el_ph .gs_rs br,.gs_el_ta .gs_rs br{display:none}@media screen and (min-width:670px){.gs_el_ta .gs_rs{margin-right:0}.gs_el_ta .gs_rs br{display:block}}.gs_age{color:#777777}.gs_rs b,.gs_rt b,.gs_rt2 b{color:#000}.gs_el_tc .gs_r{padding:0 0 1em 0;margin:1em 0 0 0;border-bottom:1px solid #eee;}.gs_el_tc .gs_rt a{font-size:17px;line-height:20px;padding:12px 0 9px 0;}.gs_el_tc .gs_rt2 a{font-size:14px;line-height:20px;padding:6px 0 4px 0;}.gs_el_tc .gs_a,.gs_el_tc .gs_a a,.gs_el_tc .gs_ri .gs_fl a{padding:8px 0 5px 0;}.gs_el_tc .gs_ri .gs_fl a{line-height:29px;}#gs_n{clear:both;margin:1.5em 0;width:650px;text-align:center;}#gs_n td{font-size:13px}#gs_n a:link,#gs_n a:visited{color:#1a0dab}#gs_n a:active{color:#d14836}#gs_nm{clear:both;position:relative;text-align:center;max-width:500px;margin:1.5em 50px;font-size:13px;line-height:29px;display:none;}.gs_el_tc #gs_nm{font-size:15px;line-height:41px;}#gs_nm button{position:absolute;top:0}#gs_nm .gs_btnPL{left:-50px}#gs_nm .gs_btnPR{right:-50px}.gs_el_tc #gs_nm button{height:41px}.gs_el_tc #gs_nm button .gs_wr{line-height:39px}.gs_el_tc #gs_nm button .gs_ico{top:8px}#gs_nml{overflow:hidden;white-space:nowrap;width:100%;}.gs_nma{display:inline-block;width:40px;margin:0 5px;}.gs_el_tc #gs_n,.gs_el_ta #gs_n,.gs_el_ph #gs_n{display:none}.gs_el_tc #gs_nm,.gs_el_ta #gs_nm,.gs_el_ph #gs_nm{display:block}.gs_lkp_btm{margin:24px 0}.gs_alrt_btm a:link,.gs_alrt_btm a:visited{color:#444}.gs_alrt_btm a:active{color:#d14836}#gs_ftr{width:650px;}.gs_el_ta #gs_ftr,.gs_el_ph #gs_ftr{width:auto;max-width:600px;}@media print{#gs_gb,#gs_hdr,#gs_ab,#gs_top #gs_lnv,.gs_pda,.gs_ggs,.gs_alrt_btm,#gs_top #gs_n,#gs_top #gs_nm,#gs_ftr,#gs_top .gs_ctc,#gs_top .gs_ctu,#gs_rt_hdr,.gs_rt_hdr_ttl{display:none}#gs_top,#gs_top #gs_bdy,#gs_top #gs_res_bdy,#gs_top #gs_ccl,#gs_top .gs_r,#gs_top .gs_ri,#gs_top .gs_rs{font-size:9pt;color:black;position:static;float:none;margin:0;padding:0;width:auto;min-width:0;max-width:none;}#gs_top #gs_bdy a{color:blue;text-decoration:none}#gs_top .gs_r{margin:1em 0;page-break-inside:avoid}#gs_top .gs_med,#gs_top .gs_rt{font-size:12pt}#gs_top .gs_a,#gs_top #gs_bdy .gs_a a{font-size:9pt;color:green}#gs_top .gs_fl,#gs_top .gs_fl a{font-size:9pt}#gs_top .gs_rs br{display:inline}}</style><script>var gs_ie_ver=100;</script><!--[if lte IE 8]><script>gs_ie_ver=8;</script><![endif]--><script>function gs_id(i){return document.getElementById(i)}function gs_ch(e,t){return e?e.getElementsByTagName(t):[]}function gs_ech(e){return e.children||e.childNodes}function gs_atr(e,a){return e.getAttribute(a)}function gs_hatr(e,a){var n=e.getAttributeNode(a);return n&&n.specified}function gs_xatr(e,a,v){e.setAttribute(a,v)}function gs_uatr(e,a){e.removeAttribute(a)}function gs_catr(e,a,v){gs_hatr(e,a)&&gs_xatr(e,a,v)}function gs_ctai(e,v){gs_hatr(e,"tabindex")&&(e.tabIndex=v)}function gs_uas(s){return (navigator.userAgent||"").indexOf(s)>=0}var gs_is_tc=/[?&]tc=([01])/.exec(window.location.search||""),gs_is_ios=gs_uas("iPhone")||gs_uas("iPod")||gs_uas("iPad");if(gs_is_tc){gs_is_tc=parseInt(gs_is_tc[1]);}else if(window.matchMedia&&matchMedia("(pointer),(-moz-touch-enabled),(-moz-touch-enabled:0)").matches){gs_is_tc=matchMedia("(pointer:coarse),(-moz-touch-enabled)").matches;}else{gs_is_tc=0||(\'ontouchstart\' in window)||(navigator.msMaxTouchPoints||0)>0;}var gs_re_sp=/\\s+/,gs_re_sel=/(?:^|\\s)gs_sel(?!\\S)/g,gs_re_par=/(?:^|\\s)gs_par(?!\\S)/g,gs_re_dis=/(?:^|\\s)gs_dis(?!\\S)/g,gs_re_vis=/(?:^|\\s)gs_vis(?!\\S)/g,gs_re_bsp=/(?:^|\\s)gs_bsp(?!\\S)/g,gs_re_err=/(?:^|\\s)gs_err(?!\\S)/g,gs_re_cb=/(?:^|\\s)gs_in_cb(?!\\S)/,gs_re_ra=/(?:^|\\s)gs_in_ra(?!\\S)/,gs_re_qsp=/[\\s\\u0000-\\u002f\\u003a-\\u0040\\u005b-\\u0060\\u007b-\\u00bf\\u2000-\\u206f\\u2e00-\\u2e42\\u3000-\\u303f\\uff00-\\uff0f\\uff1a-\\uff20\\uff3b-\\uff40\\uff5b-\\uff65]+/;function gs_xcls(e,c){gs_scls(e,e.className+" "+c)}function gs_ucls(e,r){gs_scls(e,e.className.replace(r,""))}function gs_scls(e,c){return e.className!=c&&(e.className=c,true)}function gs_usel(e){gs_ucls(e,gs_re_sel)}function gs_xsel(e){gs_usel(e);gs_xcls(e,"gs_sel")}function gs_tsel(e){return e.className.match(gs_re_sel)}function gs_isel(e){(gs_tsel(e)?gs_usel:gs_xsel)(e)}function gs_upar(e){gs_ucls(e,gs_re_par)}function gs_xpar(e){gs_upar(e);gs_xcls(e,"gs_par")}function gs_udis(e){gs_ucls(e,gs_re_dis)}function gs_xdis(e){gs_udis(e);gs_xcls(e,"gs_dis")}function gs_tdis(e){return e.className.match(gs_re_dis)}function gs_uvis(e){gs_ucls(e,gs_re_vis)}function gs_xvis(e){gs_uvis(e);gs_xcls(e,"gs_vis")}function gs_ubsp(e){gs_ucls(e,gs_re_bsp)}function gs_xbsp(e){gs_ubsp(e);gs_xcls(e,"gs_bsp")}function gs_uerr(e){gs_ucls(e,gs_re_err)}function gs_xerr(e){gs_uerr(e);gs_xcls(e,"gs_err")}var gs_gcs=window.getComputedStyle?function(e){return getComputedStyle(e,null)}:function(e){return e.currentStyle};var gs_ctd=function(){var s=document.documentElement.style,p,l=[\'OT\',\'MozT\',\'webkitT\',\'t\'],i=l.length;function f(s){return Math.max.apply(null,(s||"").split(",").map(parseFloat))||0;}do{p=l[--i]+\'ransition\'}while(i&&!(p in s));return i?function(e){var s=gs_gcs(e);return f(s[p+"Delay"])+f(s[p+"Duration"]);}:function(){return 0};}();var gs_vis=function(){var X,P=0;return function(e,v,c){var s=e&&e.style,h,f;if(s){gs_catr(e,"aria-hidden",v?"false":"true");if(v){s.display=v===2?"inline":"block";gs_ctd(e);gs_xvis(e);f=gs_ctd(e);gs_uas("AppleWebKit")&&f&&gs_evt_one(e,"transitionend webkitTransitionEnd",function(){var t=pageYOffset+e.getBoundingClientRect().bottom;X=X||gs_id("gs_top");++P;t>X.offsetHeight&&(X.style.minHeight=t+"px");});c&&(f?setTimeout(c,1000*f):c());}else{gs_uvis(e);h=function(){s.display="none";if(P&&!--P){X.style.minHeight="";}c&&c();};f=gs_ctd(e);f?setTimeout(h,1000*f):h();}}};}();function gs_visi(i,v,c){gs_vis(gs_id(i),v,c)}function gs_sel_clk(p,t){var l=gs_ch(gs_id(p),"li"),i=l.length,c,x,s;while(i--){if((c=gs_ch(x=l[i],"a")).length){s=c[0]===t;(s?gs_xsel:gs_usel)(x);gs_catr(c[0],"aria-selected",s?"true":"false");}}return false;}function gs_efl(f){if(typeof f=="string"){var c=f.charAt(0),x=f.slice(1);if(c==="#")f=function(t){return t.id===x};else if(c===".")f=function(t){return (" "+t.className+" ").indexOf(" "+x+" ")>=0};else{c=f.toLowerCase();f=function(t){return t.nodeName.toLowerCase()===c};}}return f;}function gs_dfcn(d){return (d?"last":"first")+"Child"}function gs_dnsn(d){return (d?"previous":"next")+"Sibling"}var gs_trv=function(){function h(r,x,f,s,n,c){var t,p;while(x){if(x.nodeType===1){if(f(x)){if(c)return x;}else{for(p=x[s];p;p=p[n])if(t=h(p,p,f,s,n,1))return t;}}c=1;while(1){if(x===r)return;p=x.parentNode;if(x=x[n])break;x=p;}}}return function(r,x,f,d){return h(r,x,gs_efl(f),gs_dfcn(d),gs_dnsn(d))};}();function gs_bind(){var a=Array.prototype.slice.call(arguments),f=a.shift();return function(){return f.apply(null,a.concat(Array.prototype.slice.call(arguments)))};}function gs_evt1(e,n,f){e.addEventListener(n,f,false)}function gs_uevt1(e,n,f){e.removeEventListener(n,f,false)}if(!window.addEventListener){gs_evt1=function(e,n,f){e.attachEvent("on"+n,f)};gs_uevt1=function(e,n,f){e.detachEvent("on"+n,f)};}function gs_evtX(e,n,f,w){var i,a;typeof n==="string"&&(n=n.split(" "));for(i=n.length;i--;)(a=n[i])&&w(e,a,f);}function gs_evt(e,n,f){gs_evtX(e,n,f,gs_evt1)}function gs_uevt(e,n,f){gs_evtX(e,n,f,gs_uevt1)}function gs_evt_one(e,n,f){function g(E){gs_uevt(e,n,g);f(E);}gs_evt(e,n,g);}function gs_evt_all(l,n,f){for(var i=l.length;i--;){gs_evt(l[i],n,gs_bind(f,l[i]))}}function gs_evt_dlg(p,c,n,f){p!==c&&(c=gs_efl(c));gs_evt(p,n,p===c?function(e){f(p,e)}:function(e){var t=gs_evt_tgt(e);while(t){if(c(t))return f(t,e);if(t===p)return;t=t.parentNode;}});}function gs_evt_sms(v){var L=[],l=["mousedown","click"],i=l.length;function s(e){for(var l=L,n=l.length,i=0,x=e.clientX,y=e.clientY;i<n;i+=2){if(Math.abs(x-l[i])<10&&Math.abs(y-l[i+1])<10){gs_evt_ntr(e);break;}}}while(i--)document.addEventListener(l[i],s,true);gs_evt_sms=function(e){var l=e.changedTouches||[],h=l[0]||{};L.push(h.clientX,h.clientY);setTimeout(function(){L.splice(0,2)},2000);};gs_evt_sms(v);v=0;}function gs_evt_clk(e,f,w,k){return gs_evt_dlg_clk(e,e,function(t,e){f(e)},w,k);}function gs_evt_dlg_clk(p,c,f,w,k){k=","+(k||[13,32]).join(",")+",";return gs_evt_dlg_xclk(p,c,function(t,e){if(e.type=="keydown"){if(k.indexOf(","+e.keyCode+",")<0)return;gs_evt_ntr(e);}f(t,e);},w);}function gs_evt_xclk(e,f,w){return gs_evt_dlg_xclk(e,e,function(t,e){f(e)},w);}function gs_evt_dlg_xclk(p,c,f,w){var T,S=0,X=0,Y=0,O=0,V=0;function u(t,e){var n=e.type,h,l;if(t!==T){T=t;S=0;}if(!gs_evt_spk(e)){if(n==="mousedown"){if(w!==2)return S=0;S=1;}else if(n==="click"){if(S){gs_evt_ntr(e);return S=0;}}else if(n==="touchstart"&&w){if(e.timeStamp-V<200){gs_evt_ntr(e);return S=0;}if(w===2){S=0;}else{if((l=e.touches).length!==1)return S=-3;h=l[0];X=h.pageX;Y=h.pageY;O=pageYOffset;return S=3;}}else if(n==="touchcancel"){return S=0;}else if(n==="touchend"&&w){gs_evt_sms(e);V=e.timeStamp;if(w===2){gs_evt_ntr(e);return S=0;}if(S!==3||(l=e.changedTouches).length!==1||Math.abs(X-(h=l[0]).pageX)>10||Math.abs(Y-h.pageY)>10||Math.abs(O-pageYOffset)>1){return S=(e.touches.length?-4:0);}S=0;}else if(n==="keydown"){f(t,e);return;}else if(n==="keyup"){e.keyCode===32&&gs_evt_pdf(e);return;}else{return}gs_evt_ntr(e);f(t,e);}}gs_evt_dlg(p,c,["keydown","keyup","click"].concat(w?["mousedown"].concat((w===2?1:0)?["touchstart","touchend","touchcancel"]:[]):[]),u);return u;}function gs_evt_inp(e,f){gs_evt(e,["input","keyup","cut","paste","change"],function(){setTimeout(f,0)});}function gs_evt_fcs(e,f){e.addEventListener("focus",f,true)}function gs_evt_blr(e,f){e.addEventListener("blur",f,true)}if("onfocusin" in document){gs_evt_fcs=function(e,f){gs_evt(e,"focusin",f)};gs_evt_blr=function(e,f){gs_evt(e,"focusout",f)};}function gs_evt_stp(e){e.cancelBubble=true;e.stopPropagation&&e.stopPropagation();return false;}function gs_evt_pdf(e){e.returnValue=false;e.preventDefault&&e.preventDefault();}function gs_evt_ntr(e){gs_evt_stp(e);gs_evt_pdf(e);}function gs_evt_tgt(e){var t=e.target||e.srcElement;t&&t.nodeType===3&&(t=t.parentNode);return t;}function gs_evt_spk(e){return (e.ctrlKey?1:0)|(e.altKey?2:0)|(e.metaKey?4:0)|(e.shiftKey?8:0);}function gs_tfcs(t){if(!gs_is_tc||(gs_uas("Windows")&&!gs_uas("IEMobile"))){t.focus();t.value=t.value;}}var gs_raf=window.requestAnimationFrame||window.webkitRequestAnimationFrame||window.mozRequestAnimationFrame||function(c){setTimeout(c,33)};var gs_evt_rdy=function(){var d=document,l=[],h=function(){var n=l.length,i=0;while(i<n)l[i++]();l=[];};gs_evt(d,"DOMContentLoaded",h);gs_evt(d,"readystatechange",function(){var s=d.readyState;(s=="complete"||(s=="interactive"&&gs_id("gs_rdy")))&&h();});gs_evt(window,"load",h);return function(f){l.push(f)};}();function gs_evt_raf(e,n){var l=[],t=0,h=function(){var x=l,n=x.length,i=0;while(i<n)x[i++]();t=0;};return function(f){l.length||gs_evt(e,n,function(){!t++&&gs_raf(h)});l.push(f);};}var gs_evt_wsc=gs_evt_raf(window,"scroll"),gs_evt_wre=gs_evt_raf(window,"resize");var gs_md_st=[],gs_md_lv={},gs_md_fc={},gs_md_if,gs_md_is=0;function gs_md_ifc(d,f){gs_md_fc[d]=f}function gs_md_sif(){gs_md_if=1;setTimeout(function(){gs_md_if=0},0);}function gs_md_plv(n){var l=gs_md_lv,x=0;while(n&&!x){x=l[n.id]||0;n=n.parentNode;}return x;}gs_evt(document,"click",function(e){var m=gs_md_st.length;if(m&&!gs_evt_spk(e)&&m>gs_md_plv(gs_evt_tgt(e))){(gs_md_st.pop())();gs_evt_pdf(e);}});gs_evt(document,"keydown",function(e){e.keyCode==27&&!gs_evt_spk(e)&&gs_md_st.length&&(gs_md_st.pop())();});gs_evt(document,"selectstart",function(e){gs_md_is&&gs_evt_pdf(e)});gs_evt_fcs(document,function(e){var l=gs_md_lv,m=gs_md_st.length,x,k,v,d;if(m&&!gs_md_if){x=gs_md_plv(gs_evt_tgt(e));while(x<m){v=0;for(k in l)l.hasOwnProperty(k)&&l[k]>v&&(v=l[d=k]);if(v=gs_md_fc[d]){gs_evt_stp(e);gs_id(v).focus();break;}else{(gs_md_st.pop())(1);--m;!gs_md_is++&&setTimeout(function(){gs_md_is=0},1000);}}}});function gs_md_cls(d,e){var x=gs_md_lv[d]||1e6;while(gs_md_st.length>=x)(gs_md_st.pop())();return gs_evt_stp(e);}function gs_md_shw(d,e,o,c){if(!gs_md_lv[d]){var x=gs_md_plv(gs_id(d));while(gs_md_st.length>x)(gs_md_st.pop())();o&&o();gs_md_st.push(function(u){gs_md_lv[d]=0;c&&c(u);});gs_md_lv[d]=gs_md_st.length;return gs_evt_stp(e);}}function gs_md_opn(d,e,c,z){var a=document.activeElement;return gs_md_shw(d,e,gs_bind(gs_visi,d,1),function(u){gs_visi(d,0,z);try{u||a.focus()}catch(_){}c&&c(u);});}function gs_evt_md_mnu(d,b,f,a,w){var O,X;d=gs_id(d);b=gs_id(b);f=f?gs_efl(f):function(t){return (gs_hatr(t,"data-a")||t.nodeName==="A"&&t.href)&&t.offsetWidth;};a=a||function(t){var c=gs_atr(t,"data-a");c?eval(c):t.nodeName==="A"&&t.href&&(location=t.href);};function u(e){if(e.type=="keydown"){var k=e.keyCode;if(k==38||k==40){if(O){try{gs_trv(d,d,f,k==38).focus()}catch(_){}gs_evt_ntr(e);return;}}else if(k!=13&&k!=32){return;}gs_evt_pdf(e);}if(O){gs_md_cls(d.id,e);}else{gs_md_sif();O=1;gs_xsel(b);gs_md_opn(d.id,e,function(){O=0;gs_usel(b);try{X.blur()}catch(_){}});w&&w();}}function c(x,r){var p=x.parentNode,c=gs_ech(p),i=c.length,l="offsetLeft";if(p!==d){while(c[--i]!==x);p=p[gs_dnsn(r)]||p.parentNode[gs_dfcn(r)];c=gs_ech(p);if(i=Math.min(i+1,c.length)){p=c[i-1];if(p.nodeType==1&&f(p)&&p[l]!=x[l])return p;}}}function g(t,e){function m(x){if(x){gs_evt_ntr(e);x.focus();}}if(O){if(e.type=="keydown"){var k=e.keyCode;if(k==13||k==32){}else{if(k==38||k==40){m(gs_trv(d,t,f,k==38)||gs_trv(d,d,f,k==38));}else if(k==37||k==39){m(c(t,k==37));}return;}}gs_md_cls(d.id,e);gs_evt_pdf(e);gs_md_sif();a(t);}}gs_evt_xclk(b,u,2);gs_evt_fcs(d,function(e){var x=gs_evt_tgt(e);if(x&&f(x)){gs_ctai(x,0);X=x;}});gs_evt_blr(d,function(e){var x=gs_evt_tgt(e);if(x&&f(x)){gs_ctai(x,-1);X=0;}});gs_evt_dlg_xclk(d,f,g,1);return u;}function gs_evt_md_sel(d,b,h,c,s,u){h=gs_id(h);c=gs_id(c);s=gs_id(s);return gs_evt_md_mnu(d,b,function(t){return gs_hatr(t,"data-v")},function(t){h.innerHTML=t.innerHTML;c.value=gs_atr(t,"data-v");if(t!==s){gs_usel(s);gs_uatr(s,"aria-selected");gs_xsel(s=t);gs_xatr(s,"aria-selected","true");}u&&u();},function(){s.focus()});}function gs_xhr(){if(window.XMLHttpRequest)return new XMLHttpRequest();var c=["Microsoft.XMLHTTP","MSXML2.XMLHTTP","MSXML2.XMLHTTP.3.0","MSXML2.XMLHTTP.6.0"],i=c.length;while(i--)try{return new ActiveXObject(c[i])}catch(e){}}function gs_ajax(u,d,c){var r=gs_xhr();r.onreadystatechange=function(){r.readyState==4&&c(r.status,r.responseText);};r.open(d?"POST":"GET",u,true);d&&r.setRequestHeader("Content-Type","application/x-www-form-urlencoded");d?r.send(d):r.send();}var gs_json_parse="JSON" in window?function(s){return JSON.parse(s)}:function(s){return eval("("+s+")")};function gs_frm_ser(e,f){var i=e.length,r=[],x,n,t;while(i--){x=e[i];n=encodeURIComponent(x.name||"");t=x.type;n&&(!f||f(x))&&!x.disabled&&((t!="checkbox"&&t!="radio")||x.checked)&&r.push(n+"="+encodeURIComponent(x.value||""));}return r.join("&");}var gs_rlst,gs_wlst;!function(U){var L={},S;try{S=window.localStorage}catch(_){}gs_rlst=function(k,s){if(s||!(k in L)){var v=S&&S[k];if(v)try{v=JSON.parse(v)}catch(_){v=U}else v=U;L[k]=v;}return L[k];};gs_wlst=function(k,v){L[k]=v;try{S&&(S[k]=JSON.stringify(v))}catch(_){}};}();function gs_ac_nrm(q,t){q=(q||"").toLowerCase().split(gs_re_qsp).join(" ");q[0]==" "&&(q=q.substr(1));var s=q.length-1;t&&q[s]==" "&&(q=q.substr(0,s));return q;}function gs_ac_get(Q){var h=gs_rlst("H:"+Q),t={"":1},i=0,j=0,n,v,q;(h instanceof Array)||(h=[]);for(n=h.length;i<n;i++){((v=h[i]) instanceof Array)&&v.length==3||(v=h[i]=[0,0,""]);v[0]=+v[0]||0;v[1]=+v[1]||0;q=v[2]=gs_ac_nrm(""+v[2],1);t[q]||(t[q]=1,h[j++]=v);}h.splice(Math.min(j,50),n);return h;}function gs_ac_fre(t){return Math.exp(.0231*((Math.max(t-1422777600,0)/86400)|0));}function gs_ac_add(Q,q,d){var h=gs_ac_get(Q),n=h.length,t=1e-3*(new Date()),m=0,x;if(q=gs_ac_nrm(q,1)){d=d||t;while(m<n&&h[m][2]!=q)++m;m<n||h.push([0,0,q]);if(d-h[m][0]>1){h[m][0]=d;h[m][1]=Math.min(h[m][1]+gs_ac_fre(d),10*gs_ac_fre(t));while(m&&h[m][1]>h[m-1][1]){x=h[m];h[m]=h[m-1];h[--m]=x;}h.splice(50,h.length);gs_wlst("H:"+Q,h);}}}var gs_evt_el=function(W,D,L){function p(){var r=D.documentElement,w=W.innerWidth||r.offsetWidth,h=W.innerHeight||r.offsetHeight,m="",n,i;if(w&&h){if(w<600)m="gs_el_sm gs_el_ph";else if(w<982)m="gs_el_sm gs_el_ta";else if(w<1060||h<590)m="gs_el_sm";else if(w<1252||h<640)m="gs_el_me";gs_is_tc&&(m+=" gs_el_tc");gs_is_ios&&(m+=" gs_el_ios");if(gs_scls(r,m))for(n=L.length,i=0;i<n;)L[i++]();}}p();gs_evt_wre(p);gs_evt(W,["pageshow","load"],p);return function(f){f();L.push(f)};}(window,document,[]);!function(B,U){gs_evt(document,(B&&"1"?[]:["mousedown","touchstart"]).concat(["contextmenu","click"]),function(e){var t=gs_evt_tgt(e),a="data-clk",w=window,r=document.documentElement,p="http://scholar.google.com"||"http://"+location.host,n,h,c,u;while(t){n=t.nodeName;if(n==="A"&&(h=gs_ie_ver<=8?t.getAttribute("href",2):gs_atr(t,"href"))&&(c=gs_atr(t,a))){u="/scholar_url?url="+encodeURIComponent(h)+"&"+c+"&ws="+(w.innerWidth||r.offsetWidth||0)+"x"+(w.innerHeight||r.offsetHeight||0);if(c.indexOf("&scisig=")>0){gs_xatr(t,"href",p+u);gs_uatr(t,a);}else if(B){B.call(navigator,u);}else if(u!=U.src){(U=new Image()).src=u;setTimeout(function(){U={};},1000);}break;}t=(n==="SPAN"||n==="B"||n==="I"||n==="EM")&&t.parentNode;}});}(navigator.sendBeacon,{});function gs_is_cb(e){var n=e.className||"";return n.match(gs_re_cb)||n.match(gs_re_ra);}function gs_ssel(e){}(function(d){function c(){var v=l,i=v.length,k=p,e,x=gs_id("gs_top");if(x&&!r){gs_evt(x,"click",function(){});r=1;if(!s){clearInterval(t);t=null}}p=i;while(i-->k)gs_is_cb((e=v[i]).parentNode)&&gs_ssel(e);}var s=gs_ie_ver<=8,l=[],p=0,t=setInterval(c,200),r;gs_evt_rdy(function(){c();l=[];clearInterval(t)});if(!s&&gs_is_tc){s=/AppleWebKit\\/([0-9]+)/.exec(navigator.userAgent||"");s=s&&parseInt(s[1])<535;}if(!s)return;l=gs_ch(d,"input");gs_ssel=function(e){var p=e.parentNode,l,i,r;(e.checked?gs_xsel:gs_usel)(p);if(p.className.match(gs_re_ra)){l=e.form.elements[e.name]||[];for(i=l.length;i--;)((r=l[i]).checked?gs_xsel:gs_usel)(r.parentNode);}};gs_evt(d,"click",function(e){var x=gs_evt_tgt(e),p=x.parentNode;gs_is_cb(p)&&x.nodeName==="INPUT"&&gs_ssel(x);});})(document);</script><script>var gs_ellt=null;function gs_svj(s){gs_svk();var n=0;gs_ellt=setInterval(function(){var h="",i=n;while(i--)h+=".";h+="<span style=\'color:white\'>";i=3-n;while(i--)h+=".";h+="</span>";gs_id(s).innerHTML=h;n=(n+1)%4;},200);}function gs_svk(){clearInterval(gs_ellt);gs_ellt=null;}function gs_svw(p,c){gs_visi("gs_svl"+p,0);var a=gs_id("gs_svs"+p);a.href="/citations?view_op\\x3dview_citation\\x26continue\\x3d/scholar%3Fq%3Dallintitle:%2B-quantum%2B-theory%2Bauthor:albert%2Bauthor:einstein%26hl%3Den%26num%3D5%26as_sdt%3D0,5%26as_ylo%3D1970\\x26citilm\\x3d1\\x26citation_for_view\\x3d{id}\\x26hl\\x3den\\x26oi\\x3dsaved".replace("{id}",encodeURIComponent(c));gs_vis(a,2);}function gs_now(){return +new Date();}function gs_sva(d,p){gs_visi("gs_svl"+p,0);gs_visi("gs_sve"+p,0);gs_visi("gs_svs"+p,0);gs_visi("gs_svo"+p,2);gs_svj("gs_svd"+p);gs_ajax("/citations?hl\\x3den\\x26update_op\\x3dlibrary_add\\x26xsrf\\x3dAMstHGQAAAAAVk8aXoLPtIAdJIQRXgAMIIqZT2Bar5LK\\x26info\\x3d{id}".replace("{id}",d),"",function(c,t){var f=t.charAt(0),a,b;gs_visi("gs_svo"+p,0);gs_svk();if(c==200&&t){if(f=="2"){window.location="https://accounts.google.com/Login?hl\\x3den\\x26continue\\x3dhttp://scholar.google.com/scholar%3Fas_q%3D%26as_epq%3D%26as_oq%3D%26as_eq%3Dquantum%2Btheory%26as_occt%3Dtitle%26as_sauthors%3Dalbert%2Beinstein%26as_publication%3D%26as_ylo%3D1970%26as_yhi%3D%26as_sdt%3D0,5%26btnG%3D%26hl%3Den%26num%3D5\\x26service\\x3dcitations\\x26ltmpl\\x3dscholarlibrary";}else if(f=="1"){window.location="/citations?view_op\\x3dlibrary_setup\\x26continue\\x3d/scholar%3Fq%3Dallintitle:%2B-quantum%2B-theory%2Bauthor:albert%2Bauthor:einstein%26hl%3Den%26num%3D5%26as_sdt%3D0,5%26as_ylo%3D1970\\x26info\\x3d{id}\\x26hl\\x3den".replace("{id}",d);}else if(f=="3"){a=t.substr(1).split(":");b=a.length==2?a[1]:"";window.location="/scholar?q\\x3dallintitle:+-quantum+-theory+author:albert+author:einstein\\x26hl\\x3den\\x26num\\x3d5\\x26as_sdt\\x3d0,5\\x26as_ylo\\x3d1970\\x26scilu\\x3d{f1}\\x26scisig\\x3d{f2}".replace("{f1}",a[0]).replace("{f2}",b);}else{a=t.substr(1).split(":");b={};gs_svw(p,a[1]);b[d+","+a[0]]=a[1];gs_svc(b);}}else{gs_visi("gs_sve"+p,2);}});return false;}function gs_svl(){var l=gs_rlst("s",1);return l&&typeof l=="object"?l:{};}function gs_svc(u){u=u||{};var l=gs_svl(),t=gs_now(),k,v;for(k in l)(v=l[k]) instanceof Array&&v.length==2&&t-v[1]<12e5||(delete l[k]);for(k in u)l[k]=[u[k],t];gs_wlst("s",l);}function gs_more(t,v){gs_scls(t.parentNode,"gs_fl"+(v?" gs_mvi":""));return false;}</script></head><body><div id="gs_top"><style>#gs_gb{position:relative;height:30px;background:#2d2d2d;z-index:950;font-size:13px;line-height:16px;-webkit-backface-visibility:hidden;}#gs_gb_lt,#gs_gb_rt,#gs_gb_lp{position:absolute;top:0;white-space:nowrap;}#gs_gb_lt{left:22px}.gs_el_sm #gs_gb_lt{left:6px}.gs_el_ph #gs_gb_lt{display:none}#gs_gb_lp{display:none}#gs_gb_lp:hover,#gs_gb_lp:focus,#gs_gb_lp:active{-webkit-filter:brightness(100%);}.gs_el_ph #gs_gb_lp{display:block;z-index:1;cursor:pointer;top:8px;left:8px;width:48px;height:16px;background:no-repeat url(\'/intl/en/scholar/images/1x/googlelogo_bbb_color_48x16dp.png\');background-size:48px 16px;}@media(-webkit-min-device-pixel-ratio:1.5),(min-resolution:144dpi){.gs_el_ph #gs_gb_lp{background-image:url(\'/intl/en/scholar/images/2x/googlelogo_bbb_color_48x16dp.png\');}}#gs_gb_rt{right:22px}.gs_el_sm #gs_gb_rt{right:6px}.gs_el_ta #gs_gb_rt,.gs_el_ph #gs_gb_rt{right:0}#gs_gb_lt a:link,#gs_gb_lt a:visited,#gs_gb_rt a:link,#gs_gb_rt a:visited{display:inline-block;vertical-align:top;height:29px;line-height:27px;padding:2px 10px 0 10px;font-weight:bold;color:#bbb;cursor:pointer;text-decoration:none;}#gs_gb_rt a:link,#gs_gb_rt a:visited{padding:2px 8px 0 8px}#gs_gb_lt a:hover,#gs_gb_lt a:focus,#gs_gb_lt a:active,#gs_gb_rt a:hover,#gs_gb_rt a:focus,#gs_gb_rt a:active{color:white;outline:none;}#gs_gb_ac{top:30px;left:auto;right:6px;width:288px;white-space:normal;}#gs_gb_aw,#gs_gb_ap,.gs_gb_am,#gs_gb_ab{display:block;padding:10px 20px;word-wrap:break-word;}#gs_gb_aw{background:#fef9db;font-size:11px;}#gs_gb_ap,.gs_gb_am{border-bottom:1px solid #ccc;}#gs_gb_aa:link,#gs_gb_aa:visited{float:right;margin-left:8px;color:#1a0dab;}#gs_gb_aa:active{color:#d14836}.gs_gb_am:link,.gs_gb_am:visited{color:#222;text-decoration:none;background:#fbfbfb;}.gs_gb_am:hover,.gs_gb_am:focus{background:#f1f1f1}.gs_gb_am:active{background:#eee}#gs_gb_ab{background:#fbfbfb;overflow:auto;}#gs_gb_aab{float:left}#gs_gb_aso{float:right}</style><div id="gs_gb" role="navigation"><div id="gs_gb_lt"><a href="//www.google.com/search?hl=en&amp;">Web</a><a href="//www.google.com/search?tbm=isch&amp;hl=en&amp;">Images</a><a href="//www.google.com/intl/en/options/">More&hellip;</a></div><a id="gs_gb_lp" aria-label="Web" href="//www.google.com/search?hl=en&"></a><div id="gs_gb_rt"><a href="https://accounts.google.com/Login?hl=en&amp;continue=http://scholar.google.com/scholar%3Fas_q%3D%26as_epq%3D%26as_oq%3D%26as_eq%3Dquantum%2520theory%26as_occt%3Dtitle%26as_sauthors%3Dalbert%2520einstein%26as_publication%3D%26as_ylo%3D1970%26as_yhi%3D%26as_sdt%3D0%252C5%26as_vis%3D0%26btnG%3D%26hl%3Den%26num%3D5">Sign in</a></div></div><!--[if lte IE 7]><div class="gs_alrt" style="padding:16px"><div>Sorry, some features may not work in this version of Internet Explorer.</div><div>Please use <a href="//www.google.com/chrome/">Google Chrome</a> or <a href="//www.mozilla.com/firefox/">Mozilla Firefox</a> for the best experience.</div></div><![endif]--><style>html,body{height:100%}#gs_top{min-height:100%}#gs_md_s,#gs_md_w{z-index:1200;position:absolute;top:0;left:0;width:100%;height:100%;}#gs_md_s{background:#666;filter:alpha(opacity=50);-ms-filter:"alpha(opacity=50)";opacity:.5;}.gs_md_d{position:relative;padding:28px 32px;margin:0 auto;width:400px;-moz-box-shadow:2px 2px 8px rgba(0,0,0,.65);-webkit-box-shadow:2px 2px 8px rgba(0,0,0,.65);box-shadow:2px 2px 8px rgba(0,0,0,.65);}.gs_el_ph .gs_md_d{padding:16px 20px;width:80%;max-width:400px;}.gs_md_d .gs_ico_X{position:absolute;top:8px;right:8px;background-color:#fff;}.gs_md_d h2{font-size:16px;font-weight:normal;line-height:24px;margin-bottom:16px;}.gs_el_ph .gs_md_d h2{margin-bottom:8px}.gs_md_lbl{margin:16px 0}.gs_md_btns{margin-top:16px}.gs_md_btns button{margin-right:16px}.gs_md_prg{margin:24px 0;}</style><script>function gs_md_opw(d,e,b){var r=document.documentElement,s=gs_id("gs_md_s").style,w=gs_id("gs_md_w").style,q=gs_id(d),g=q.style;g.visibility="hidden";s.display=w.display=g.display="block";g.top=Math.max(document.body.scrollTop||0,r.scrollTop||0)+Math.max((r.clientHeight-q.offsetHeight)/2,10)+"px";g.visibility="visible";gs_md_opn(d,e,function(){s.display="none"},function(){w.display="none"});if(b){b=gs_id(b);b.type==="text"?gs_tfcs(b):b.focus();}return false;}function gs_md_ldw(d,e,b,c,u,p,f){c=gs_id(c);c.innerHTML="<div class=\'gs_md_prg\'>Loading...</div>";gs_md_opw(d,e,b);gs_ajax(u,p,function(x,t){c.innerHTML=x===200?t:"<div class=\'gs_md_prg gs_alrt\'>The system can\\x27t perform the operation now. Try again later.</div>";f&&f(x,t);});}</script><div id="gs_md_s" style="display:none"></div><div id="gs_md_w" style="display:none"><div id="gs_cit" style="display:none" class="gs_md_d gs_md_wn gs_ttzi" role="dialog" aria-hidden="true" aria-labelledby="gs_cit-t"><a id="gs_cit-x" href="#" role="button" aria-label="Cancel" class="gs_ico gs_ico_X gs_ico_Xt" onclick="return gs_md_cls(\'gs_cit\',event)"></a><h2 id="gs_cit-t">Cite</h2><style>#gs_cit{width:520px;max-width:85%}.gs_el_ph #gs_cit{width:80%;max-width:520px}#gs_citt table{width:100%}#gs_citt td,#gs_citt th{vertical-align:top;padding:8px 0;}#gs_citt th{text-align:right;font-weight:normal;color:#777;padding-right:12px;white-space:nowrap;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;}#gs_citi{margin:16px 0 0 0;text-align:center;}.gs_citi{margin-right:12px;white-space:nowrap;padding:7px 0 5px 0;}#gs_citv,#gs_citf{display:none}</style><script>function gs_ocit(e,i,p){var s=gs_id("gs_cit").style,d=gs_id("gs_citd");s.height="370px";d.innerHTML="Loading...";gs_md_opw("gs_cit",e);gs_ajax(\'/scholar?q\\x3dinfo:{id}:scholar.google.com/\\x26output\\x3dcite\\x26scirp\\x3d{p}\\x26hl\\x3den\'.replace(\'{id}\',i).replace(\'{p}\',p),"",function(c,t){if(c!=200){d.innerHTML="The system can\\x27t perform the operation now. Try again later."}else{s.height="auto";d.innerHTML=t;gs_id("gs_cit0").focus();}});return false;}var gs_sdom=window.getSelection?function(i){getSelection().selectAllChildren(gs_id(i))}:function(i){try{var r=document.body.createTextRange();r.moveToElementText(gs_id(i));r.select();}catch(_){}};gs_evt_rdy(function(){var X;gs_evt_fcs(gs_id("gs_cit"),function(e){var x=gs_evt_tgt(e)||{},i=x.id||"";x!==X&&i.match(/^gs_cit[0-9]+$/)&&setTimeout(function(){gs_md_sif();gs_sdom(i);(X=x).focus();},0);});});</script><div id="gs_citd" aria-live="assertive"></div></div><script>gs_md_ifc("gs_cit","gs_cit-x");</script></div><div id="gs_hdr" role="banner"><div id="gs_hdr_bg"></div><div id="gs_hdr_lt"><div class="gs_ico gs_ico_ggl"><a href="/schhp?hl=en&amp;num=5&amp;as_sdt=0,5" aria-label="Scholar Home"></a></div><div id="gs_hdr_md"><form id="gs_hdr_frm" action="/scholar" name="f" role="search"><span id="gs_hdr_frm_in"><input type="text" class="gs_in_txt" name="q" value="allintitle: -quantum -theory author:albert author:einstein" id="gs_hdr_frm_in_txt" size="41" maxlength="2048" autocapitalize="off" aria-label="Search"><span id="gs_hdr_arw"><a id="gs_hdr_arr" class="gs_btnAD" href="#" aria-haspopup="true" aria-controls="gs_hdr_adv" aria-label="Advanced Scholar Search"><span class="gs_ico"></span><span class="gs_ttp"><span class="gs_aro"></span><span class="gs_aru"></span><span class="gs_txt">Advanced Scholar Search</span></span></a></span></span><button type="submit" id="gs_hdr_tsb" name="btnG" aria-label="Search" class="gs_btnG gs_in_ib gs_btn_act gs_btn_eml"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico"></span></span></button><input type=hidden name=hl value="en"><input type=hidden name=num value="5"><input type=hidden name=as_sdt value="0,5"><input type=hidden name=as_ylo value="1970"></form><style>#gs_hdr_adv{position:absolute;padding:9px;color:#777777;}#gs_hdr_advx{position:absolute;top:4px;right:2px;background-color:white;}.gs_hatr{clear:both;white-space:normal;}.gs_hadt{float:left;width:190px;padding:2px;padding-top:6px;}.gs_hadd{margin-left:194px;padding:2px;}.gs_el_tc .gs_hadt,.gs_el_ph .gs_hadt{float:none;width:auto;}.gs_el_tc .gs_hadd,.gs_el_ph .gs_hadd{margin-left:0;}#gs_hdr_adv .gs_yri .gs_in_txt{width:2.75em}#gs_hdr_arw{position:absolute;top:5px;right:2px;width:21px;height:21px;z-index:1100;background-color:#fff;}#gs_hdr_arr{display:block;text-decoration:none;width:21px;height:21px;}.gs_el_ph #gs_hdr_arr .gs_ttp{display:none}</style><div id="gs_hdr_adv" class="gs_md_wn gs_ttzi" style="display:none" role="dialog" aria-hidden="true" aria-label="Advanced Scholar Search"><a id="gs_hdr_advx" class="gs_ico gs_ico_X gs_ico_Xt" role="button" href="#"></a><form id="gs_hdr_frm_adv" action="/scholar"><div class="gs_hatr"><div class="gs_hadt"><b>Find articles</b></div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_q">with <b>all</b> of the words</label></div><div class="gs_hadd"><div class="gs_in_txtm"><input type="text" class="gs_in_txt gs_mini" name="as_q" value="" id="gs_asd_q" autocapitalize="off"></div></div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_epq">with the <b>exact phrase</b></label></div><div class="gs_hadd"><div class="gs_in_txtm"><input type="text" class="gs_in_txt gs_mini" name="as_epq" value="" id="gs_asd_epq" autocapitalize="off"></div></div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_oq">with <b>at least one</b> of the words</label></div><div class="gs_hadd"><div class="gs_in_txtm"><input type="text" class="gs_in_txt gs_mini" name="as_oq" value="" id="gs_asd_oq" autocapitalize="off"></div></div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_eq"><b>without</b> the words</label></div><div class="gs_hadd"><div class="gs_in_txtm"><input type="text" class="gs_in_txt gs_mini" name="as_eq" value="quantum theory" id="gs_asd_eq" autocapitalize="off"></div></div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_occt">where my words occur</label></div><div class="gs_hadd"><div style="position:relative"><input type="hidden" name="as_occt" id="gs_asd_occt" value="title"><button type="button" id="gs_asd_occt-bd" aria-controls="gs_asd_occt-md" aria-haspopup="true" class=" gs_in_se"><span class="gs_wr"><span class="gs_lbl" id="gs_asd_occt-ds">in the title of the article</span><span class="gs_icm"></span></span></button><div id="gs_asd_occt-md" class="gs_md_se" role="listbox" aria-hidden="true"><ul><li role="option" tabindex="-1" onclick="" data-v="any">anywhere in the article</li><li role="option" tabindex="-1" onclick="" data-v="title" id="gs_asd_occt-1" class="gs_sel" aria-selected="true">in the title of the article</li></ul></div><script>gs_evt_md_sel("gs_asd_occt-md","gs_asd_occt-bd","gs_asd_occt-ds","gs_asd_occt","gs_asd_occt-1");</script></div></div></div><div class="gs_hatr"><div style="height:16px"> </div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_sau">Return articles <b>authored</b> by</label></div><div class="gs_hadd"><div class="gs_in_txtm"><input type="text" class="gs_in_txt gs_mini" name="as_sauthors" value="albert einstein" id="gs_asd_sau" autocapitalize="off"></div><div>e.g., <i>"PJ Hayes"</i> or <i>McCarthy</i></div></div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_pub">Return articles <b>published</b> in</label></div><div class="gs_hadd"><div class="gs_in_txtm"><input type="text" class="gs_in_txt gs_mini" name="as_publication" value="" id="gs_asd_pub" autocapitalize="off"></div><div>e.g., <i>J Biol Chem</i> or <i>Nature</i></div></div></div><div class="gs_hatr"><div class="gs_hadt"><label for="gs_asd_ylo">Return articles <b>dated</b> between</label></div><div class="gs_hadd"><div class="gs_yri"><input type="text" class="gs_in_txt gs_mini" name="as_ylo" value="1970" id="gs_asd_ylo" size="4" maxlength="4" autocapitalize="off" pattern="[0-9]*">&nbsp;\xe2\x80\x94&nbsp;<input type="text" class="gs_in_txt gs_mini" name="as_yhi" value="" id="gs_asd_yhi" size="4" maxlength="4" autocapitalize="off" pattern="[0-9]*"></div><div>e.g., <i>1996</i></div></div></div><div class="gs_hatr"><div class="gs_hadt"><button type="submit" name="btnG" aria-label="Search" class="gs_btnG gs_in_ib gs_btn_act gs_btn_eml"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico"></span></span></button></div></div><input type=hidden name=hl value="en"><input type=hidden name=num value="5"><input type=hidden name=as_sdt value="0,5"></form></div><script>function gs_aso(e){var a=gs_id("gs_hdr_arr");a.style.display="none";gs_md_opn("gs_hdr_adv",e,function(){a.style.display=""});gs_tfcs(gs_id("gs_asd_q"));}gs_md_ifc("gs_hdr_adv","gs_hdr_advx");gs_evt_clk(gs_id("gs_hdr_advx"),gs_bind(gs_md_cls,"gs_hdr_adv"),1);gs_evt(gs_id("gs_hdr_frm_adv"),"keydown",function(e){var x=gs_evt_tgt(e)||{};e.keyCode===13&&x.nodeType===1&&x.tagName==="INPUT"&&x.form.submit();});gs_evt_clk(gs_id("gs_hdr_arr"),gs_aso,0,[13,32,38,40]);</script></div></div></div><div id="gs_ab" role="navigation"><a id="gs_ab_na" href="/schhp?hl=en&amp;num=5&amp;as_sdt=0,5">Scholar</a><div id="gs_ab_md">About 2,540 results (<b>0.05</b> sec)</div><div id="gs_ab_rt"><div id="gs_ylo_dd"><button class="gs_in_se gs_btn_mnu" id="gs_ylo_btn" type="button" aria-controls="gs_ylo_md" aria-haspopup="true"><span class="gs_wr"><span class="gs_lbl">Since 1970</span><span class="gs_icm"></span></span></button><div class="gs_md_wn" id="gs_ylo_md" style="display:none" role="menu" aria-hidden="true"><a href="/scholar?q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5" class="gs_md_li" role="menuitemradio" tabindex="-1">Any time</a><a href="/scholar?as_ylo=2015&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5" class="gs_md_li" role="menuitemradio" tabindex="-1">Since 2015</a><a href="/scholar?as_ylo=2014&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5" class="gs_md_li" role="menuitemradio" tabindex="-1">Since 2014</a><a href="/scholar?as_ylo=2011&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5" class="gs_md_li" role="menuitemradio" tabindex="-1">Since 2011</a><a href="/scholar?as_ylo=1970&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5" class="gs_md_li gs_cur" aria-checked="true" role="menuitemradio" tabindex="-1">Since 1970</a><div class="gs_hr" role="separator"></div><a href="/scholar?hl=en&amp;num=5&amp;as_sdt=0,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein" class="gs_md_li gs_cur" aria-checked="true" role="menuitemradio" tabindex="-1">Sort by relevance</a><a href="/scholar?hl=en&amp;num=5&amp;as_sdt=0,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;scisbd=1" class="gs_md_li" role="menuitemradio" tabindex="-1">Sort by date</a></div></div><script>gs_evt_md_mnu("gs_ylo_md","gs_ylo_btn")</script><button type="button" onclick="window.location=\'/citations?hl\\x3den\'" class="gs_btnC gs_in_ib"><span class="gs_wr"><span class="gs_lbl">My Citations</span><span class="gs_ico"></span></span></button><div id="gs_ad_dd"><button type="button" id="gs_btnAD" aria-label="More" aria-controls="gs_ad_md" aria-haspopup="true" class="gs_btnAD gs_in_ib gs_btn_half"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico"></span></span></button><div id="gs_ad_md" class="gs_md_wn" style="display:none" role="menu" aria-hidden="true"><div class="gs_ad_nlnv"><a href="/scholar?as_sdt=0,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_ylo=1970" class="gs_md_li gs_cur" aria-checked="true" role="menuitemradio" tabindex="-1">Articles</a><a href="/scholar?as_sdt=2006&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_ylo=1970" class="gs_md_li" role="menuitemradio" tabindex="-1">Case law</a><a href="/scholar?scilib=1&amp;scioq=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5" class="gs_md_li" role="menuitemradio" tabindex="-1">My library</a><div class="gs_hr" role="separator"></div><a href="/scholar?as_sdt=1,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_ylo=1970" role="menuitemcheckbox" tabindex="-1" aria-checked="true" class="gs_in_cb gs_sel gs_md_li"><span class="gs_lbl">include patents</span><span class="gs_chk"></span><span class="gs_cbx"></span></a><a href="/scholar?as_vis=1&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" role="menuitemcheckbox" tabindex="-1" aria-checked="true" class="gs_in_cb gs_sel gs_md_li"><span class="gs_lbl">include citations</span><span class="gs_chk"></span><span class="gs_cbx"></span></a><div class="gs_hr" role="separator"></div><a href="/citations?hl=en" role="menuitem" tabindex="-1" class="gs_btnC gs_in_ib gs_md_li"><span class="gs_lbl">My Citations</span><span class="gs_ico"></span></a><a href="/scholar_alerts?view_op=create_alert_options&amp;hl=en&amp;alert_query=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;alert_params=hl%3Den%26as_sdt%3D0,5" role="menuitem" tabindex="-1" class="gs_btnM gs_in_ib gs_md_li"><span class="gs_lbl">Create alert</span><span class="gs_ico"></span></a></div><a href="/citations?view_op=top_venues&amp;hl=en" role="menuitem" tabindex="-1" class="gs_btnJ gs_in_ib gs_md_li"><span class="gs_lbl">Metrics</span><span class="gs_ico"></span></a><a href="/scholar_settings?q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" role="menuitem" tabindex="-1" class="gs_btnP gs_in_ib gs_md_li"><span class="gs_lbl">Settings</span><span class="gs_ico"></span></a><a href="#" id="gs_a_adv" role="menuitem" tabindex="-1" class="gs_btnSB gs_in_ib gs_md_li"><span class="gs_lbl">Advanced search</span><span class="gs_ico"></span></a></div></div></div></div><script>gs_evt_md_mnu("gs_ad_md","gs_btnAD");gs_xatr(gs_id("gs_a_adv"),"data-a","gs_aso&&gs_aso({})");</script><div id="gs_bdy"><div id="gs_res_bdy"><div id="gs_lnv" role="navigation"><ul id="gs_lnv_pri"><li class="gs_sel"><a href="/scholar?as_sdt=0,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_ylo=1970">Articles</a></li><li><a href="/scholar?as_sdt=2006&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_ylo=1970">Case law</a></li><li><a href="/scholar?scilib=1&amp;scioq=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5">My library</a></li></ul><div class="gs_pad"><div class="gs_hr"></div></div><ul id="gs_lnv_ylo" class="gs_pad"><li class="gs_ind"><a href="/scholar?q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5">Any time</a></li><li class="gs_ind"><a href="/scholar?as_ylo=2015&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5">Since 2015</a></li><li class="gs_ind"><a href="/scholar?as_ylo=2014&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5">Since 2014</a></li><li class="gs_ind"><a href="/scholar?as_ylo=2011&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5">Since 2011</a></li><li class="gs_ind gs_sel"><a href="#" onclick="return gs_lnv_yloc_clk(this)">Custom range...</a></li></ul><script>function gs_lnv_yloc_clk(t){gs_visi(\'gs_lnv_yloc\',1);gs_is_tc||gs_tfcs(gs_id(\'gs_as_ylo\'));return gs_sel_clk("gs_lnv_ylo",t);}</script><form id="gs_lnv_yloc" class="gs_pad" action="/scholar"><input type=hidden name=q value="allintitle: -quantum -theory author:albert author:einstein"><input type=hidden name=hl value="en"><input type=hidden name=num value="5"><input type=hidden name=as_sdt value="0,5"><table><tr><td nowrap><input type="text" pattern="[0-9]*" name="as_ylo" class="gs_in_txt gs_mini" size="4" maxlength="4" value="1970" id="gs_as_ylo">&nbsp;\xe2\x80\x94&nbsp;<input type="text" pattern="[0-9]*" name="as_yhi" class="gs_in_txt gs_mini" size="4" maxlength="4" value=""></td></tr><tr><td align="center"><button type="submit" class=""><span class="gs_wr"><span class="gs_lbl">Search</span></span></button></td></tr></table></form><div class="gs_pad"><div class="gs_hr"></div></div><ul id="gs_lnv_stype" class="gs_pad"><li class="gs_ind gs_sel"><a href="/scholar?hl=en&amp;num=5&amp;as_sdt=0,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein">Sort by relevance</a></li><li class="gs_ind"><a href="/scholar?hl=en&amp;num=5&amp;as_sdt=0,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;scisbd=1">Sort by date</a></li></ul><div class="gs_pad"><div class="gs_hr"></div></div><ul id="gs_lnv_misc" class="gs_pad"><li class="gs_inw"><a href="/scholar?as_sdt=1,5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_ylo=1970" role="checkbox" aria-checked="true" class="gs_in_cb gs_sel"><span class="gs_lbl">include patents</span><span class="gs_chk"></span><span class="gs_cbx"></span></a></li><li class="gs_inw"><a href="/scholar?as_vis=1&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" role="checkbox" aria-checked="true" class="gs_in_cb gs_sel"><span class="gs_lbl">include citations</span><span class="gs_chk"></span><span class="gs_cbx"></span></a></li></ul><div class="gs_pad"><div class="gs_hr"></div><div><a href="/scholar_alerts?view_op=create_alert_options&amp;hl=en&amp;alert_query=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;alert_params=hl%3Den%26as_sdt%3D0,5" class="gs_btnM gs_in_ib"><span class="gs_lbl">Create alert</span><span class="gs_ico"></span></a></div></div></div><div id="gs_ccl" role="main">  <div class="gs_r"><h3 class="gs_rt"><a href="/citations?view_op=search_authors&amp;mauthors=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;oi=ao">User profiles for <b>allintitle: -quantum -theory author:albert author:einstein</b></a></h3><table cellspacing="0" cellpadding="2" border="0" style="max-width:49.5em"><tr><td style="padding-right:12px"><img src="/intl/en/scholar/feather-72.png" width="30" height="60"></td><td valign="top" style="padding-right:8px"><h4 class="gs_rt2"><a href="/citations?user=qc6CJjYAAAAJ&amp;hl=en&amp;oi=ao"><b>Albert Einstein</b></a></h4><div class="gs_nph">Institute of Advanced Studies, Princeton</div><div>Cited by 94846</div></td></tr></table></div>  <div class="gs_r"><div class="gs_ri"><h3 class="gs_rt"><span class="gs_ctc"><span class="gs_ct1">[BOOK]</span><span class="gs_ct2">[B]</span></span> <a href="http://books.google.com/books?hl=en&amp;lr=&amp;id=qszDAgAAQBAJ&amp;oi=fnd&amp;pg=PA1&amp;dq=+-quantum+-theory+albert+einstein&amp;ots=ZCTZ32bGGn&amp;sig=8w6uxwKNQ5zfPwaf6sXoYZdWCYY" data-clk="hl=en&amp;sa=T&amp;ct=res&amp;cd=0&amp;ei=3shNVuDRNcmlmAG20bX4Bw">The principle of relativity</a></h3><div class="gs_a"><a href="/citations?user=qc6CJjYAAAAJ&amp;hl=en&amp;oi=sra">A <b>Einstein</b></a>, FA Davis - 2013 - books.google.com</div><div class="gs_rs">Here are the 11 papers that forged the general and special theories of relativity: seven <br>papers by Einstein, plus two papers by Lorentz and one each by Minkowski and Weyl.&quot; A <br>thrill to read again the original papers by these giants.&quot;\xe2\x80\x94School Science and Mathematics ...</div><div class="gs_fl"><a href="/scholar?cites=10222925839632055980&amp;as_sdt=2005&amp;sciodt=0,5&amp;hl=en&amp;num=5">Cited by 1074</a> <a href="/scholar?q=related:rD5uROMg340J:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">Related articles</a> <a href="/scholar?cluster=10222925839632055980&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" class="gs_nph">All 5 versions</a> <a onclick="return gs_ocit(event,\'rD5uROMg340J\',\'0\')" href="#" class="gs_nph" role="button" aria-controls="gs_cit" aria-haspopup="true">Cite</a> <span class="gs_nph"><a id="gs_svl0" onclick="return gs_sva(\'rD5uROMg340J\',\'0\')" href="#" title="Save this article to my library so that I can read or cite it later.">Save</a><span id="gs_svo0" class="gs_svm">Saving<span id="gs_svd0">...</span></span><a id="gs_svs0" style="display:none">Saved</a><span id="gs_sve0" class="gs_svm">Error saving. <a onclick="return gs_sva(\'rD5uROMg340J\',\'0\')" href="#">Try again?</a></span></span> <a href="#" class="gs_mor" role="button" onclick="return gs_more(this,1)">More</a> <a href="/scholar?output=instlink&amp;q=info:rD5uROMg340J:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970&amp;scillfp=10689645761161196289&amp;oi=llo" class="gs_nvi">Library Search</a> <a href="#" class="gs_nvi" role="button" onclick="return gs_more(this,0)">Fewer</a></div></div></div>  <div class="gs_r"><div class="gs_ggs gs_fl"><button type="button" id="gs_ggsB1" class="gs_btnFI gs_in_ib gs_btn_half"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico"></span></span></button><div class="gs_md_wp gs_ttss" id="gs_ggsW1"><a href="http://static.schoolrack.com/files/7572/103399/Albert_Einstein_-_The_World_As_I_See_It.pdf" data-clk="hl=en&amp;sa=T&amp;oi=gga&amp;ct=gga&amp;cd=1&amp;ei=3shNVuDRNcmlmAG20bX4Bw"><span class="gs_ggsL"><span class=gs_ctg2>[PDF]</span> from schoolrack.com</span><span class="gs_ggsS">schoolrack.com <span class=gs_ctg2>[PDF]</span></span></a></div></div><div class="gs_ri"><h3 class="gs_rt"><span class="gs_ctc"><span class="gs_ct1">[BOOK]</span><span class="gs_ct2">[B]</span></span> <a href="http://books.google.com/books?hl=en&amp;lr=&amp;id=aNKOo94tO6cC&amp;oi=fnd&amp;pg=PR13&amp;dq=+-quantum+-theory+albert+einstein&amp;ots=QmYFmOJ_3o&amp;sig=brSBctPGG-fgk7PawPDgYsRfzks" data-clk="hl=en&amp;sa=T&amp;ct=res&amp;cd=1&amp;ei=3shNVuDRNcmlmAG20bX4Bw">The world as I see it</a></h3><div class="gs_a"><a href="/citations?user=qc6CJjYAAAAJ&amp;hl=en&amp;oi=sra">A <b>Einstein</b></a> - 2007 - books.google.com</div><div class="gs_rs">The most advanced and celebrated mind of the 20th Century, without a doubt, is attributed to <br>Albert Einstein. Instead of his hard science and advanced mathematical theories, which <br>often go far beyond the minds of average people, this book allows us to meet him as a  ...</div><div class="gs_fl"><a href="/scholar?cites=17183588468959488864&amp;as_sdt=2005&amp;sciodt=0,5&amp;hl=en&amp;num=5">Cited by 597</a> <a href="/scholar?q=related:YCvUgqteeO4J:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">Related articles</a> <a href="/scholar?cluster=17183588468959488864&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" class="gs_nph">All 142 versions</a> <a onclick="return gs_ocit(event,\'YCvUgqteeO4J\',\'1\')" href="#" class="gs_nph" role="button" aria-controls="gs_cit" aria-haspopup="true">Cite</a> <span class="gs_nph"><a id="gs_svl1" onclick="return gs_sva(\'YCvUgqteeO4J\',\'1\')" href="#" title="Save this article to my library so that I can read or cite it later.">Save</a><span id="gs_svo1" class="gs_svm">Saving<span id="gs_svd1">...</span></span><a id="gs_svs1" style="display:none">Saved</a><span id="gs_sve1" class="gs_svm">Error saving. <a onclick="return gs_sva(\'YCvUgqteeO4J\',\'1\')" href="#">Try again?</a></span></span> <a href="#" class="gs_mor" role="button" onclick="return gs_more(this,1)">More</a> <a href="/scholar?output=instlink&amp;q=info:YCvUgqteeO4J:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970&amp;scillfp=5360172429833922802&amp;oi=llo" class="gs_nvi">Library Search</a> <a href="#" class="gs_nvi" role="button" onclick="return gs_more(this,0)">Fewer</a></div></div></div>  <div class="gs_r"><div class="gs_ri"><h3 class="gs_rt"><span class="gs_ctc"><span class="gs_ct1">[BOOK]</span><span class="gs_ct2">[B]</span></span> <a href="http://books.google.com/books?hl=en&amp;lr=&amp;id=J-zv71syXJMC&amp;oi=fnd&amp;pg=PR11&amp;dq=+-quantum+-theory+albert+einstein&amp;ots=2Dd337pMD1&amp;sig=bz469m0LWY9EsQVXy3-3Igt18XI" data-clk="hl=en&amp;sa=T&amp;ct=res&amp;cd=2&amp;ei=3shNVuDRNcmlmAG20bX4Bw">The collected papers of Albert Einstein</a></h3><div class="gs_a"><a href="/citations?user=qc6CJjYAAAAJ&amp;hl=en&amp;oi=sra">A <b>Einstein</b></a>, A Beck, P Havas - 1989 - books.google.com</div><div class="gs_rs">Every document in The Collected Papers of Albert Einstein appears in the language in <br>which it was written, and this supplementary paperback volume presents the English <br>translations of all non-English materials. This translation does not include notes or  ...</div><div class="gs_fl"><a href="/scholar?cites=6706908336481689418&amp;as_sdt=2005&amp;sciodt=0,5&amp;hl=en&amp;num=5">Cited by 497</a> <a href="/scholar?q=related:St8Y6Zi5E10J:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">Related articles</a> <a href="/scholar?cluster=6706908336481689418&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" class="gs_nph">All 10 versions</a> <a onclick="return gs_ocit(event,\'St8Y6Zi5E10J\',\'2\')" href="#" class="gs_nph" role="button" aria-controls="gs_cit" aria-haspopup="true">Cite</a> <span class="gs_nph"><a id="gs_svl2" onclick="return gs_sva(\'St8Y6Zi5E10J\',\'2\')" href="#" title="Save this article to my library so that I can read or cite it later.">Save</a><span id="gs_svo2" class="gs_svm">Saving<span id="gs_svd2">...</span></span><a id="gs_svs2" style="display:none">Saved</a><span id="gs_sve2" class="gs_svm">Error saving. <a onclick="return gs_sva(\'St8Y6Zi5E10J\',\'2\')" href="#">Try again?</a></span></span> <a href="#" class="gs_mor" role="button" onclick="return gs_more(this,1)">More</a> <a href="/scholar?output=instlink&amp;q=info:St8Y6Zi5E10J:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970&amp;scillfp=12117491396839005222&amp;oi=llo" class="gs_nvi">Library Search</a> <a href="#" class="gs_nvi" role="button" onclick="return gs_more(this,0)">Fewer</a></div></div></div>  <div class="gs_r"><div class="gs_ggs gs_fl"><button type="button" id="gs_ggsB3" class="gs_btnFI gs_in_ib gs_btn_half"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico"></span></span></button><div class="gs_md_wp gs_ttss" id="gs_ggsW3"><a href="http://www.geocities.ws/astronet_2008/ondas_grav.pdf" data-clk="hl=en&amp;sa=T&amp;oi=gga&amp;ct=gga&amp;cd=3&amp;ei=3shNVuDRNcmlmAG20bX4Bw"><span class="gs_ggsL"><span class=gs_ctg2>[PDF]</span> from geocities.ws</span><span class="gs_ggsS">geocities.ws <span class=gs_ctg2>[PDF]</span></span></a></div></div><div class="gs_ri"><h3 class="gs_rt"><span class="gs_ctc"><span class="gs_ct1">[BOOK]</span><span class="gs_ct2">[B]</span></span> <a href="http://link.springer.com/chapter/10.1007/978-3-322-83770-7_13" data-clk="hl=en&amp;sa=T&amp;ct=res&amp;cd=3&amp;ei=3shNVuDRNcmlmAG20bX4Bw">On gravitational waves</a></h3><div class="gs_a"><a href="/citations?user=qc6CJjYAAAAJ&amp;hl=en&amp;oi=sra">A <b>Einstein</b></a> - 1990 - Springer</div><div class="gs_rs">Abstract The rigorous solution for cylindrical gravitational waves is given. For the <br>convenience of the reader the theory of gravitational waves and their production, already <br>known in principle, is given in the first part of this paper. After encountering relationships  ...</div><div class="gs_fl"><a href="/scholar?cites=17985207591311031889&amp;as_sdt=2005&amp;sciodt=0,5&amp;hl=en&amp;num=5">Cited by 439</a> <a href="/scholar?q=related:Ub7AuwNLmPkJ:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">Related articles</a> <a href="/scholar?cluster=17985207591311031889&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" class="gs_nph">All 6 versions</a> <a onclick="return gs_ocit(event,\'Ub7AuwNLmPkJ\',\'3\')" href="#" class="gs_nph" role="button" aria-controls="gs_cit" aria-haspopup="true">Cite</a> <span class="gs_nph"><a id="gs_svl3" onclick="return gs_sva(\'Ub7AuwNLmPkJ\',\'3\')" href="#" title="Save this article to my library so that I can read or cite it later.">Save</a><span id="gs_svo3" class="gs_svm">Saving<span id="gs_svd3">...</span></span><a id="gs_svs3" style="display:none">Saved</a><span id="gs_sve3" class="gs_svm">Error saving. <a onclick="return gs_sva(\'Ub7AuwNLmPkJ\',\'3\')" href="#">Try again?</a></span></span> <a href="#" class="gs_mor" role="button" onclick="return gs_more(this,1)">More</a> <a href="/scholar?output=instlink&amp;q=info:Ub7AuwNLmPkJ:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970&amp;scillfp=9251455342463616138&amp;oi=llo" class="gs_nvi">Library Search</a> <a href="#" class="gs_nvi" role="button" onclick="return gs_more(this,0)">Fewer</a></div></div></div>  <div class="gs_r"><div class="gs_ri"><h3 class="gs_rt"><span class="gs_ctc"><span class="gs_ct1">[BOOK]</span><span class="gs_ct2">[B]</span></span> <a href="http://books.google.com/books?hl=en&amp;lr=&amp;id=QuJQdu_fUqcC&amp;oi=fnd&amp;pg=PP1&amp;dq=+-quantum+-theory+albert+einstein&amp;ots=ZJlFU4jWWP&amp;sig=SErBjtyg6y9M9Kzr5eESf9oF_GQ" data-clk="hl=en&amp;sa=T&amp;ct=res&amp;cd=4&amp;ei=3shNVuDRNcmlmAG20bX4Bw">The Universe and Dr. Einstein</a></h3><div class="gs_a">L Barnett, A <b>Einstein</b> - 2005 - books.google.com</div><div class="gs_rs">In the century since the publication of the special theory of relativity, there remains a <br>tendency to venerate Einstein&#39;s genius without actually understanding his achievement. This <br>book offers the opportunity to truly comprehend the workings of one of humanity&#39;s greatest  ...</div><div class="gs_fl"><a href="/scholar?cites=15317244643960906689&amp;as_sdt=2005&amp;sciodt=0,5&amp;hl=en&amp;num=5">Cited by 413</a> <a href="/scholar?q=related:wWMLddnIkdQJ:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">Related articles</a> <a href="/scholar?cluster=15317244643960906689&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970" class="gs_nph">All 4 versions</a> <a onclick="return gs_ocit(event,\'wWMLddnIkdQJ\',\'4\')" href="#" class="gs_nph" role="button" aria-controls="gs_cit" aria-haspopup="true">Cite</a> <span class="gs_nph"><a id="gs_svl4" onclick="return gs_sva(\'wWMLddnIkdQJ\',\'4\')" href="#" title="Save this article to my library so that I can read or cite it later.">Save</a><span id="gs_svo4" class="gs_svm">Saving<span id="gs_svd4">...</span></span><a id="gs_svs4" style="display:none">Saved</a><span id="gs_sve4" class="gs_svm">Error saving. <a onclick="return gs_sva(\'wWMLddnIkdQJ\',\'4\')" href="#">Try again?</a></span></span> <a href="#" class="gs_mor" role="button" onclick="return gs_more(this,1)">More</a> <a href="/scholar?output=instlink&amp;q=info:wWMLddnIkdQJ:scholar.google.com/&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970&amp;scillfp=2364805099763271328&amp;oi=llo" class="gs_nvi">Library Search</a> <a href="#" class="gs_nvi" role="button" onclick="return gs_more(this,0)">Fewer</a></div></div></div><script>!function(){var i,b;for(i=0;i<5;i++){(b=gs_id("gs_ggsB"+i))&&gs_evt_clk(b,gs_bind(function(i,e){gs_md_sif();gs_md_opn("gs_ggsW"+i,e);},i),2);}}();</script><p class="gs_alrt_btm"><a href="/scholar_alerts?view_op=create_alert_options&amp;hl=en&amp;alert_query=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;alert_params=hl%3Den%26as_sdt%3D0,5" class="gs_btnM gs_in_ib"><span class="gs_lbl">Create alert</span><span class="gs_ico"></span></a></p><div id="gs_n" role="navigation"><center><table cellpadding="0" width="1%"><tr align="center" valign="top"><td align="right" nowrap><span class="gs_ico gs_ico_nav_first"></span><b style="display:block;margin-right:35px;visibility:hidden">Previous</b></td><td><span class="gs_ico gs_ico_nav_current"></span><b>1</b></td><td><a href="/scholar?start=5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>2</a></td><td><a href="/scholar?start=10&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>3</a></td><td><a href="/scholar?start=15&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>4</a></td><td><a href="/scholar?start=20&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>5</a></td><td><a href="/scholar?start=25&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>6</a></td><td><a href="/scholar?start=30&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>7</a></td><td><a href="/scholar?start=35&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>8</a></td><td><a href="/scholar?start=40&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>9</a></td><td><a href="/scholar?start=45&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_page"></span>10</a></td><td align="left" nowrap><a href="/scholar?start=5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970"><span class="gs_ico gs_ico_nav_next"></span><b style="display:block;margin-left:53px">Next</b></a></td></tr></table></center></div><div id="gs_nm" role="navigation"><button type="button" aria-label="Previous" disabled class="gs_btnPL gs_in_ib gs_btn_half gs_dis"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico gs_ico_dis"></span></span></button><button type="button" onclick="window.location=\'/scholar?start\\x3d5\\x26q\\x3dallintitle:+-quantum+-theory+author:albert+author:einstein\\x26hl\\x3den\\x26num\\x3d5\\x26as_sdt\\x3d0,5\\x26as_ylo\\x3d1970\'" aria-label="Next" class="gs_btnPR gs_in_ib gs_btn_half"><span class="gs_wr"><span class="gs_lbl"></span><span class="gs_ico"></span></span></button><div id="gs_nml"><b class="gs_nma">1</b><a class="gs_nma" href="/scholar?start=5&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">2</a><a class="gs_nma" href="/scholar?start=10&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">3</a><a class="gs_nma" href="/scholar?start=15&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">4</a><a class="gs_nma" href="/scholar?start=20&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">5</a><a class="gs_nma" href="/scholar?start=25&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">6</a><a class="gs_nma" href="/scholar?start=30&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">7</a><a class="gs_nma" href="/scholar?start=35&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">8</a><a class="gs_nma" href="/scholar?start=40&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">9</a><a class="gs_nma" href="/scholar?start=45&amp;q=allintitle:+-quantum+-theory+author:albert+author:einstein&amp;hl=en&amp;num=5&amp;as_sdt=0,5&amp;as_ylo=1970">10</a></div></div><div id="gs_ftr" role="contentinfo"><a href="/intl/en/scholar/about.html">About Google Scholar</a> <a href="//www.google.com/intl/en/policies/privacy/">Privacy</a> <a href="//www.google.com/intl/en/policies/terms/">Terms</a> <a href="//support.google.com/scholar/contact/general">Provide feedback</a></div></div></div></div></div><div id="gs_rdy"></div></body></html>'
    #querier.send_query(query)
    querier.send_query_html(query,html)

    if options.csv:
        csv(querier)
    elif options.csv_header:
        csv(querier, header=True)
    elif options.citation is not None:
        citation_export(querier)
    else:
        txt(querier, with_globals=options.txt_globals)

    if options.cookie_file:
        querier.save_cookies()

    return 0

if __name__ == "__main__":
    sys.exit(main())
