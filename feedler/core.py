#
# core.py
#
# Copyright (C) 2009 Josh <josh@kaiju.net>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

from deluge.log import LOG as log
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
import feedparser
import hashlib
import anydbm
import re
from twisted.internet.task import LoopingCall

DEFAULT_PREFS = {
    "poll_interval": 60,
    "feeds": []
}

class Core(CorePluginBase):
    def enable(self):

        self.config = deluge.configmanager.ConfigManager("feedler.conf", DEFAULT_PREFS)
        self.history = anydbm.open(deluge.configmanager.get_config_dir() + '/feedler.history', 'c')

        self.timers = []

        for feed in self.config['feeds']:
            timer = LoopingCall(self.fetch_feed, (feed))

            if 'poll_interval' in feed:
                interval = feed['poll_interval']
            else:
                interval = self.config['poll_interval']

            timer.start(interval)
            self.timers.append(timer)

    def disable(self):
        self.config.save()
        for timer in self.timers:
            timer.stop()
        self.history.close()

        pass

    def update(self):
        pass


    def fetch_feed(self, feed):
        log.debug("Fetching %s" % feed['source'])
        rss = feedparser.parse(feed['source'])

        if rss.bozo is 1:
            log.error("Problem fetching feed %s" % feed['source'])
            pass

        for entry in rss.entries:

            groups = []
            matches = 0

            for rule in feed['rules']:
                match = re.search(rule[1], entry[rule[0]])
                if match:
                    groups.extend(list(match.groups()))
                    matches += 1

            if matches == len(feed['rules']):
                hash = hashlib.md5(entry.title + entry.published + rss.href).hexdigest()
                if hash not in self.history.keys():
                    log.debug("Found %s torrent!! Adding to history as %s..." % (entry.title, hash))

                    target_directory = feed['target_directory']

                    for marker in re.findall('\$\d', feed['target_directory']):
                        index = int(marker.lstrip('$'))
                        if len(groups) >= index:
                            replacement = groups[index]
                        else:
                            replacement = ''
                        target_directory = target_directory.replace(marker, replacement)

                    # todo, stuff torrent status in here and check it
                    self.history[hash] = entry.title

                    component.get("Core").add_torrent_url(entry.link, { 'move_completed': True, 'move_completed_path': target_directory })

        pass


    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config
