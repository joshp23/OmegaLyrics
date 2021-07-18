#
# Omega Lyrics: a Quod Libet plugin for viewing lyrics.
# Version: 0.0.4
#
# Copyright 2008, 2011, 2012 Vasiliy Faronov <vfaronov@gmail.com>
#           2013-17 Nick Boultbee
#           2014 Christoph Reiter
#           2015 Joschua Gandert
#           2020 Josh Panter <joshu@unfettered.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk

from quodlibet import _, print_d, app
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins.gui import UserInterfacePlugin
from quodlibet.qltk import Icons, add_css, Button
from quodlibet.qltk.information import Information
from quodlibet.util.songwrapper import SongWrapper

from urllib import request, error
from urllib.parse import quote
import ssl
import socket
import json

# TODO: GTK config to set alternative url
#base_url = ("http://localhost:8080")
base_url = ("https://api.lyrics.ovh")
full_url = base_url + ("/v1/%s/%s")

def create_api_fetch_url(song):
    artist, title = song("artist"), song("title")
    artist = quote(artist.encode('utf-8'))
    title = quote(title.encode('utf-8'))
    return full_url % (artist, title)
  
class OmegaLyrics(EventPlugin, UserInterfacePlugin):
    """A plugin for viewing lyrics in the main window."""

    PLUGIN_ID = 'Omega Lyrics'
    PLUGIN_NAME = _('Omega Lyrics')
    PLUGIN_DESC = _('Automatically displays tag or file-based lyrics, '
                    'or lyrics from the web in a sidebar.')
    PLUGIN_ICON = Icons.FORMAT_JUSTIFY_FILL
    
    def enabled(self):
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                        Gtk.PolicyType.AUTOMATIC)
        self.adjustment = self.scrolled_window.get_vadjustment()

        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self._italics = self.textbuffer.create_tag("italic", style="italic",
                                                   foreground="grey")
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_justification(Gtk.Justification.LEFT)
        self.textview.connect('key-press-event', self.key_press_event_cb)
        add_css(self.textview, "* { padding: 6px; }")
        vbox = Gtk.VBox()
        vbox.pack_start(self.textview, True, True, 0)
        self._edit_button = Button("Edit Lyrics", Icons.EDIT)
        hbox = Gtk.HBox()
        hbox.pack_end(self._edit_button, False, False, 3)
        vbox.pack_start(hbox, False, False, 3)
        self.scrolled_window.add(vbox)
        self.textview.show()

        self.scrolled_window.show()
        self._sig = None
        cur = app.player.info
        if cur is not None:
            cur = SongWrapper(cur)
        self.plugin_on_song_started(cur)

    def create_sidebar(self):
        vbox = Gtk.VBox(margin=0)
        vbox.pack_start(self.scrolled_window, True, True, 0)
        vbox.show_all()
        return vbox

    def disabled(self):
        self.textview.destroy()
        self.scrolled_window.destroy()

    def plugin_on_song_started(self, song):
        """Called when a song is started. Loads the lyrics.

        If there are lyrics associated with `song`, load them into the
        lyrics viewer. Otherwise, hides the lyrics viewer.
        """
        lyrics = None
        if song is not None:
            print_d("Looking for lyrics for %s" % song("~filename"))
            lyrics = song("~lyrics")
            if lyrics:
                self.textbuffer.set_text(lyrics)
                self.adjustment.set_value(0)    # Scroll to the top.
                self.textview.show()
            else:
                fetch_url = create_api_fetch_url(song)
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    conn = request.urlopen(fetch_url, timeout=4, context=ctx).read()
                except error.HTTPError or error.URLError as e:
                    title = _("No lyrics found for:\n%s") % song("artist") + ' - ' + song("title")
                    self._set_italicised(title)
                except socket.timeout as e:
                    title = _("Timed out searching for:\n%s") % song("artist") + ' - ' + song("title")
                    self._set_italicised(title)
                else:
                    obj = json.loads(conn)
                    lyrics = obj["lyrics"] 
                    if lyrics.find("\n\n\n\n") != -1: # Clean up poorly formated lyrics
                        lyrics = lyrics.replace("\n\n", "\n").replace("\n\n\n\n", "\n\n")
                    self.textbuffer.set_text(lyrics)
                    self.adjustment.set_value(0)    # Scroll to the top.
                    self.textview.show()
            def edit(widget):
                print_d("Launching lyrics editor for %s" % song("~filename"))
                assert isinstance(song, SongWrapper)
                information = Information(app.librarian, [song._song])
                information.get_child()._switch_to_lyrics()
                information.show()

            if self._sig:
                self._edit_button.disconnect(self._sig)
            self._sig = self._edit_button.connect('clicked', edit)

    def _set_italicised(self, title):
        self.textbuffer.set_text(title)
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        self.textbuffer.remove_all_tags(start, end)
        self.textbuffer.apply_tag(self._italics, start, end)

    def plugin_on_changed(self, songs):
        cur = app.player.info
        if cur:
            fn = cur("~filename")
            for s in songs:
                if s("~filename") == fn:
                    print_d("Active song changed, reloading lyrics")
                    self.plugin_on_song_started(SongWrapper(cur))
        else:
            self._set_italicised(_("No active song"))

    def key_press_event_cb(self, widget, event):
        """Handles up/down "key-press-event" in the lyrics view."""
        adj = self.scrolled_window.get_vadjustment().props
        if event.keyval == Gdk.KEY_Up:
            adj.value = max(adj.value - adj.step_increment, adj.lower)
        elif event.keyval == Gdk.KEY_Down:
            adj.value = min(adj.value + adj.step_increment,
                            adj.upper - adj.page_size)
        elif event.keyval == Gdk.KEY_Page_Up:
            adj.value = max(adj.value - adj.page_increment, adj.lower)
        elif event.keyval == Gdk.KEY_Page_Down:
            adj.value = min(adj.value + adj.page_increment,
                            adj.upper - adj.page_size)
        elif event.keyval == Gdk.KEY_Home:
            adj.value = adj.lower
        elif event.keyval == Gdk.KEY_End:
            adj.value = adj.upper - adj.page_size
        else:
            return False
        return True

