import os
import sys
import urllib
import urlparse

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

# Make sure library folder is on the path
addon = xbmcaddon.Addon()
sys.path.append(xbmc.translatePath(os.path.join(
    addon.getAddonInfo("path"), "lib")))

import libsonic_extra


class Plugin(object):
    """
    Plugin container.
    """

    def __init__(self, addon_url, addon_handle, addon_args):
        self.addon_url = addon_url
        self.addon_handle = addon_handle
        self.addon_args = addon_args

        # Retrieve plugin settings
        self.url = addon.getSetting("subsonic_url")
        self.username = addon.getSetting("username")
        self.password = addon.getSetting("password")

        self.albums_per_page = int(addon.getSetting("albums_per_page"))
        self.tracks_per_page = int(addon.getSetting("tracks_per_page"))
        
        self.bitrate = int(addon.getSetting("bitrate"))
        self.transcode_format = addon.getSetting("transcode_format")

        # Create connection
        self.connection = libsonic_extra.SubsonicClient(
            self.url, self.username, self.password)

    def build_url(self, query):
        """
        Create URL for page.
        """

        parts = list(urlparse.urlparse(self.addon_url))
        parts[4] = urllib.urlencode(query)

        return urlparse.urlunparse(parts)

    def route(self):
        """
        Map a Kodi request to certain action. This takes the `mode' query
        parameter and executed the function in this instance with that name.
        """

        mode = self.addon_args.get("mode", ["main_menu"])[0]

        if not mode.startswith("_"):
            getattr(self, mode)()

    def add_track(self, track, show_artist=False):
        """
        Display one track in the list.
        """

        url = self.connection.streamUrl(
            sid=track["id"], maxBitRate=self.bitrate,
            tformat=self.transcode_format)

        # Create list item
        if show_artist:
            title = "%s - %s" % (
                track.get("artist", "<Unknown>"),
                track.get("title", "<Unknown>"))
        else:
            title = track.get("title", "<Unknown>")

        # Create item
        li = xbmcgui.ListItem(title)

        # Handle cover art
        if "coverArt" in track:
            cover_art_url = self.connection.getCoverArtUrl(track["coverArt"])

            li.setIconImage(cover_art_url)
            li.setThumbnailImage(cover_art_url)
            li.setProperty("fanart_image", cover_art_url)

        # Handle metadata
        li.setProperty("IsPlayable", "true")
        li.setMimeType(track.get("contentType"))
        li.setInfo(type="Music", infoLabels={
            "Artist": track.get("artist"),
            "Title": track.get("title"),
            "Year": track.get("year"),
            "Duration": track.get("duration"),
            "Genre": track.get("genre"),
            "TrackNumber": track.get("track")})

        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle, url=url, listitem=li)

    def add_album(self, album, show_artist=False):
        """
        Display one album in the list.
        """

        url = self.build_url({
            "mode": "track_list",
            "album_id": album["id"]})

        # Create list item
        if show_artist:
            title = "%s - %s" % (
                album.get("artist", "<Unknown>"),
                album.get("name", "<Unknown>"))
        else:
            title = album.get("name", "<Unknown>")

        # Add year if applicable
        if album.get("year"):
            title = "%s [%d]" % (title, album.get("year"))

        # Create item
        li = xbmcgui.ListItem()
        li.setLabel(title)

        # Handle cover art
        if "coverArt" in album:
            cover_art_url = self.connection.getCoverArtUrl(album["coverArt"])

            li.setIconImage(cover_art_url)
            li.setThumbnailImage(cover_art_url)
            li.setProperty("fanart_image", cover_art_url)

        # Handle metadata
        li.setInfo(type="music", infoLabels={
            "Artist": album.get("artist"),
            "Album": album.get("name"),
            "Year": album.get("year")})

        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle, url=url, listitem=li, isFolder=True)

    def main_menu(self):
        """
        Display main menu.
        """

        menu = [
            {"mode": "list_artists", "foldername": "Artists"},
            {"mode": "menu_albums", "foldername": "Albums"},
            {"mode": "list_playlists", "foldername": "Playlists"},
            {"mode": "menu_tracks", "foldername": "Tracks"}
        ]

        for entry in menu:
            url = self.build_url(entry)

            li = xbmcgui.ListItem(entry["foldername"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)
        
    def menu_tracks(self):
        """
        Display main menu.
        """

        menu = [
            {"mode": "list_tracks_starred", "foldername": "Starred tracks"},
            {"mode": "list_tracks_random_genre", "foldername": "Random tracks by genre"},
            {"mode": "list_tracks_random_year", "foldername": "Random tracks by year"}
        ]

        for entry in menu:
            url = self.build_url(entry)

            li = xbmcgui.ListItem(entry["foldername"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)
            
    def menu_albums(self):
        """
        Display main menu.
        """

        menu = [
            {"mode": "list_albums_newest", "foldername": "Newest albums", "page":1},
            {"mode": "list_albums_frequent", "foldername": "Most played albums", "page":1},
            {"mode": "list_albums_recent", "foldername": "Recently played albums", "page":1},
            {"mode": "list_albums_genre", "foldername": "Albums by Genre"}
        ]

        for entry in menu:
            url = self.build_url(entry)

            li = xbmcgui.ListItem(entry["foldername"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)
        
    def menu_link(self):
        mode = self.addon_args["mode"][0]
        menu_item = {"mode": "main_menu", "foldername": "Back to Menu"}
        menu_item_url = self.build_url(menu_item)
        menu_item_li = xbmcgui.ListItem(menu_item["foldername"])
        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle, url=menu_item_url, listitem=menu_item_li, isFolder=True)

    def next_page_link(self,page):

        page += 1
        title = "Next page (%s)" % (page)
        
        mode = self.addon_args["mode"][0]
        
        menu_item = {"mode": mode, "foldername": title, "page":page}
        menu_item_url = self.build_url(menu_item)
        menu_item_li = xbmcgui.ListItem(menu_item["foldername"])
        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle, url=menu_item_url, listitem=menu_item_li, isFolder=True)

    def list_playlists(self):
        """
        Display playlists.
        """

        for playlist in self.connection.walk_playlists():
            cover_art_url = self.connection.getCoverArtUrl(
                playlist["coverArt"])
            url = self.build_url({
                "mode": "list_playlist_songs", "playlist_id": playlist["id"]})

            li = xbmcgui.ListItem(playlist["name"], iconImage=cover_art_url)
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)
        
    def list_playlist_songs(self):
        """
        Display playlist tracks.
        """

        playlist_id = self.addon_args["playlist_id"][0]

        xbmcplugin.setContent(self.addon_handle, "songs")

        for track in self.connection.walk_playlist(playlist_id):
            self.add_track(track, show_artist=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def list_albums_genre(self):
        """
        Display albums by genre list.
        """

        genres = self.connection.walk_genres()
        genres_sorted = sorted(genres, key=lambda k: k['value']) 

        for genre in genres_sorted:
            
            try:
            
                genre_slug = genre["value"]
                genre_name = genre_slug.replace(';',' / ')
                genre_count = int(genre["albumCount"])
                
                if genre_count == 0:
                    continue
                
                
                genre_name += ' (' + str(genre_count) + ')'

                url = self.build_url({
                    "mode": 'album_list_genre',
                    "foldername": genre_slug.encode("utf-8")})

                li = xbmcgui.ListItem(genre_name)
                xbmcplugin.addDirectoryItem(
                    handle=self.addon_handle, url=url, listitem=li, isFolder=True)
                
            except:
                pass
            
                

        xbmcplugin.endOfDirectory(self.addon_handle)
        
    def list_albums_newest(self):
        """
        Display newest album list.
        """

        page = int(self.addon_args["page"][0])
        size = self.albums_per_page
        offset = size * ( page -1 )

        xbmcplugin.setContent(self.addon_handle, "albums")

        for album in self.connection.walk_albums(ltype='newest',size=size,offset=offset):
            self.add_album(album, show_artist=True)
            
        self.next_page_link(page)
        self.menu_link()

        xbmcplugin.endOfDirectory(self.addon_handle)

    def list_albums_frequent(self):
        """
        Display most played albums list.
        """
        
        page = int(self.addon_args["page"][0])
        size = self.albums_per_page
        offset = size * ( page -1 )

        xbmcplugin.setContent(self.addon_handle, "albums")

        for album in self.connection.walk_albums(ltype='frequent',size=size,offset=offset):
            self.add_album(album, show_artist=True)
            
        self.next_page_link(page)
        self.menu_link()

        xbmcplugin.endOfDirectory(self.addon_handle)
        
    def list_albums_recent(self):
        """
        Display recently played album list.
        """
        
        page = int(self.addon_args["page"][0])
        size = self.albums_per_page
        offset = size * ( page -1 )

        xbmcplugin.setContent(self.addon_handle, "albums")

        for album in self.connection.walk_albums(ltype='recent',size=size):
            self.add_album(album, show_artist=True)
            
        self.next_page_link(page)
        self.menu_link()

        xbmcplugin.endOfDirectory(self.addon_handle)
        

    def album_list_genre(self):
        """
        Display album list by genre menu.
        """
        
        genre = self.addon_args["foldername"][0].decode("utf-8")
        size = self.albums_per_page

        xbmcplugin.setContent(self.addon_handle, "albums")

        for album in self.connection.walk_albums(ltype='byGenre',size=size,genre=genre):
            self.add_album(album, show_artist=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def list_artists(self):
        """
        Display artist list
        """

        xbmcplugin.setContent(self.addon_handle, "artists")

        for artist in self.connection.walk_artists():
            cover_art_url = self.connection.getCoverArtUrl(artist["id"])
            url = self.build_url({
                "mode": "album_list",
                "artist_id": artist["id"]})

            li = xbmcgui.ListItem(artist["name"])
            li.setIconImage(cover_art_url)
            li.setThumbnailImage(cover_art_url)
            li.setProperty("fanart_image", cover_art_url)
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def album_list(self):
        """
        Display list of albums for certain artist.
        """

        artist_id = self.addon_args["artist_id"][0]

        xbmcplugin.setContent(self.addon_handle, "albums")

        for album in self.connection.walk_artist(artist_id):
            self.add_album(album)

        xbmcplugin.addSortMethod(
            self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(
            self.addon_handle, xbmcplugin.SORT_METHOD_ALBUM)
        xbmcplugin.addSortMethod(
            self.addon_handle, xbmcplugin.SORT_METHOD_ARTIST)
        xbmcplugin.addSortMethod(
            self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def track_list(self):
        """
        Display track list.
        """

        album_id = self.addon_args["album_id"][0]

        xbmcplugin.setContent(self.addon_handle, "songs")

        for track in self.connection.walk_album(album_id):
            self.add_track(track)

        xbmcplugin.endOfDirectory(self.addon_handle)


    def list_tracks_starred(self):
        """
        Display starred songs.
        """

        xbmcplugin.setContent(self.addon_handle, "songs")

        for starred in self.connection.walk_tracks_starred():
            self.add_track(starred, show_artist=True)

        xbmcplugin.endOfDirectory(self.addon_handle)
        
    def list_tracks_random_genre(self):
        """
        Display random genre list.
        """

        for genre in self.connection.walk_genres():
            url = self.build_url({
                "mode": "random_by_genre_track_list",
                "foldername": genre["value"].encode("utf-8")})

            li = xbmcgui.ListItem(genre["value"])
            xbmcplugin.addDirectoryItem(
                handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def random_by_genre_track_list(self):
        """
        Display random tracks by genre
        """

        genre = self.addon_args["foldername"][0].decode("utf-8")

        xbmcplugin.setContent(self.addon_handle, "songs")

        for track in self.connection.walk_tracks_random(
                size=self.tracks_per_page, genre=genre):
            self.add_track(track, show_artist=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def list_tracks_random_year(self):
        """
        Display random tracks by year.
        """

        from_year = xbmcgui.Dialog().input(
            "From year", type=xbmcgui.INPUT_NUMERIC)
        to_year = xbmcgui.Dialog().input(
            "To year", type=xbmcgui.INPUT_NUMERIC)

        xbmcplugin.setContent(self.addon_handle, "songs")

        for track in self.connection.walk_tracks_random(
                size=self.tracks_per_page, from_year=from_year, to_year=to_year):
            self.add_track(track, show_artist=True)

        xbmcplugin.endOfDirectory(self.addon_handle)


def main():
    """
    Entry point for this plugin. Instantiates a new plugin object and runs the
    action that is given.
    """

    addon_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    addon_args = urlparse.parse_qs(sys.argv[2][1:])

    # Route request to action.
    Plugin(addon_url, addon_handle, addon_args).route()

# Start plugin from within Kodi.
if __name__ == "__main__":
    main()
