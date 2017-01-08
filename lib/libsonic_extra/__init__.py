import urllib
import urlparse
import libsonic

def force_list(value):
    """
    Coerce the input value to a list.

    If `value` is `None`, return an empty list. If it is a single value, create
    a new list with that element on index 0.

    :param value: Input value to coerce.
    :return: Value as list.
    :rtype: list
    """

    if value is None:
        return []
    elif type(value) == list:
        return value
    else:
        return [value]


class SubsonicClient(libsonic.Connection):
    """
    Extend `libsonic.Connection` with new features and fix a few issues.

    - Parse URL for host and port for constructor.
    - Make sure API results are of of uniform type.
    - Provide methods to intercept URL of binary requests.
    - Add order property to playlist items.
    - Add conventient `walk_*' methods to iterate over the API responses.
    """

    def __init__(self, url, username, password, apiversion, insecure, legacyauth):
        """
        Construct a new SubsonicClient.

        :param str url: Full URL (including scheme) of the Subsonic server.
        :param str username: Username of the server.
        :param str password: Password of the server.
        """

        self.intercept_url = False

        # Parse Subsonic URL
        parts = urlparse.urlparse(url)
        scheme = parts.scheme or "http"

        # Make sure there is hostname
        if not parts.hostname:
            raise ValueError("Expected hostname for URL: %s" % url)

        # Validate scheme
        if scheme not in ("http", "https"):
            raise ValueError("Unexpected scheme '%s' for URL: %s" % (
                scheme, url))

        # Pick a default port
        host = "%s://%s" % (scheme, parts.hostname)
        port = parts.port or {"http": 80, "https": 443}[scheme]

        # Invoke original constructor
        super(SubsonicClient, self).__init__(
            host, username, password, port=port, appName='Kodi', apiVersion=apiversion, insecure=insecure, legacyAuth=legacyauth)

    def getIndexes(self, *args, **kwargs):
        """
        Improve the getIndexes method. Ensures IDs are integers.
        """

        def _artists_iterator(artists):
            for artist in force_list(artists):
                artist["id"] = int(artist["id"])
                yield artist

        def _index_iterator(index):
            for index in force_list(index):
                index["artist"] = list(_artists_iterator(index.get("artist")))
                yield index

        def _children_iterator(children):
            for child in force_list(children):
                child["id"] = int(child["id"])

                if "parent" in child:
                    child["parent"] = int(child["parent"])
                if "coverArt" in child:
                    child["coverArt"] = int(child["coverArt"])
                if "artistId" in child:
                    child["artistId"] = int(child["artistId"])
                if "albumId" in child:
                    child["albumId"] = int(child["albumId"])

                yield child

        response = super(SubsonicClient, self).getIndexes(*args, **kwargs)
        response["indexes"] = response.get("indexes", {})
        response["indexes"]["index"] = list(
            _index_iterator(response["indexes"].get("index")))
        response["indexes"]["child"] = list(
            _children_iterator(response["indexes"].get("child")))

        return response

    def getPlaylists(self, *args, **kwargs):
        """
        Improve the getPlaylists method. Ensures IDs are integers.
        """

        def _playlists_iterator(playlists):
            for playlist in force_list(playlists):
                playlist["id"] = int(playlist["id"])
                yield playlist

        response = super(SubsonicClient, self).getPlaylists(*args, **kwargs)
        response["playlists"]["playlist"] = list(
            _playlists_iterator(response["playlists"].get("playlist")))

        return response

    def getPlaylist(self, *args, **kwargs):
        """
        Improve the getPlaylist method. Ensures IDs are integers and add an
        order property to each entry.
        """

        def _entries_iterator(entries):
            for order, entry in enumerate(force_list(entries), start=1):
                entry["id"] = int(entry["id"])
                entry["order"] = order
                yield entry

        response = super(SubsonicClient, self).getPlaylist(*args, **kwargs)
        response["playlist"]["entry"] = list(
            _entries_iterator(response["playlist"].get("entry")))

        return response

    def getArtists(self, *args, **kwargs):
        """
        Improve the getArtists method. Ensures IDs are integers.
        """

        def _artists_iterator(artists):
            for artist in force_list(artists):
                artist["id"] = int(artist["id"])
                yield artist

        def _index_iterator(index):
            for index in force_list(index):
                index["artist"] = list(_artists_iterator(index.get("artist")))
                yield index

        response = super(SubsonicClient, self).getArtists(*args, **kwargs)
        response["artists"] = response.get("artists", {})
        response["artists"]["index"] = list(
            _index_iterator(response["artists"].get("index")))

        return response

    def getArtist(self, *args, **kwargs):
        """
        Improve the getArtist method. Ensures IDs are integers.
        """

        def _albums_iterator(albums):
            for album in force_list(albums):
                album["id"] = int(album["id"])

                if "artistId" in album:
                    album["artistId"] = int(album["artistId"])

                yield album

        response = super(SubsonicClient, self).getArtist(*args, **kwargs)
        response["artist"]["album"] = list(
            _albums_iterator(response["artist"].get("album")))

        return response

    def getMusicDirectory(self, *args, **kwargs):
        """
        Improve the getMusicDirectory method. Ensures IDs are integers.
        """

        def _children_iterator(children):
            for child in force_list(children):
                child["id"] = int(child["id"])

                if "parent" in child:
                    child["parent"] = int(child["parent"])
                if "coverArt" in child:
                    child["coverArt"] = int(child["coverArt"])
                if "artistId" in child:
                    child["artistId"] = int(child["artistId"])
                if "albumId" in child:
                    child["albumId"] = int(child["albumId"])

                yield child

        response = super(SubsonicClient, self).getMusicDirectory(
            *args, **kwargs)
        response["directory"]["child"] = list(
            _children_iterator(response["directory"].get("child")))

        return response

    def getAlbum(self, *args, **kwargs):
        """
        Improve the getAlbum method. Ensures the IDs are real integers.
        """

        def _songs_iterator(songs):
            for song in force_list(songs):
                song["id"] = int(song["id"])
                yield song

        response = super(SubsonicClient, self).getAlbum(*args, **kwargs)
        response["album"]["song"] = list(
            _songs_iterator(response["album"].get("song")))

        return response

    def getAlbumList2(self, *args, **kwargs):
        """
        Improve the getAlbumList2 method. Ensures the IDs are real integers.
        """

        def _album_iterator(albums):
            for album in force_list(albums):
                album["id"] = int(album["id"])
                yield album

        response = super(SubsonicClient, self).getAlbumList2(*args, **kwargs)
        response["albumList2"]["album"] = list(
            _album_iterator(response["albumList2"].get("album")))

        return response

    def getStarred(self, *args, **kwargs):
        """
        Improve the getStarred method. Ensures the IDs are real integers.
        """

        def _song_iterator(songs):
            for song in force_list(songs):
                song["id"] = int(song["id"])
                yield song

        response = super(SubsonicClient, self).getStarred(*args, **kwargs)
        response["starred"]["song"] = list(
            _song_iterator(response["starred"].get("song")))

        return response

    def getCoverArtUrl(self, *args, **kwargs):
        """
        Return an URL to the cover art.
        """

        self.intercept_url = True
        url = self.getCoverArt(*args, **kwargs)
        self.intercept_url = False

        return url

    def streamUrl(self, *args, **kwargs):
        """
        Return an URL to the file to stream.
        """

        self.intercept_url = True
        url = self.stream(*args, **kwargs)
        self.intercept_url = False

        return url

    def _doBinReq(self, *args, **kwargs):
        """
        Intercept request URL to provide the URL of the item that is requested.

        If the URL is intercepted, the request is not executed. A username and
        password is added to provide direct access to the stream.
        """

        if self.intercept_url:
            parts = list(urlparse.urlparse(
                args[0].get_full_url() + "?" + args[0].data))
            parts[4] = dict(urlparse.parse_qsl(parts[4]))
            parts[4].update({"u": self.username, "p": self.password})
            parts[4] = urllib.urlencode(parts[4])

            return urlparse.urlunparse(parts)
        else:
            return super(SubsonicClient, self)._doBinReq(*args, **kwargs)

    def walk_index(self, folder_id=None):
        """
        Request Subsonic's index and iterate each item.
        """

        response = self.getIndexes(folder_id)

        for index in response["indexes"]["index"]:
            for index in index["artist"]:
                for item in self.walk_directory(index["id"]):
                    yield item

        for child in response["indexes"]["child"]:
            if child.get("isDir"):
                for child in self.walk_directory(child["id"]):
                    yield child
            else:
                yield child

    def walk_playlists(self):
        """
        Request Subsonic's playlists and iterate over each item.
        """

        response = self.getPlaylists()

        for child in response["playlists"]["playlist"]:
            yield child

    def walk_playlist(self, playlist_id):
        """
        Request Subsonic's playlist items and iterate over each item.
        """

        response = self.getPlaylist(playlist_id)

        for child in response["playlist"]["entry"]:
            yield child
            
    def walk_folders(self):
        response = self.getMusicFolders()
        
        for child in response["musicFolders"]["musicFolder"]:
            yield child

    def walk_directory(self, directory_id):
        """
        Request a Subsonic music directory and iterate over each item.
        """

        response = self.getMusicDirectory(directory_id)

        for child in response["directory"]["child"]:
            if child.get("isDir"):
                for child in self.walk_directory(child["id"]):
                    yield child
            else:
                yield child

    def walk_artist(self, artist_id):
        """
        Request a Subsonic artist and iterate over each album.
        """

        response = self.getArtist(artist_id)

        for child in response["artist"]["album"]:
            yield child

    def walk_artists(self):
        """
        Request all artists and iterate over each item.
        """

        response = self.getArtists()

        for index in response["artists"]["index"]:
            for artist in index["artist"]:
                yield artist

    def walk_genres(self):
        """
        Request all genres and iterate over each item.
        """

        response = self.getGenres()

        for genre in response["genres"]["genre"]:
            yield genre

    def walk_albums(self, ltype, size=None, fromYear=None,toYear=None, genre=None, offset=None):
        """
        Request all albums for a given genre and iterate over each album.
        """
        
        if ltype == 'byGenre' and genre is None:
            return
        
        if ltype == 'byYear' and (fromYear is None or toYear is None):
            return

        response = self.getAlbumList2(
            ltype=ltype, size=size, fromYear=fromYear, toYear=toYear,genre=genre, offset=offset)

        if not response["albumList2"]["album"]:
            return

        for album in response["albumList2"]["album"]:
            yield album


    def walk_album(self, album_id):
        """
        Request an alum and iterate over each item.
        """

        response = self.getAlbum(album_id)

        for song in response["album"]["song"]:
            yield song

    def walk_tracks_random(self, size=None, genre=None, fromYear=None,toYear=None):
        """
        Request random songs by genre and/or year and iterate over each song.
        """

        response = self.getRandomSongs(
            size=size, genre=genre, fromYear=fromYear, toYear=toYear)

        for song in response["randomSongs"]["song"]:
            yield song
            

    def walk_tracks_starred(self):
        """
        Request Subsonic's starred songs and iterate over each item.
        """

        response = self.getStarred()

        for song in response["starred"]["song"]:
            yield song
