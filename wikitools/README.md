branched from Alex Zaddach's wikitools
wikitools -- Package for working with MediaWiki wikis

Requirements
------------

  * Python 3.3+. Tested on 3.5.1
  * Basic functionality should be possible in wikis as old as 1.13, but at least
    MediaWiki 1.21 is recommended.

Installation
------------

Available modules
-----------------

  * api - Contains the APIRequest class, for doing queries directly,
    see API examples below
  * wiki - Contains the Wiki class, used for logging in to the site,
    storing cookies, and storing basic site information
  * page -  Contains the Page class for dealing with individual pages
    on the wiki. Can be used to get page info and text, as well as edit and
    other actions if enabled on the wiki
  * wikifile - File is a subclass of Page with extra functions for
    working with files - note that there may be some issues with shared
    repositories, as the pages for files on shared repos technically don't
    exist on the local wiki.
  * user - Contains the User class for getting information about and
    blocking/unblocking users

Further documentation
---------------------
  * https://github.com/alexz-enwp/wikitools/wiki

Current limitations
-------------------

  * Can only do what the API can do. On a site without the edit-API enabled
    (disabled by default prior to MediaWiki 1.14), you cannot edit/delete/
    protect pages, only retrieve information about them.
  * Usage on restricted-access (logged-out users can't read) wikis is
    mostly untested

Quick start
-----------

To make a simple query:

```python
#!/usr/bin/python

from wikitools import wiki
from wikitools import api

# create a Wiki object
site = wiki.Wiki("http://my.wikisite.org/w/api.php")
# login - required for read-restricted wikis
site.login("username", "password")
# define the params for the query
params = {'action':'query', 'titles':'Main Page'}
# create the request object
request = api.APIRequest(site, params)
# query the API
result = request.query()
```

The result will look something like:

```json
{u'query':
	{u'pages':
		{u'15580374':
			{u'ns': 0, u'pageid': 15580374, u'title': u'Main Page'}
		}
	}
}
```

See the MediaWiki API documentation at <http://www.mediawiki.org/wiki/API>
for more information about using the MediaWiki API. You can get an example of
what query results will look like by doing the queries in your web browser using
the "jsonfm" format option

Licensed under the GNU General Public License, version 3. A copy of the
license is included with this release.

Authors
-------

* Original source code Alex Z. (User:Mr.Z-man @ en.wikipedia) <mrzmanwiki@gmail.com>
* Some code/assistance (User:Bjweeks @ en.wikipedia)
