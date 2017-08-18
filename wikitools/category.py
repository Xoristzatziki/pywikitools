# -*- coding: utf-8 -*-
# Copyright 2008-2016 Alex Zaddach (mrzmanwiki@gmail.com)

# This file is part of wikitools.
# wikitools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# wikitools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with wikitools.  If not, see <http://www.gnu.org/licenses/>.

# Changes made by xoristzatziki

from . import api

class Category():
    def __enter__(self):
        print('entering Category')
        return self

    def __exit__(self, t, v, tb):
        print('Exiting Category...')
        return True

    """A category on the wiki"""
    def __init__(self, site, categorytitle, check=True, followRedir=True, section=None, sectionnumber=None, pageid=None):
        """
        site - A wiki object
        title - The page title, as a string or unicode object
        check - Checks for existence, normalizes title, required for most things
        followRedir - follow redirects (check must be true)
        section - the section name
        sectionnumber - the section number
        pageid - pageid, can be in place of title
        """
        #page.Page.__init__(self, site=site, title=title, check=check, followRedir=followRedir, section=section, sectionnumber=sectionnumber, pageid=pageid)
        self.info = {}
        self.site = site
        self.categorytitle = categorytitle
        print(self.categorytitle,'self.categorytitle')
        #if self.namespace != 14:
            #self.setNamespace(14, check)

    def getCategoryInfo(self, force=False):
        """Get some basic information about a category
        Returns a dict with:
        size - Total number of items in the category
        pages - Number of ordinary pages
        files - Number of files
        subcats - Number of subcategories
        """
        if self.info and not Force:
            return self.info
        params = {'action':'query',
            'prop':'categoryinfo',
            'titles':self.categorytitle
        }
        req = api.APIRequest(self.site, params)
        res = req.query(False)
        key = list(res['query']['pages'].keys())[0]
        self.info = res['query']['pages'][key]['categoryinfo']
        return self.info

    def getAllMembers(self, namespaces=None):
        """Gets a list of pages in the category

        namespaces - List of namespaces to restrict to
        """
        members = []
        print('getAllMembers start members',members)
        for member in self.__getMembersInternal(namespaces, self.site.limit):
            members.append(member)
        return members

    def getAllMembersGen(self, titleonly=False, reload=False, namespaces=None):
        """Generator function for pages in the category

        titleonly - set to True to yield strings,
        else it will yield Page objects
        reload - Deprecated, unused
        namespaces - List of namespaces to restrict to

        """
        for member in self.__getMembersInternal(namespaces, 50):
            if titleonly:
                yield member.title
            else:
                yield member

    def __getMembersInternal(self, namespaces, limit):
        if 'continue' not in self.site.features:
            raise exceptions.UnsupportedError("MediaWiki 1.21+ is required for this function")
        params = {'action':'query',
            'list':'categorymembers',
            'cmtitle':self.categorytitle,
            'cmlimit':limit,
            'cmprop':'title'
        }
        if namespaces is not None:
            params['cmnamespace'] = '|'.join([str(ns) for ns in namespaces])
        req = api.APIRequest(self.site, params)
        for data in req.queryGen():
            for item in data['query']['categorymembers']:
                yield item['title']

    def __getattr__(self, name):
        """Computed attributes:
        members
        """
        if name != 'members':
            return super().__getattr__(name)
        return self.getAllMembers()

