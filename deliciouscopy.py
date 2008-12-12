#!/usr/bin/env python
#
# Copyright (C) 2006-2008 Michael G. Noll <http://www.michael-noll.com/>
# Copyright (C) 2008 Mark A. Matienzo <http://matienzo.org>
# 
# deliciouscopy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# deliciouscopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with deliciouscopy.  If not, see <http://www.gnu.org/licenses/>.

import md5
import os
import sys
from time import sleep, strftime
import feedparser
import pydelicious
from simplejson import loads as json_load
import settings

class DeliciousCopy(object):
    """Class to copy inbox items to public bookmarks, checking for if the poster
    is in the account's network.
    
    Based upon Michael Noll's deliciousmonitor.py:
    http://www.michael-noll.com/wiki/Del.icio.us_Python_API#deliciousmonitor.py
    """
    def __init__(self, username, password, key, logfile, verbose=False):
        self.inbox = pydelicious.dlcs_feed('user_inbox', format='rss',
                        username=username, key=key)
        self.api = pydelicious.DeliciousAPI(username, password)
        self.posters = json_load(pydelicious.json_network(username))
        self.logfile = logfile
        self.verbose = verbose
            
    def check(self):
        """Check inbox for new items."""
        
        logfh = None
        
        if os.access(self.logfile, os.F_OK):
            if self.verbose:
                print "[LOG] Log file found. Trying to resume...",
            try:
                # read in previous log data for resuming
                logfh = open(self.logfile, 'r')
                # remove leading and trailing whitespace if any (incl. newlines)
                self.urls = [line.strip() for line in logfh.readlines()]
                logfh.close()
                if self.verbose:
                    print "done"
            except IOError:
                # most probably, the log file does not exist (yet)
                if self.verbose:
                    print "failed"
        else:
            # log file does not exist, so there isn't any resume data
            # to read in
            pass

        try:
            if self.verbose:
                print "[LOG] Open log file for appending...",
            logfh = open(self.logfile, 'a')
            if self.verbose:
                print "done"
        except IOError:
            if self.verbose:
                print "failed"
            print "[LOG] ERROR: could not open log file for appending"
            self._cleanup()
            return
        
        # query metadata about each entry from delicious.com
        for index, entry in enumerate(self.inbox.entries):
            url = entry.link
            urlmd5 = md5.new(url).hexdigest()
            if entry.author in self.posters:
                if self.verbose:
                    logfh.write("[LOG] %s Processing entry #%s: '%s'\n" % \
                        (strftime("%Y-%m-%d %H:%M:%S"), index + 1, url))
                try:
                    sleep(1) # be nice and wait 1 sec between connects 
                    urlinfo = json_load(pydelicious.dlcs_feed('urlinfo',
                                urlmd5=urlmd5))
                    if urlinfo:
                        urlinfo = urlinfo[0]
                    else:
                        urlinfo = {}
                    title = urlinfo['title']
                    top_tags = urlinfo['top_tags'] or []
                    tagstr = 'via:%s ' % entry.author + \
                        ' '.join([tag.replace(' ','_') for tag in top_tags]) 
                    self.api.posts_add(url, title, tags=tagstr.strip())
                    if self.verbose:
                        logfh.write("[LOG] %s Saved %s\n" % \
                            (strftime("%Y-%m-%d %H:%M:%S"), url))
                except KeyError:
                    pass
                except pydelicious.DeliciousItemExistsError:
                    if self.verbose:
                        logfh.write("[LOG] %s %s already added\n" % \
                            (strftime("%Y-%m-%d %H:%M:%S"), url))
                except:
                    logfh.write("[LOG] %s ERROR: %s\n" % \
                        (strftime("%Y-%m-%d %H:%M:%S"), sys.exc_info()[0]))
                    # clean up
                    logfh.close()
                    raise
            else:
                logfh.write("[LOG] ERROR: %s not authorized, not saving %s\n" %\
                    (entry.author, url))
        # clean up
        logfh.close()

if __name__ == "__main__":
    dc = DeliciousCopy(username=settings.USERNAME, password=settings.PASSWORD,
                        key=settings.KEY, logfile=settings.LOGFILE)
    dc.check()