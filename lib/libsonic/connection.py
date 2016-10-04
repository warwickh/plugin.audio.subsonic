"""
This file is part of py-sonic.

py-sonic is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

py-sonic is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with py-sonic.  If not, see <http://www.gnu.org/licenses/>
"""

from urllib import urlencode
from .errors import *
from pprint import pprint
from cStringIO import StringIO
from netrc import netrc
from hashlib import md5
import json, urllib2, httplib, logging, socket, ssl, sys, os

API_VERSION = '1.14.0'

logger = logging.getLogger(__name__)

class HTTPSConnectionChain(httplib.HTTPSConnection):
    _preferred_ssl_protos = sorted([ p for p in dir(ssl)
        if p.startswith('PROTOCOL_') ], reverse=True)
    _ssl_working_proto = None

    def _create_sock(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        return sock

    def connect(self):
        if self._ssl_working_proto is not None:
            # If we have a working proto, let's use that straight away
            logger.debug("Using known working proto: '%s'",
                         self._ssl_working_proto)
            sock = self._create_sock()
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                ssl_version=self._ssl_working_proto)
            return

        # Try connecting via the different SSL protos in preference order
        for proto_name in self._preferred_ssl_protos:
            sock = self._create_sock()
            proto = getattr(ssl, proto_name, None)
            try:
                self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                    ssl_version=proto)
            except:
                sock.close()
            else:
                # Cache the working ssl version
                HTTPSConnectionChain._ssl_working_proto = proto
                break


class HTTPSHandlerChain(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnectionChain, req)

# install opener
urllib2.install_opener(urllib2.build_opener(HTTPSHandlerChain()))

class PysHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    """
    This class is used to override the default behavior of the
    HTTPRedirectHandler, which does *not* redirect POST data
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        m = req.get_method()
        if (code in (301, 302, 303, 307) and m in ("GET", "HEAD")
            or code in (301, 302, 303) and m == "POST"):
            newurl = newurl.replace(' ', '%20')
            newheaders = dict((k, v) for k, v in req.headers.items()
                if k.lower() not in ("content-length", "content-type")
            )
            data = None
            if req.has_data():
                data = req.get_data()
            return urllib2.Request(newurl,
                           data=data,
                           headers=newheaders,
                           origin_req_host=req.get_origin_req_host(),
                           unverifiable=True)
        else:
            raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)

class Connection(object):
    def __init__(self, baseUrl, username=None, password=None, port=4040,
            serverPath='/rest', appName='py-sonic', apiVersion=API_VERSION,
            insecure=False, useNetrc=None, legacyAuth=False, useGET=False):
        """
        This will create a connection to your subsonic server

        baseUrl:str         The base url for your server. Be sure to use
                            "https" for SSL connections.  If you are using
                            a port other than the default 4040, be sure to
                            specify that with the port argument.  Do *not*
                            append it here.

                            ex: http://subsonic.example.com

                            If you are running subsonic under a different
                            path, specify that with the "serverPath" arg,
                            *not* here.  For example, if your subsonic
                            lives at:

                            https://mydomain.com:8080/path/to/subsonic/rest

                            You would set the following:

                            baseUrl = "https://mydomain.com"
                            port = 8080
                            serverPath = "/path/to/subsonic/rest"
        username:str        The username to use for the connection.  This
                            can be None if `useNetrc' is True (and you
                            have a valid entry in your netrc file)
        password:str        The password to use for the connection.  This
                            can be None if `useNetrc' is True (and you
                            have a valid entry in your netrc file)
        port:int            The port number to connect on.  The default for
                            unencrypted subsonic connections is 4040
        serverPath:str      The base resource path for the subsonic views.
                            This is useful if you have your subsonic server
                            behind a proxy and the path that you are proxying
                            is different from the default of '/rest'.
                            Ex:
                                serverPath='/path/to/subs'

                              The full url that would be built then would be
                              (assuming defaults and using "example.com" and
                              you are using the "ping" view):

                                http://example.com:4040/path/to/subs/ping.view
        appName:str         The name of your application.
        apiVersion:str      The API version you wish to use for your
                            application.  Subsonic will throw an error if you
                            try to use/send an api version higher than what
                            the server supports.  See the Subsonic API docs
                            to find the Subsonic version -> API version table.
                            This is useful if you are connecting to an older
                            version of Subsonic.
        insecure:bool       This will allow you to use self signed
                            certificates when connecting if set to True.
        useNetrc:str|bool   You can either specify a specific netrc
                            formatted file or True to use your default
                            netrc file ($HOME/.netrc).
        legacyAuth:bool     Use pre-1.13.0 API version authentication
        useGET:bool         Use a GET request instead of the default POST
                            request.  This is not recommended as request
                            URLs can get very long with some API calls
        """
        self._baseUrl = baseUrl
        self._hostname = baseUrl.split('://')[1].strip()
        self._username = username
        self._rawPass = password
        self._legacyAuth = legacyAuth
        self._useGET = useGET

        self._netrc = None
        if useNetrc is not None:
            self._process_netrc(useNetrc)
        elif username is None or password is None:
            raise CredentialError('You must specify either a username/password '
                'combination or "useNetrc" must be either True or a string '
                'representing a path to a netrc file')

        self._port = int(port)
        self._apiVersion = apiVersion
        self._appName = appName
        self._serverPath = serverPath.strip('/')
        self._insecure = insecure
        self._opener = self._getOpener(self._username, self._rawPass)

    # Properties
    def setBaseUrl(self, url):
        self._baseUrl = url
        self._opener = self._getOpener(self._username, self._rawPass)
    baseUrl = property(lambda s: s._baseUrl, setBaseUrl)

    def setPort(self, port):
        self._port = int(port)
    port = property(lambda s: s._port, setPort)

    def setUsername(self, username):
        self._username = username
        self._opener = self._getOpener(self._username, self._rawPass)
    username = property(lambda s: s._username, setUsername)

    def setPassword(self, password):
        self._rawPass = password
        # Redo the opener with the new creds
        self._opener = self._getOpener(self._username, self._rawPass)
    password = property(lambda s: s._rawPass, setPassword)

    apiVersion = property(lambda s: s._apiVersion)

    def setAppName(self, appName):
        self._appName = appName
    appName = property(lambda s: s._appName, setAppName)

    def setServerPath(self, path):
        self._serverPath = path.strip('/')
    serverPath = property(lambda s: s._serverPath, setServerPath)

    def setInsecure(self, insecure):
        self._insecure = insecure
    insecure = property(lambda s: s._insecure, setInsecure)

    def setLegacyAuth(self, lauth):
        self._legacyAuth = lauth
    legacyAuth = property(lambda s: s._legacyAuth, setLegacyAuth)

    def setGET(self, get):
        self._useGET = get
    useGET = property(lambda s: s._useGET, setGET)

    # API methods
    def ping(self):
        """
        since: 1.0.0

        Returns a boolean True if the server is alive, False otherwise
        """
        methodName = 'ping'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        try:
            res = self._doInfoReq(req)
        except:
            return False
        if res['status'] == 'ok':
            return True
        elif res['status'] == 'failed':
            exc = getExcByCode(res['error']['code'])
            raise exc(res['error']['message'])
        return False

    def getLicense(self):
        """
        since: 1.0.0

        Gets details related to the software license

        Returns a dict like the following:

        {u'license': {u'date': u'2010-05-21T11:14:39',
                      u'email': u'email@example.com',
                      u'key': u'12345678901234567890123456789012',
                      u'valid': True},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getLicense'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getMusicFolders(self):
        """
        since: 1.0.0

        Returns all configured music folders

        Returns a dict like the following:

        {u'musicFolders': {u'musicFolder': [{u'id': 0, u'name': u'folder1'},
                                    {u'id': 1, u'name': u'folder2'},
                                    {u'id': 2, u'name': u'folder3'}]},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getMusicFolders'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getNowPlaying(self):
        """
        since: 1.0.0

        Returns what is currently being played by all users

        Returns a dict like the following:

        {u'nowPlaying': {u'entry': {u'album': u"Jazz 'Round Midnight 12",
                            u'artist': u'Astrud Gilberto',
                            u'bitRate': 172,
                            u'contentType': u'audio/mpeg',
                            u'coverArt': u'98349284',
                            u'duration': 325,
                            u'genre': u'Jazz',
                            u'id': u'2424324',
                            u'isDir': False,
                            u'isVideo': False,
                            u'minutesAgo': 0,
                            u'parent': u'542352',
                            u'path': u"Astrud Gilberto/Jazz 'Round Midnight 12/01 - The Girl From Ipanema.mp3",
                            u'playerId': 1,
                            u'size': 7004089,
                            u'suffix': u'mp3',
                            u'title': u'The Girl From Ipanema',
                            u'track': 1,
                            u'username': u'user1',
                            u'year': 1996}},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getNowPlaying'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getIndexes(self, musicFolderId=None, ifModifiedSince=0):
        """
        since: 1.0.0

        Returns an indexed structure of all artists

        musicFolderId:int       If this is specified, it will only return
                                artists for the given folder ID from
                                the getMusicFolders call
        ifModifiedSince:int     If specified, return a result if the artist
                                collection has changed since the given 
                                unix timestamp

        Returns a dict like the following:

        {u'indexes': {u'index': [{u'artist': [{u'id': u'29834728934',
                                       u'name': u'A Perfect Circle'},
                                      {u'id': u'238472893',
                                       u'name': u'A Small Good Thing'},
                                      {u'id': u'9327842983',
                                       u'name': u'A Tribe Called Quest'},
                                      {u'id': u'29348729874',
                                       u'name': u'A-Teens, The'},
                                      {u'id': u'298472938',
                                       u'name': u'ABA STRUCTURE'}],
                      u'lastModified': 1303318347000L},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getIndexes'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'musicFolderId': musicFolderId,
            'ifModifiedSince': self._ts2milli(ifModifiedSince)})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        self._fixLastModified(res)
        return res

    def getMusicDirectory(self, mid):
        """
        since: 1.0.0

        Returns a listing of all files in a music directory.  Typically used
        to get a list of albums for an artist or list of songs for an album.

        mid:str     The string ID value which uniquely identifies the
                    folder.  Obtained via calls to getIndexes or
                    getMusicDirectory.  REQUIRED

        Returns a dict like the following:

        {u'directory': {u'child': [{u'artist': u'A Tribe Called Quest',
                            u'coverArt': u'223484',
                            u'id': u'329084',
                            u'isDir': True,
                            u'parent': u'234823940',
                            u'title': u'Beats, Rhymes And Life'},
                           {u'artist': u'A Tribe Called Quest',
                            u'coverArt': u'234823794',
                            u'id': u'238472893',
                            u'isDir': True,
                            u'parent': u'2308472938',
                            u'title': u'Midnight Marauders'},
                           {u'artist': u'A Tribe Called Quest',
                            u'coverArt': u'39284792374',
                            u'id': u'983274892',
                            u'isDir': True,
                            u'parent': u'9823749',
                            u'title': u"People's Instinctive Travels And The Paths Of Rhythm"},
                           {u'artist': u'A Tribe Called Quest',
                            u'coverArt': u'289347293',
                            u'id': u'3894723934',
                            u'isDir': True,
                            u'parent': u'9832942',
                            u'title': u'The Anthology'},
                           {u'artist': u'A Tribe Called Quest',
                            u'coverArt': u'923847923',
                            u'id': u'29834729',
                            u'isDir': True,
                            u'parent': u'2934872893',
                            u'title': u'The Love Movement'},
                           {u'artist': u'A Tribe Called Quest',
                            u'coverArt': u'9238742893',
                            u'id': u'238947293',
                            u'isDir': True,
                            u'parent': u'9432878492',
                            u'title': u'The Low End Theory'}],
                u'id': u'329847293',
                u'name': u'A Tribe Called Quest'},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getMusicDirectory'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName, {'id': mid})
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def search(self, artist=None, album=None, title=None, any=None,
            count=20, offset=0, newerThan=None):
        """
        since: 1.0.0

        DEPRECATED SINCE API 1.4.0!  USE search2() INSTEAD!

        Returns a listing of files matching the given search criteria.
        Supports paging with offset

        artist:str      Search for artist
        album:str       Search for album
        title:str       Search for title of song
        any:str         Search all fields
        count:int       Max number of results to return [default: 20]
        offset:int      Search result offset.  For paging [default: 0]
        newerThan:int   Return matches newer than this timestamp
        """
        if artist == album == title == any == None:
            raise ArgumentError('Invalid search.  You must supply search '
                'criteria')
        methodName = 'search'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'artist': artist, 'album': album,
            'title': title, 'any': any, 'count': count, 'offset': offset,
            'newerThan': self._ts2milli(newerThan)})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def search2(self, query, artistCount=20, artistOffset=0, albumCount=20,
            albumOffset=0, songCount=20, songOffset=0, musicFolderId=None):
        """
        since: 1.4.0

        Returns albums, artists and songs matching the given search criteria.
        Supports paging through the result.

        query:str           The search query
        artistCount:int     Max number of artists to return [default: 20]
        artistOffset:int    Search offset for artists (for paging) [default: 0]
        albumCount:int      Max number of albums to return [default: 20]
        albumOffset:int     Search offset for albums (for paging) [default: 0]
        songCount:int       Max number of songs to return [default: 20]
        songOffset:int      Search offset for songs (for paging) [default: 0]
        musicFolderId:int   Only return results from the music folder
                            with the given ID. See getMusicFolders

        Returns a dict like the following:

        {u'searchResult2': {u'album': [{u'artist': u'A Tribe Called Quest',
                                u'coverArt': u'289347',
                                u'id': u'32487298',
                                u'isDir': True,
                                u'parent': u'98374289',
                                u'title': u'The Love Movement'}],
                    u'artist': [{u'id': u'2947839',
                                 u'name': u'A Tribe Called Quest'},
                                {u'id': u'239847239',
                                 u'name': u'Tribe'}],
                    u'song': [{u'album': u'Beats, Rhymes And Life',
                               u'artist': u'A Tribe Called Quest',
                               u'bitRate': 224,
                               u'contentType': u'audio/mpeg',
                               u'coverArt': u'329847',
                               u'duration': 148,
                               u'genre': u'default',
                               u'id': u'3928472893',
                               u'isDir': False,
                               u'isVideo': False,
                               u'parent': u'23984728394',
                               u'path': u'A Tribe Called Quest/Beats, Rhymes And Life/A Tribe Called Quest - Beats, Rhymes And Life - 03 - Motivators.mp3',
                               u'size': 4171913,
                               u'suffix': u'mp3',
                               u'title': u'Motivators',
                               u'track': 3}]},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'search2'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'query': query, 'artistCount': artistCount,
            'artistOffset': artistOffset, 'albumCount': albumCount,
            'albumOffset': albumOffset, 'songCount': songCount,
            'songOffset': songOffset, 'musicFolderId': musicFolderId})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def search3(self, query, artistCount=20, artistOffset=0, albumCount=20,
            albumOffset=0, songCount=20, songOffset=0, musicFolderId=None):
        """
        since: 1.8.0

        Works the same way as search2, but uses ID3 tags for
        organization

        query:str           The search query
        artistCount:int     Max number of artists to return [default: 20]
        artistOffset:int    Search offset for artists (for paging) [default: 0]
        albumCount:int      Max number of albums to return [default: 20]
        albumOffset:int     Search offset for albums (for paging) [default: 0]
        songCount:int       Max number of songs to return [default: 20]
        songOffset:int      Search offset for songs (for paging) [default: 0]
        musicFolderId:int   Only return results from the music folder
                            with the given ID. See getMusicFolders

        Returns a dict like the following (search for "Tune Yards":
            {u'searchResult3': {u'album': [{u'artist': u'Tune-Yards',
                                u'artistId': 1,
                                u'coverArt': u'al-7',
                                u'created': u'2012-01-30T12:35:33',
                                u'duration': 3229,
                                u'id': 7,
                                u'name': u'Bird-Brains',
                                u'songCount': 13},
                               {u'artist': u'Tune-Yards',
                                u'artistId': 1,
                                u'coverArt': u'al-8',
                                u'created': u'2011-03-22T15:08:00',
                                u'duration': 2531,
                                u'id': 8,
                                u'name': u'W H O K I L L',
                                u'songCount': 10}],
                    u'artist': {u'albumCount': 2,
                                u'coverArt': u'ar-1',
                                u'id': 1,
                                u'name': u'Tune-Yards'},
                    u'song': [{u'album': u'Bird-Brains',
                               u'albumId': 7,
                               u'artist': u'Tune-Yards',
                               u'artistId': 1,
                               u'bitRate': 160,
                               u'contentType': u'audio/mpeg',
                               u'coverArt': 105,
                               u'created': u'2012-01-30T12:35:33',
                               u'duration': 328,
                               u'genre': u'Lo-Fi',
                               u'id': 107,
                               u'isDir': False,
                               u'isVideo': False,
                               u'parent': 105,
                               u'path': u'Tune Yards/Bird-Brains/10-tune-yards-fiya.mp3',
                               u'size': 6588498,
                               u'suffix': u'mp3',
                               u'title': u'Fiya',
                               u'track': 10,
                               u'type': u'music',
                               u'year': 2009}]},

             u'status': u'ok',
             u'version': u'1.5.0',
             u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'search3'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'query': query, 'artistCount': artistCount,
            'artistOffset': artistOffset, 'albumCount': albumCount,
            'albumOffset': albumOffset, 'songCount': songCount,
            'songOffset': songOffset, 'musicFolderId': musicFolderId})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getPlaylists(self, username=None):
        """
        since: 1.0.0

        Returns the ID and name of all saved playlists
        The "username" option was added in 1.8.0.

        username:str        If specified, return playlists for this user
                            rather than for the authenticated user.  The
                            authenticated user must have admin role
                            if this parameter is used

        Returns a dict like the following:

        {u'playlists': {u'playlist': [{u'id': u'62656174732e6d3375',
                               u'name': u'beats'},
                              {u'id': u'766172696574792e6d3375',
                               u'name': u'variety'}]},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getPlaylists'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'username': username})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getPlaylist(self, pid):
        """
        since: 1.0.0

        Returns a listing of files in a saved playlist

        id:str      The ID of the playlist as returned in getPlaylists()

        Returns a dict like the following:

        {u'playlist': {u'entry': {u'album': u'The Essential Bob Dylan',
                          u'artist': u'Bob Dylan',
                          u'bitRate': 32,
                          u'contentType': u'audio/mpeg',
                          u'coverArt': u'2983478293',
                          u'duration': 984,
                          u'genre': u'Classic Rock',
                          u'id': u'982739428',
                          u'isDir': False,
                          u'isVideo': False,
                          u'parent': u'98327428974',
                          u'path': u"Bob Dylan/Essential Bob Dylan Disc 1/Bob Dylan - The Essential Bob Dylan - 03 - The Times They Are A-Changin'.mp3",
                          u'size': 3921899,
                          u'suffix': u'mp3',
                          u'title': u"The Times They Are A-Changin'",
                          u'track': 3},
               u'id': u'44796c616e2e6d3375',
               u'name': u'Dylan'},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getPlaylist'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName, {'id': pid})
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def createPlaylist(self, playlistId=None, name=None, songIds=[]):
        """
        since: 1.2.0

        Creates OR updates a playlist.  If updating the list, the
        playlistId is required.  If creating a list, the name is required.

        playlistId:str      The ID of the playlist to UPDATE
        name:str            The name of the playlist to CREATE
        songIds:list        The list of songIds to populate the list with in
                            either create or update mode.  Note that this
                            list will replace the existing list if updating

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'createPlaylist'
        viewName = '%s.view' % methodName

        if playlistId == name == None:
            raise ArgumentError('You must supply either a playlistId or a name')
        if playlistId is not None and name is not None:
            raise ArgumentError('You can only supply either a playlistId '
                 'OR a name, not both')

        q = self._getQueryDict({'playlistId': playlistId, 'name': name})

        req = self._getRequestWithList(viewName, 'songId', songIds, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def deletePlaylist(self, pid):
        """
        since: 1.2.0

        Deletes a saved playlist

        pid:str     ID of the playlist to delete, as obtained by getPlaylists

        Returns a dict like the following:

        """
        methodName = 'deletePlaylist'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName, {'id': pid})
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def download(self, sid):
        """
        since: 1.0.0

        Downloads a given music file.

        sid:str     The ID of the music file to download.

        Returns the file-like object for reading or raises an exception
        on error
        """
        methodName = 'download'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName, {'id': sid})
        res = self._doBinReq(req)
        if isinstance(res, dict):
            self._checkStatus(res)
        return res

    def stream(self, sid, maxBitRate=0, tformat=None, timeOffset=None,
            size=None, estimateContentLength=False, converted=False):
        """
        since: 1.0.0

        Downloads a given music file.

        sid:str         The ID of the music file to download.
        maxBitRate:int  (since: 1.2.0) If specified, the server will
                        attempt to limit the bitrate to this value, in
                        kilobits per second. If set to zero (default), no limit
                        is imposed. Legal values are: 0, 32, 40, 48, 56, 64,
                        80, 96, 112, 128, 160, 192, 224, 256 and 320.
        tformat:str     (since: 1.6.0) Specifies the target format
                        (e.g. "mp3" or "flv") in case there are multiple
                        applicable transcodings (since: 1.9.0) You can use
                        the special value "raw" to disable transcoding
        timeOffset:int  (since: 1.6.0) Only applicable to video
                        streaming.  Start the stream at the given
                        offset (in seconds) into the video
        size:str        (since: 1.6.0) The requested video size in
                        WxH, for instance 640x480
        estimateContentLength:bool  (since: 1.8.0) If set to True,
                                    the HTTP Content-Length header
                                    will be set to an estimated
                                    value for trancoded media
        converted:bool  (since: 1.14.0) Only applicable to video streaming.
                        Subsonic can optimize videos for streaming by
                        converting them to MP4. If a conversion exists for
                        the video in question, then setting this parameter
                        to "true" will cause the converted video to be
                        returned instead of the original.

        Returns the file-like object for reading or raises an exception
        on error
        """
        methodName = 'stream'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': sid, 'maxBitRate': maxBitRate,
            'format': tformat, 'timeOffset': timeOffset, 'size': size,
            'estimateContentLength': estimateContentLength,
            'converted': converted})

        req = self._getRequest(viewName, q)
        res = self._doBinReq(req)
        if isinstance(res, dict):
            self._checkStatus(res)
        return res

    def getCoverArt(self, aid, size=None):
        """
        since: 1.0.0

        Returns a cover art image

        aid:str     ID string for the cover art image to download
        size:int    If specified, scale image to this size

        Returns the file-like object for reading or raises an exception
        on error
        """
        methodName = 'getCoverArt'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': aid, 'size': size})

        req = self._getRequest(viewName, q)
        res = self._doBinReq(req)
        if isinstance(res, dict):
            self._checkStatus(res)
        return res

    def scrobble(self, sid, submission=True, listenTime=None):
        """
        since: 1.5.0

        "Scrobbles" a given music file on last.fm.  Requires that the user
        has set this up.

        Since 1.8.0 you may specify multiple id (and optionally time)
        parameters to scrobble multiple files.

        Since 1.11.0 this method will also update the play count and
        last played timestamp for the song and album. It will also make
        the song appear in the "Now playing" page in the web app, and
        appear in the list of songs returned by getNowPlaying

        sid:str             The ID of the file to scrobble
        submission:bool     Whether this is a "submission" or a "now playing"
                            notification
        listenTime:int      (Since 1.8.0) The time (unix timestamp) at
                            which the song was listened to.

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'scrobble'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': sid, 'submission': submission,
            'time': self._ts2milli(listenTime)})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def changePassword(self, username, password):
        """
        since: 1.1.0

        Changes the password of an existing Subsonic user.  Note that the
        user performing this must have admin privileges

        username:str        The username whose password is being changed
        password:str        The new password of the user

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'changePassword'
        viewName = '%s.view' % methodName
        hexPass = 'enc:%s' % self._hexEnc(password)

        # There seems to be an issue with some subsonic implementations
        # not recognizing the "enc:" precursor to the encoded password and
        # encodes the whole "enc:<hex>" as the password.  Weird.
        #q = {'username': username, 'password': hexPass.lower()}
        q = {'username': username, 'password': password}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getUser(self, username):
        """
        since: 1.3.0

        Get details about a given user, including which auth roles it has.
        Can be used to enable/disable certain features in the client, such
        as jukebox control

        username:str        The username to retrieve.  You can only retrieve
                            your own user unless you have admin privs.

        Returns a dict like the following:

        {u'status': u'ok',
         u'user': {u'adminRole': False,
               u'commentRole': False,
               u'coverArtRole': False,
               u'downloadRole': True,
               u'jukeboxRole': False,
               u'playlistRole': True,
               u'podcastRole': False,
               u'settingsRole': True,
               u'streamRole': True,
               u'uploadRole': True,
               u'username': u'test'},
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getUser'
        viewName = '%s.view' % methodName

        q = {'username': username}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getUsers(self):
        """
        since 1.8.0

        Gets a list of users

        returns a dict like the following

        {u'status': u'ok',
         u'users': {u'user': [{u'adminRole': True,
                   u'commentRole': True,
                   u'coverArtRole': True,
                   u'downloadRole': True,
                   u'jukeboxRole': True,
                   u'playlistRole': True,
                   u'podcastRole': True,
                   u'scrobblingEnabled': True,
                   u'settingsRole': True,
                   u'shareRole': True,
                   u'streamRole': True,
                   u'uploadRole': True,
                   u'username': u'user1'},
                   ...
                   ...
                   ]},
         u'version': u'1.10.2',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getUsers'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def createUser(self, username, password, email,
            ldapAuthenticated=False, adminRole=False, settingsRole=True,
            streamRole=True, jukeboxRole=False, downloadRole=False,
            uploadRole=False, playlistRole=False, coverArtRole=False,
            commentRole=False, podcastRole=False, shareRole=False,
            musicFolderId=None):
        """
        since: 1.1.0

        Creates a new subsonic user, using the parameters defined.  See the
        documentation at http://subsonic.org for more info on all the roles.

        username:str        The username of the new user
        password:str        The password for the new user
        email:str           The email of the new user
        <For info on the boolean roles, see http://subsonic.org for more info>
        musicFolderId:int   These are the only folders the user has access to

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'createUser'
        viewName = '%s.view' % methodName
        hexPass = 'enc:%s' % self._hexEnc(password)

        q = self._getQueryDict({
            'username': username, 'password': hexPass, 'email': email,
            'ldapAuthenticated': ldapAuthenticated, 'adminRole': adminRole,
            'settingsRole': settingsRole, 'streamRole': streamRole,
            'jukeboxRole': jukeboxRole, 'downloadRole': downloadRole,
            'uploadRole': uploadRole, 'playlistRole': playlistRole,
            'coverArtRole': coverArtRole, 'commentRole': commentRole,
            'podcastRole': podcastRole, 'shareRole': shareRole,
            'musicFolderId': musicFolderId
        })

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def updateUser(self, username,  password=None, email=None,
            ldapAuthenticated=False, adminRole=False, settingsRole=True,
            streamRole=True, jukeboxRole=False, downloadRole=False,
            uploadRole=False, playlistRole=False, coverArtRole=False,
            commentRole=False, podcastRole=False, shareRole=False,
            musicFolderId=None, maxBitRate=0):
        """
        since 1.10.1

        Modifies an existing Subsonic user.

        username:str        The username of the user to update.
        musicFolderId:int   Only return results from the music folder
                            with the given ID. See getMusicFolders
        maxBitRate:int      The max bitrate for the user.  0 is unlimited

        All other args are the same as create user and you can update
        whatever item you wish to update for the given username.

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'updateUser'
        viewName = '%s.view' % methodName
        if password is not None:
            password = 'enc:%s' % self._hexEnc(password)
        q = self._getQueryDict({'username': username, 'password': password,
            'email': email, 'ldapAuthenticated': ldapAuthenticated,
            'adminRole': adminRole,
            'settingsRole': settingsRole, 'streamRole': streamRole,
            'jukeboxRole': jukeboxRole, 'downloadRole': downloadRole,
            'uploadRole': uploadRole, 'playlistRole': playlistRole,
            'coverArtRole': coverArtRole, 'commentRole': commentRole,
            'podcastRole': podcastRole, 'shareRole': shareRole,
            'musicFolderId': musicFolderId, 'maxBitRate': maxBitRate
        })
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def deleteUser(self, username):
        """
        since: 1.3.0

        Deletes an existing Subsonic user.  Of course, you must have admin
        rights for this.

        username:str        The username of the user to delete

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'deleteUser'
        viewName = '%s.view' % methodName

        q = {'username': username}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getChatMessages(self, since=1):
        """
        since: 1.2.0

        Returns the current visible (non-expired) chat messages.

        since:int       Only return messages newer than this timestamp

        NOTE: All times returned are in MILLISECONDS since the Epoch, not
              seconds!

        Returns a dict like the following:
        {u'chatMessages': {u'chatMessage': {u'message': u'testing 123',
                                            u'time': 1303411919872L,
                                            u'username': u'admin'}},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getChatMessages'
        viewName = '%s.view' % methodName

        q = {'since': self._ts2milli(since)}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def addChatMessage(self, message):
        """
        since: 1.2.0

        Adds a message to the chat log

        message:str     The message to add

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'addChatMessage'
        viewName = '%s.view' % methodName

        q = {'message': message}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getAlbumList(self, ltype, size=10, offset=0, fromYear=None,
            toYear=None, genre=None, musicFolderId=None):
        """
        since: 1.2.0

        Returns a list of random, newest, highest rated etc. albums.
        Similar to the album lists on the home page of the Subsonic
        web interface

        ltype:str       The list type. Must be one of the following: random,
                        newest, highest, frequent, recent,
                        (since 1.8.0 -> )starred, alphabeticalByName,
                        alphabeticalByArtist
                        Since 1.10.1 you can use byYear and byGenre to
                        list albums in a given year range or genre.
        size:int        The number of albums to return. Max 500
        offset:int      The list offset. Use for paging. Max 5000
        fromYear:int    If you specify the ltype as "byYear", you *must*
                        specify fromYear
        toYear:int      If you specify the ltype as "byYear", you *must*
                        specify toYear
        genre:str       The name of the genre e.g. "Rock".  You must specify
                        genre if you set the ltype to "byGenre"
        musicFolderId:str   Only return albums in the music folder with
                            the given ID. See getMusicFolders()

        Returns a dict like the following:

        {u'albumList': {u'album': [{u'artist': u'Hank Williams',
                            u'id': u'3264928374',
                            u'isDir': True,
                            u'parent': u'9238479283',
                            u'title': u'The Original Singles Collection...Plus'},
                           {u'artist': u'Freundeskreis',
                            u'coverArt': u'9823749823',
                            u'id': u'23492834',
                            u'isDir': True,
                            u'parent': u'9827492374',
                            u'title': u'Quadratur des Kreises'}]},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getAlbumList'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'type': ltype, 'size': size,
            'offset': offset, 'fromYear': fromYear, 'toYear': toYear,
            'genre': genre, 'musicFolderId': musicFolderId})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getAlbumList2(self, ltype, size=10, offset=0, fromYear=None,
            toYear=None, genre=None):
        """
        since 1.8.0

        Returns a list of random, newest, highest rated etc. albums.
        This is similar to getAlbumList, but uses ID3 tags for
        organization

        ltype:str       The list type. Must be one of the following: random,
                        newest, highest, frequent, recent,
                        (since 1.8.0 -> )starred, alphabeticalByName,
                        alphabeticalByArtist
                        Since 1.10.1 you can use byYear and byGenre to
                        list albums in a given year range or genre.
        size:int        The number of albums to return. Max 500
        offset:int      The list offset. Use for paging. Max 5000
        fromYear:int    If you specify the ltype as "byYear", you *must*
                        specify fromYear
        toYear:int      If you specify the ltype as "byYear", you *must*
                        specify toYear
        genre:str       The name of the genre e.g. "Rock".  You must specify
                        genre if you set the ltype to "byGenre"

        Returns a dict like the following:
           {u'albumList2': {u'album': [{u'artist': u'Massive Attack',
                             u'artistId': 0,
                             u'coverArt': u'al-0',
                             u'created': u'2009-08-28T10:00:44',
                             u'duration': 3762,
                             u'id': 0,
                             u'name': u'100th Window',
                             u'songCount': 9},
                            {u'artist': u'Massive Attack',
                             u'artistId': 0,
                             u'coverArt': u'al-5',
                             u'created': u'2003-11-03T22:00:00',
                             u'duration': 2715,
                             u'id': 5,
                             u'name': u'Blue Lines',
                             u'songCount': 9}]},
            u'status': u'ok',
            u'version': u'1.8.0',
            u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getAlbumList2'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'type': ltype, 'size': size,
            'offset': offset, 'fromYear': fromYear, 'toYear': toYear,
            'genre': genre})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getRandomSongs(self, size=10, genre=None, fromYear=None,
            toYear=None, musicFolderId=None):
        """
        since 1.2.0

        Returns random songs matching the given criteria

        size:int            The max number of songs to return. Max 500
        genre:str           Only return songs from this genre
        fromYear:int        Only return songs after or in this year
        toYear:int          Only return songs before or in this year
        musicFolderId:str   Only return songs in the music folder with the
                            given ID.  See getMusicFolders

        Returns a dict like the following:

        {u'randomSongs': {u'song': [{u'album': u'1998 EP - Airbag (How Am I Driving)',
                             u'artist': u'Radiohead',
                             u'bitRate': 320,
                             u'contentType': u'audio/mpeg',
                             u'duration': 129,
                             u'id': u'9284728934',
                             u'isDir': False,
                             u'isVideo': False,
                             u'parent': u'983249823',
                             u'path': u'Radiohead/1998 EP - Airbag (How Am I Driving)/06 - Melatonin.mp3',
                             u'size': 5177469,
                             u'suffix': u'mp3',
                             u'title': u'Melatonin'},
                            {u'album': u'Mezmerize',
                             u'artist': u'System Of A Down',
                             u'bitRate': 214,
                             u'contentType': u'audio/mpeg',
                             u'coverArt': u'23849372894',
                             u'duration': 176,
                             u'id': u'28937492834',
                             u'isDir': False,
                             u'isVideo': False,
                             u'parent': u'92837492837',
                             u'path': u'System Of A Down/Mesmerize/10 - System Of A Down - Old School Hollywood.mp3',
                             u'size': 4751360,
                             u'suffix': u'mp3',
                             u'title': u'Old School Hollywood',
                             u'track': 10}]},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getRandomSongs'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'size': size, 'genre': genre,
            'fromYear': fromYear, 'toYear': toYear,
            'musicFolderId': musicFolderId})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getLyrics(self, artist=None, title=None):
        """
        since: 1.2.0

        Searches for and returns lyrics for a given song

        artist:str      The artist name
        title:str       The song title

        Returns a dict like the following for
        getLyrics('Bob Dylan', 'Blowin in the wind'):

        {u'lyrics': {u'artist': u'Bob Dylan',
             u'content': u"How many roads must a man walk down<snip>",
             u'title': u"Blowin' in the Wind"},
         u'status': u'ok',
         u'version': u'1.5.0',
         u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getLyrics'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'artist': artist, 'title': title})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def jukeboxControl(self, action, index=None, sids=[], gain=None,
            offset=None):
        """
        since: 1.2.0

        NOTE: Some options were added as of API version 1.7.0

        Controls the jukebox, i.e., playback directly on the server's
        audio hardware. Note: The user must be authorized to control
        the jukebox

        action:str      The operation to perform. Must be one of: get,
                        start, stop, skip, add, clear, remove, shuffle,
                        setGain, status (added in API 1.7.0),
                        set (added in API 1.7.0)
        index:int       Used by skip and remove. Zero-based index of the
                        song to skip to or remove.
        sids:str        Used by "add" and "set". ID of song to add to the
                        jukebox playlist. Use multiple id parameters to
                        add many songs in the same request.  Whether you
                        are passing one song or many into this, this
                        parameter MUST be a list
        gain:float      Used by setGain to control the playback volume.
                        A float value between 0.0 and 1.0
        offset:int      (added in API 1.7.0) Used by "skip".  Start playing
                        this many seconds into the track.
        """
        methodName = 'jukeboxControl'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'action': action, 'index': index,
            'gain': gain, 'offset': offset})

        req = None
        if action == 'add':
            # We have to deal with the sids
            if not (isinstance(sids, list) or isinstance(sids, tuple)):
                raise ArgumentError('If you are adding songs, "sids" must '
                    'be a list or tuple!')
            req = self._getRequestWithList(viewName, 'id', sids, q)
        else:
            req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getPodcasts(self, incEpisodes=True, pid=None):
        """
        since: 1.6.0

        Returns all podcast channels the server subscribes to and their
        episodes.

        incEpisodes:bool    (since: 1.9.0) Whether to include Podcast
                            episodes in the returned result.
        pid:str             (since: 1.9.0) If specified, only return
                            the Podcast channel with this ID.

        Returns a dict like the following:
        {u'status': u'ok',
         u'version': u'1.6.0',
         u'xmlns': u'http://subsonic.org/restapi',
         u'podcasts': {u'channel': {u'description': u"Dr Chris Smith...",
                            u'episode': [{u'album': u'Dr Karl and the Naked Scientist',
                                          u'artist': u'BBC Radio 5 live',
                                          u'bitRate': 64,
                                          u'contentType': u'audio/mpeg',
                                          u'coverArt': u'2f6f7074',
                                          u'description': u'Dr Karl answers all your science related questions.',
                                          u'duration': 2902,
                                          u'genre': u'Podcast',
                                          u'id': 0,
                                          u'isDir': False,
                                          u'isVideo': False,
                                          u'parent': u'2f6f70742f737562736f6e69632f706f6463617374732f4472204b61726c20616e6420746865204e616b656420536369656e74697374',
                                          u'publishDate': u'2011-08-17 22:06:00.0',
                                          u'size': 23313059,
                                          u'status': u'completed',
                                          u'streamId': u'2f6f70742f737562736f6e69632f706f6463617374732f4472204b61726c20616e6420746865204e616b656420536369656e746973742f64726b61726c5f32303131303831382d30343036612e6d7033',
                                          u'suffix': u'mp3',
                                          u'title': u'DrKarl: Peppermints, Chillies & Receptors',
                                          u'year': 2011},
                                         {u'description': u'which is warmer, a bath with bubbles in it or one without?  Just one of the stranger science stories tackled this week by Dr Chris Smith and the Naked Scientists!',
                                          u'id': 1,
                                          u'publishDate': u'2011-08-14 21:05:00.0',
                                          u'status': u'skipped',
                                          u'title': u'DrKarl: how many bubbles in your bath? 15 AUG 11'},
                                          ...
                                         {u'description': u'Dr Karl joins Rhod to answer all your science questions',
                                          u'id': 9,
                                          u'publishDate': u'2011-07-06 22:12:00.0',
                                          u'status': u'skipped',
                                          u'title': u'DrKarl: 8 Jul 11 The Strange Sound of the MRI Scanner'}],
                            u'id': 0,
                            u'status': u'completed',
                            u'title': u'Dr Karl and the Naked Scientist',
                            u'url': u'http://downloads.bbc.co.uk/podcasts/fivelive/drkarl/rss.xml'}}
        }

        See also: http://subsonic.svn.sourceforge.net/viewvc/subsonic/trunk/subsonic-main/src/main/webapp/xsd/podcasts_example_1.xml?view=markup
        """
        methodName = 'getPodcasts'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'includeEpisodes': incEpisodes,
            'id': pid})
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getShares(self):
        """
        since: 1.6.0

        Returns information about shared media this user is allowed to manage

        Note that entry can be either a single dict or a list of dicts

        Returns a dict like the following:

        {u'status': u'ok',
         u'version': u'1.6.0',
         u'xmlns': u'http://subsonic.org/restapi',
         u'shares': {u'share': [
             {u'created': u'2011-08-18T10:01:35',
              u'entry': {u'artist': u'Alice In Chains',
                         u'coverArt': u'2f66696c65732f6d7033732f412d4d2f416c69636520496e20436861696e732f416c69636520496e20436861696e732f636f7665722e6a7067',
                         u'id': u'2f66696c65732f6d7033732f412d4d2f416c69636520496e20436861696e732f416c69636520496e20436861696e73',
                         u'isDir': True,
                         u'parent': u'2f66696c65732f6d7033732f412d4d2f416c69636520496e20436861696e73',
                         u'title': u'Alice In Chains'},
              u'expires': u'2012-08-18T10:01:35',
              u'id': 0,
              u'url': u'http://crustymonkey.subsonic.org/share/BuLbF',
              u'username': u'admin',
              u'visitCount': 0
             }]}
        }
        """
        methodName = 'getShares'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def createShare(self, shids=[], description=None, expires=None):
        """
        since: 1.6.0

        Creates a public URL that can be used by anyone to stream music
        or video from the Subsonic server. The URL is short and suitable
        for posting on Facebook, Twitter etc. Note: The user must be
        authorized to share (see Settings > Users > User is allowed to
        share files with anyone).

        shids:list[str]              A list of ids of songs, albums or videos
                                    to share.
        description:str             A description that will be displayed to
                                    people visiting the shared media
                                    (optional).
        expires:float               A timestamp pertaining to the time at
                                    which this should expire (optional)

        This returns a structure like you would get back from getShares()
        containing just your new share.
        """
        methodName = 'createShare'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'description': description,
            'expires': self._ts2milli(expires)})
        req = self._getRequestWithList(viewName, 'id', shids, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def updateShare(self, shid, description=None, expires=None):
        """
        since: 1.6.0

        Updates the description and/or expiration date for an existing share

        shid:str            The id of the share to update
        description:str     The new description for the share (optional).
        expires:float       The new timestamp for the expiration time of this
                            share (optional).
        """
        methodName = 'updateShare'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': shid, 'description': description,
            expires: self._ts2milli(expires)})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def deleteShare(self, shid):
        """
        since: 1.6.0

        Deletes an existing share

        shid:str        The id of the share to delete

        Returns a standard response dict
        """
        methodName = 'deleteShare'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': shid})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def setRating(self, id, rating):
        """
        since: 1.6.0

        Sets the rating for a music file

        id:str          The id of the item (song/artist/album) to rate
        rating:int      The rating between 1 and 5 (inclusive), or 0 to remove
                        the rating

        Returns a standard response dict
        """
        methodName = 'setRating'
        viewName = '%s.view' % methodName

        try:
            rating = int(rating)
        except:
            raise ArgumentError('Rating must be an integer between 0 and 5: '
                '%r' % rating)
        if rating < 0 or rating > 5:
            raise ArgumentError('Rating must be an integer between 0 and 5: '
                '%r' % rating)

        q = self._getQueryDict({'id': id, 'rating': rating})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getArtists(self):
        """
        since 1.8.0

        Similar to getIndexes(), but this method uses the ID3 tags to
        determine the artist

        Returns a dict like the following:
            {u'artists': {u'index': [{u'artist': {u'albumCount': 7,
                                      u'coverArt': u'ar-0',
                                      u'id': 0,
                                      u'name': u'Massive Attack'},
                          u'name': u'M'},
                         {u'artist': {u'albumCount': 2,
                                      u'coverArt': u'ar-1',
                                      u'id': 1,
                                      u'name': u'Tune-Yards'},
                          u'name': u'T'}]},
             u'status': u'ok',
             u'version': u'1.8.0',
             u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getArtists'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getArtist(self, id):
        """
        since 1.8.0

        Returns the info (albums) for an artist.  This method uses
        the ID3 tags for organization

        id:str      The artist ID

        Returns a dict like the following:

           {u'artist': {u'album': [{u'artist': u'Tune-Yards',
                         u'artistId': 1,
                         u'coverArt': u'al-7',
                         u'created': u'2012-01-30T12:35:33',
                         u'duration': 3229,
                         u'id': 7,
                         u'name': u'Bird-Brains',
                         u'songCount': 13},
                        {u'artist': u'Tune-Yards',
                         u'artistId': 1,
                         u'coverArt': u'al-8',
                         u'created': u'2011-03-22T15:08:00',
                         u'duration': 2531,
                         u'id': 8,
                         u'name': u'W H O K I L L',
                         u'songCount': 10}],
             u'albumCount': 2,
             u'coverArt': u'ar-1',
             u'id': 1,
             u'name': u'Tune-Yards'},
            u'status': u'ok',
            u'version': u'1.8.0',
            u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getArtist'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': id})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getAlbum(self, id):
        """
        since 1.8.0

        Returns the info and songs for an album.  This method uses
        the ID3 tags for organization

        id:str      The album ID

        Returns a dict like the following:

           {u'album': {u'artist': u'Massive Attack',
            u'artistId': 0,
            u'coverArt': u'al-0',
            u'created': u'2009-08-28T10:00:44',
            u'duration': 3762,
            u'id': 0,
            u'name': u'100th Window',
            u'song': [{u'album': u'100th Window',
                       u'albumId': 0,
                       u'artist': u'Massive Attack',
                       u'artistId': 0,
                       u'bitRate': 192,
                       u'contentType': u'audio/mpeg',
                       u'coverArt': 2,
                       u'created': u'2009-08-28T10:00:57',
                       u'duration': 341,
                       u'genre': u'Rock',
                       u'id': 14,
                       u'isDir': False,
                       u'isVideo': False,
                       u'parent': 2,
                       u'path': u'Massive Attack/100th Window/01 - Future Proof.mp3',
                       u'size': 8184445,
                       u'suffix': u'mp3',
                       u'title': u'Future Proof',
                       u'track': 1,
                       u'type': u'music',
                       u'year': 2003}],
              u'songCount': 9},
            u'status': u'ok',
            u'version': u'1.8.0',
            u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getAlbum'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': id})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getSong(self, id):
        """
        since 1.8.0

        Returns the info for a song.  This method uses the ID3
        tags for organization

        id:str      The song ID

        Returns a dict like the following:
            {u'song': {u'album': u'W H O K I L L',
               u'albumId': 8,
               u'artist': u'Tune-Yards',
               u'artistId': 1,
               u'bitRate': 320,
               u'contentType': u'audio/mpeg',
               u'coverArt': 106,
               u'created': u'2011-03-22T15:08:00',
               u'discNumber': 1,
               u'duration': 192,
               u'genre': u'Indie Rock',
               u'id': 120,
               u'isDir': False,
               u'isVideo': False,
               u'parent': 106,
               u'path': u'Tune Yards/Who Kill/10 Killa.mp3',
               u'size': 7692656,
               u'suffix': u'mp3',
               u'title': u'Killa',
               u'track': 10,
               u'type': u'music',
               u'year': 2011},
             u'status': u'ok',
             u'version': u'1.8.0',
             u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getSong'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': id})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getVideos(self):
        """
        since 1.8.0

        Returns all video files

        Returns a dict like the following:
            {u'status': u'ok',
             u'version': u'1.8.0',
             u'videos': {u'video': {u'bitRate': 384,
                        u'contentType': u'video/x-matroska',
                        u'created': u'2012-08-26T13:36:44',
                        u'duration': 1301,
                        u'id': 130,
                        u'isDir': False,
                        u'isVideo': True,
                        u'path': u'South Park - 16x07 - Cartman Finds Love.mkv',
                        u'size': 287309613,
                        u'suffix': u'mkv',
                        u'title': u'South Park - 16x07 - Cartman Finds Love',
                        u'transcodedContentType': u'video/x-flv',
                        u'transcodedSuffix': u'flv'}},
             u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getVideos'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getStarred(self, musicFolderId=None):
        """
        since 1.8.0

        musicFolderId:int   Only return results from the music folder
                            with the given ID. See getMusicFolders

        Returns starred songs, albums and artists

        Returns a dict like the following:
            {u'starred': {u'album': {u'album': u'Bird-Brains',
                         u'artist': u'Tune-Yards',
                         u'coverArt': 105,
                         u'created': u'2012-01-30T13:16:58',
                         u'id': 105,
                         u'isDir': True,
                         u'parent': 104,
                         u'starred': u'2012-08-26T13:18:34',
                         u'title': u'Bird-Brains'},
              u'song': [{u'album': u'Mezzanine',
                         u'albumId': 4,
                         u'artist': u'Massive Attack',
                         u'artistId': 0,
                         u'bitRate': 256,
                         u'contentType': u'audio/mpeg',
                         u'coverArt': 6,
                         u'created': u'2009-06-15T07:48:28',
                         u'duration': 298,
                         u'genre': u'Dub',
                         u'id': 72,
                         u'isDir': False,
                         u'isVideo': False,
                         u'parent': 6,
                         u'path': u'Massive Attack/Mezzanine/Massive Attack_02_mezzanine.mp3',
                         u'size': 9564160,
                         u'starred': u'2012-08-26T13:19:26',
                         u'suffix': u'mp3',
                         u'title': u'Risingson',
                         u'track': 2,
                         u'type': u'music'},
                        {u'album': u'Mezzanine',
                         u'albumId': 4,
                         u'artist': u'Massive Attack',
                         u'artistId': 0,
                         u'bitRate': 256,
                         u'contentType': u'audio/mpeg',
                         u'coverArt': 6,
                         u'created': u'2009-06-15T07:48:25',
                         u'duration': 380,
                         u'genre': u'Dub',
                         u'id': 71,
                         u'isDir': False,
                         u'isVideo': False,
                         u'parent': 6,
                         u'path': u'Massive Attack/Mezzanine/Massive Attack_01_mezzanine.mp3',
                         u'size': 12179456,
                         u'starred': u'2012-08-26T13:19:03',
                         u'suffix': u'mp3',
                         u'title': u'Angel',
                         u'track': 1,
                         u'type': u'music'}]},
             u'status': u'ok',
             u'version': u'1.8.0',
             u'xmlns': u'http://subsonic.org/restapi'}
        """
        methodName = 'getStarred'
        viewName = '%s.view' % methodName

        q = {}
        if musicFolderId:
            q['musicFolderId'] = musicFolderId

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getStarred2(self, musicFolderId=None):
        """
        since 1.8.0

        musicFolderId:int   Only return results from the music folder
                            with the given ID. See getMusicFolders

        Returns starred songs, albums and artists like getStarred(),
        but this uses ID3 tags for organization

        Returns a dict like the following:

            **See the output from getStarred()**
        """
        methodName = 'getStarred2'
        viewName = '%s.view' % methodName

        q = {}
        if musicFolderId:
            q['musicFolderId'] = musicFolderId

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def updatePlaylist(self, lid, name=None, comment=None, songIdsToAdd=[],
            songIndexesToRemove=[]):
        """
        since 1.8.0

        Updates a playlist.  Only the owner of a playlist is allowed to
        update it.

        lid:str                 The playlist id
        name:str                The human readable name of the playlist
        comment:str             The playlist comment
        songIdsToAdd:list       A list of song IDs to add to the playlist
        songIndexesToRemove:list    Remove the songs at the
                                    0 BASED INDEXED POSITIONS in the
                                    playlist, NOT the song ids.  Note that
                                    this is always a list.

        Returns a normal status response dict
        """
        methodName = 'updatePlaylist'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'playlistId': lid, 'name': name,
            'comment': comment})
        if not isinstance(songIdsToAdd, list) or isinstance(songIdsToAdd,
                tuple):
            songIdsToAdd = [songIdsToAdd]
        if not isinstance(songIndexesToRemove, list) or isinstance(
                songIndexesToRemove, tuple):
            songIndexesToRemove = [songIndexesToRemove]
        listMap = {'songIdToAdd': songIdsToAdd,
            'songIndexToRemove': songIndexesToRemove}
        req = self._getRequestWithLists(viewName, listMap, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getAvatar(self, username):
        """
        since 1.8.0

        Returns the avatar for a user or None if the avatar does not exist

        username:str    The user to retrieve the avatar for

        Returns the file-like object for reading or raises an exception
        on error
        """
        methodName = 'getAvatar'
        viewName = '%s.view' % methodName

        q = {'username': username}

        req = self._getRequest(viewName, q)
        try:
            res = self._doBinReq(req)
        except urllib2.HTTPError:
            # Avatar is not set/does not exist, return None
            return None
        if isinstance(res, dict):
            self._checkStatus(res)
        return res

    def star(self, sids=[], albumIds=[], artistIds=[]):
        """
        since 1.8.0

        Attaches a star to songs, albums or artists

        sids:list       A list of song IDs to star
        albumIds:list   A list of album IDs to star.  Use this rather than
                        "sids" if the client access the media collection
                        according to ID3 tags rather than file
                        structure
        artistIds:list  The ID of an artist to star.  Use this rather
                        than sids if the client access the media
                        collection according to ID3 tags rather
                        than file structure

        Returns a normal status response dict
        """
        methodName = 'star'
        viewName = '%s.view' % methodName

        if not isinstance(sids, list) or isinstance(sids, tuple):
            sids = [sids]
        if not isinstance(albumIds, list) or isinstance(albumIds, tuple):
            albumIds = [albumIds]
        if not isinstance(artistIds, list) or isinstance(artistIds, tuple):
            artistIds = [artistIds]
        listMap = {'id': sids,
            'albumId': albumIds,
            'artistId': artistIds}
        req = self._getRequestWithLists(viewName, listMap)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def unstar(self, sids=[], albumIds=[], artistIds=[]):
        """
        since 1.8.0

        Removes a star to songs, albums or artists.  Basically, the
        same as star in reverse

        sids:list       A list of song IDs to star
        albumIds:list   A list of album IDs to star.  Use this rather than
                        "sids" if the client access the media collection
                        according to ID3 tags rather than file
                        structure
        artistIds:list  The ID of an artist to star.  Use this rather
                        than sids if the client access the media
                        collection according to ID3 tags rather
                        than file structure

        Returns a normal status response dict
        """
        methodName = 'unstar'
        viewName = '%s.view' % methodName

        if not isinstance(sids, list) or isinstance(sids, tuple):
            sids = [sids]
        if not isinstance(albumIds, list) or isinstance(albumIds, tuple):
            albumIds = [albumIds]
        if not isinstance(artistIds, list) or isinstance(artistIds, tuple):
            artistIds = [artistIds]
        listMap = {'id': sids,
            'albumId': albumIds,
            'artistId': artistIds}
        req = self._getRequestWithLists(viewName, listMap)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getGenres(self):
        """
        since 1.9.0

        Returns all genres
        """
        methodName = 'getGenres'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getSongsByGenre(self, genre, count=10, offset=0, musicFolderId=None):
        """
        since 1.9.0

        Returns songs in a given genre

        genre:str       The genre, as returned by getGenres()
        count:int       The maximum number of songs to return.  Max is 500
                        default: 10
        offset:int      The offset if you are paging.  default: 0
        musicFolderId:int   Only return results from the music folder
                            with the given ID. See getMusicFolders
        """
        methodName = 'getGenres'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'genre': genre,
            'count': count,
            'offset': offset,
            'musicFolderId': musicFolderId,
        })

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def hls (self, mid, bitrate=None):
        """
        since 1.8.0

        Creates an HTTP live streaming playlist for streaming video or
        audio HLS is a streaming protocol implemented by Apple and
        works by breaking the overall stream into a sequence of small
        HTTP-based file downloads. It's supported by iOS and newer
        versions of Android. This method also supports adaptive
        bitrate streaming, see the bitRate parameter.

        mid:str     The ID of the media to stream
        bitrate:str If specified, the server will attempt to limit the
                    bitrate to this value, in kilobits per second. If
                    this parameter is specified more than once, the
                    server will create a variant playlist, suitable
                    for adaptive bitrate streaming. The playlist will
                    support streaming at all the specified bitrates.
                    The server will automatically choose video dimensions
                    that are suitable for the given bitrates.
                    (since: 1.9.0) you may explicitly request a certain
                    width (480) and height (360) like so:
                    bitRate=1000@480x360

        Returns the raw m3u8 file as a string
        """
        methodName = 'hls'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': mid, 'bitrate': bitrate})
        req = self._getRequest(viewName, q)
        try:
            res = self._doBinReq(req)
        except urllib2.HTTPError:
            # Avatar is not set/does not exist, return None
            return None
        if isinstance(res, dict):
            self._checkStatus(res)
        return res.read()

    def refreshPodcasts(self):
        """
        since: 1.9.0

        Tells the server to check for new Podcast episodes. Note: The user
        must be authorized for Podcast administration
        """
        methodName = 'refreshPodcasts'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def createPodcastChannel(self, url):
        """
        since: 1.9.0

        Adds a new Podcast channel.  Note: The user must be authorized
        for Podcast administration

        url:str     The URL of the Podcast to add
        """
        methodName = 'createPodcastChannel'
        viewName = '%s.view' % methodName

        q = {'url': url}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def deletePodcastChannel(self, pid):
        """
        since: 1.9.0

        Deletes a Podcast channel.  Note: The user must be authorized
        for Podcast administration

        pid:str         The ID of the Podcast channel to delete
        """
        methodName = 'deletePodcastChannel'
        viewName = '%s.view' % methodName

        q = {'id': pid}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def deletePodcastEpisode(self, pid):
        """
        since: 1.9.0

        Deletes a Podcast episode.  Note: The user must be authorized
        for Podcast administration

        pid:str         The ID of the Podcast episode to delete
        """
        methodName = 'deletePodcastEpisode'
        viewName = '%s.view' % methodName

        q = {'id': pid}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def downloadPodcastEpisode(self, pid):
        """
        since: 1.9.0

        Tells the server to start downloading a given Podcast episode.
        Note: The user must be authorized for Podcast administration

        pid:str         The ID of the Podcast episode to download
        """
        methodName = 'downloadPodcastEpisode'
        viewName = '%s.view' % methodName

        q = {'id': pid}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getInternetRadioStations(self):
        """
        since: 1.9.0

        Returns all internet radio stations
        """
        methodName = 'getInternetRadioStations'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getBookmarks(self):
        """
        since: 1.9.0

        Returns all bookmarks for this user.  A bookmark is a position
        within a media file
        """
        methodName = 'getBookmarks'
        viewName = '%s.view' % methodName

        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def createBookmark(self, mid, position, comment=None):
        """
        since: 1.9.0

        Creates or updates a bookmark (position within a media file).
        Bookmarks are personal and not visible to other users

        mid:str         The ID of the media file to bookmark.  If a bookmark
                        already exists for this file, it will be overwritten
        position:int    The position (in milliseconds) within the media file
        comment:str     A user-defined comment
        """
        methodName = 'createBookmark'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': mid, 'position': position,
            'comment': comment})

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def deleteBookmark(self, mid):
        """
        since: 1.9.0

        Deletes the bookmark for a given file

        mid:str     The ID of the media file to delete the bookmark from.
                    Other users' bookmarks are not affected
        """
        methodName = 'deleteBookmark'
        viewName = '%s.view' % methodName

        q = {'id': mid}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getArtistInfo(self, aid, count=20, includeNotPresent=False):
        """
        since: 1.11.0

        Returns artist info with biography, image URLS and similar artists
        using data from last.fm

        aid:str                 The ID of the artist, album or song
        count:int               The max number of similar artists to return
        includeNotPresent:bool  Whether to return artists that are not
                                present in the media library
        """
        methodName = 'getArtistInfo'
        viewName = '%s.view' % methodName

        q = {'id': aid, 'count': count,
            'includeNotPresent': includeNotPresent}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getArtistInfo2(self, aid, count=20, includeNotPresent=False):
        """
        since: 1.11.0

        Similar to getArtistInfo(), but organizes music according to ID3 tags

        aid:str                 The ID of the artist, album or song
        count:int               The max number of similar artists to return
        includeNotPresent:bool  Whether to return artists that are not
                                present in the media library
        """
        methodName = 'getArtistInfo2'
        viewName = '%s.view' % methodName

        q = {'id': aid, 'count': count,
            'includeNotPresent': includeNotPresent}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getSimilarSongs(self, iid, count=50):
        """
        since 1.11.0

        Returns a random collection of songs from the given artist and
        similar artists, using data from last.fm. Typically used for
        artist radio features.

        iid:str     The artist, album, or song ID
        count:int   Max number of songs to return
        """
        methodName = 'getSimilarSongs'
        viewName = '%s.view' % methodName

        q = {'id': iid, 'count': count}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getSimilarSongs2(self, iid, count=50):
        """
        since 1.11.0

        Similar to getSimilarSongs(), but organizes music according to
        ID3 tags

        iid:str     The artist, album, or song ID
        count:int   Max number of songs to return
        """
        methodName = 'getSimilarSongs2'
        viewName = '%s.view' % methodName

        q = {'id': iid, 'count': count}

        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def savePlayQueue(self, qids, current=None, position=None):
        """
        since 1.12.0

        qid:list[int]       The list of song ids in the play queue
        current:int         The id of the current playing song
        position:int        The position, in milliseconds, within the current
                            playing song

        Saves the state of the play queue for this user. This includes 
        the tracks in the play queue, the currently playing track, and 
        the position within this track. Typically used to allow a user to 
        move between different clients/apps while retaining the same play 
        queue (for instance when listening to an audio book).
        """
        methodName = 'savePlayQueue'
        viewName = '%s.view' % methodName
        if not isinstance(qids, (tuple, list)):
            qids = [qids]

        q = self._getQueryDict({'current': current, 'position': position})
        
        req = self._getRequestWithLists(viewName, {'id': qids}, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getPlayQueue(self):
        """
        since 1.12.0

        Returns the state of the play queue for this user (as set by 
        savePlayQueue). This includes the tracks in the play queue, 
        the currently playing track, and the position within this track. 
        Typically used to allow a user to move between different 
        clients/apps while retaining the same play queue (for instance 
        when listening to an audio book).
        """
        methodName = 'getPlayQueue'
        viewName = '%s.view' % methodName
        
        req = self._getRequest(viewName)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getTopSongs(self, artist, count=50):
        """
        since 1.13.0

        Returns the top songs for a given artist

        artist:str      The artist to get songs for
        count:int       The number of songs to return
        """
        methodName = 'getTopSongs'
        viewName = '%s.view' % methodName
        
        q = {'artist': artist, 'count': count}
        
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getNewestPodcasts(self, count=20):
        """
        since 1.13.0

        Returns the most recently published Podcast episodes

        count:int       The number of episodes to return
        """
        methodName = 'getNewestPodcasts'
        viewName = '%s.view' % methodName
        
        q = {'count': count}
        
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def scanMediaFolders(self):
        """
        This is not an officially supported method of the API

        Same as selecting 'Settings' > 'Scan media folders now' with
        Subsonic web GUI

        Returns True if refresh successful, False otherwise
        """
        methodName = 'scanNow'
        return self._unsupportedAPIFunction(methodName)

    def cleanupDatabase(self):
        """
        This is not an officially supported method of the API

        Same as selecting 'Settings' > 'Clean-up Database' with Subsonic
        web GUI

        Returns True if cleanup initiated successfully, False otherwise

        Subsonic stores information about all media files ever encountered.
        By cleaning up the database, information about files that are
        no longer in your media collection is permanently removed.
        """
        methodName = 'expunge'
        return self._unsupportedAPIFunction(methodName)

    def getVideoInfo(self, vid):
        """
        since 1.14.0

        Returns details for a video, including information about available
        audio tracks, subtitles (captions) and conversions.

        vid:int     The video ID
        """
        methodName = 'getVideoInfo'
        viewName = '%s.view' % methodName

        q = {'id': int(vid)}
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getAlbumInfo(self, aid):
        """
        since 1.14.0

        Returns the album notes, image URLs, etc., using data from last.fm

        aid:int     The album ID
        """
        methodName = 'getAlbumInfo'
        viewName = '%s.view' % methodName

        q = {'id': int(aid)}
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getAlbumInfo2(self, aid):
        """
        since 1.14.0

        Same as getAlbumInfo, but uses ID3 tags

        aid:int     The album ID
        """
        methodName = 'getAlbumInfo2'
        viewName = '%s.view' % methodName

        q = {'id': int(aid)}
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def getCaptions(self, vid, fmt=None):
        """
        since 1.14.0

        Returns captions (subtitles) for a video.  Use getVideoInfo for a list
        of captions.

        vid:int         The ID of the video
        fmt:str         Preferred captions format ("srt" or "vtt")
        """
        methodName = 'getCaptions'
        viewName = '%s.view' % methodName

        q = self._getQueryDict({'id': int(vid), 'format': fmt})
        req = self._getRequest(viewName, q)
        res = self._doInfoReq(req)
        self._checkStatus(res)
        return res

    def _unsupportedAPIFunction(self, methodName):
        """
        base function to call unsupported API methods

        Returns True if refresh successful, False otherwise
        :rtype : boolean
        """
        baseMethod = 'musicFolderSettings'
        viewName = '%s.view' % baseMethod

        url = '%s:%d/%s/%s?%s' % (self._baseUrl, self._port,
            self._separateServerPath(), viewName, methodName)
        req = urllib2.Request(url)
        res = self._opener.open(req)
        res_msg = res.msg.lower()
        return res_msg == 'ok'

    #
    # Private internal methods
    #
    def _getOpener(self, username, passwd):
        # Context is only relevent in >= python 2.7.9
        https_chain = HTTPSHandlerChain()
        if sys.version_info[:3] >= (2, 7, 9) and self._insecure:
            https_chain = HTTPSHandlerChain(
                context=ssl._create_unverified_context())
        opener = urllib2.build_opener(PysHTTPRedirectHandler, https_chain)
        return opener

    def _getQueryDict(self, d):
        """
        Given a dictionary, it cleans out all the values set to None
        """
        for k, v in d.items():
            if v is None:
                del d[k]
        return d

    def _getBaseQdict(self):
        qdict = {
            'f': 'json',
            'v': self._apiVersion,
            'c': self._appName,
            'u': self._username,
        }

        if self._legacyAuth:
            qdict['p'] = 'enc:%s' % self._hexEnc(self._rawPass)
        else:
            salt = self._getSalt()
            token = md5(self._rawPass + salt).hexdigest()
            qdict.update({
                's': salt,
                't': token,
            })

        return qdict

    def _getRequest(self, viewName, query={}):
        qdict = self._getBaseQdict()
        qdict.update(query)
        url = '%s:%d/%s/%s' % (self._baseUrl, self._port, self._serverPath,
            viewName)
        req = urllib2.Request(url, urlencode(qdict))

        if self._useGET:
            url += '?%s' % urlencode(qdict)
            req = urllib2.Request(url)

        return req

    def _getRequestWithList(self, viewName, listName, alist, query={}):
        """
        Like _getRequest, but allows appending a number of items with the
        same key (listName).  This bypasses the limitation of urlencode()
        """
        qdict = self._getBaseQdict()
        qdict.update(query)
        url = '%s:%d/%s/%s' % (self._baseUrl, self._port, self._serverPath,
            viewName)
        data = StringIO()
        data.write(urlencode(qdict))
        for i in alist:
            data.write('&%s' % urlencode({listName: i}))
        req = urllib2.Request(url, data.getvalue())

        if self._useGET:
            url += '?%s' % data.getvalue()
            req = urllib2.Request(url)

        return req

    def _getRequestWithLists(self, viewName, listMap, query={}):
        """
        Like _getRequestWithList(), but you must pass a dictionary
        that maps the listName to the list.  This allows for multiple
        list parameters to be used, like in updatePlaylist()

        viewName:str        The name of the view
        listMap:dict        A mapping of listName to a list of entries
        query:dict          The normal query dict
        """
        qdict = self._getBaseQdict()
        qdict.update(query)
        url = '%s:%d/%s/%s' % (self._baseUrl, self._port, self._serverPath,
            viewName)
        data = StringIO()
        data.write(urlencode(qdict))
        for k, l in listMap.iteritems():
            for i in l:
                data.write('&%s' % urlencode({k: i}))
        req = urllib2.Request(url, data.getvalue())

        if self._useGET:
            url += '?%s' % data.getvalue()
            req = urllib2.Request(url)

        return req

    def _doInfoReq(self, req):
        # Returns a parsed dictionary version of the result
        res = self._opener.open(req)
        dres = json.loads(res.read())
        return dres['subsonic-response']

    def _doBinReq(self, req):
        res = self._opener.open(req)
        contType = res.info().getheader('Content-Type')
        if contType:
            if contType.startswith('text/html') or \
                    contType.startswith('application/json'):
                dres = json.loads(res.read())
                return dres['subsonic-response']
        return res

    def _checkStatus(self, result):
        if result['status'] == 'ok':
            return True
        elif result['status'] == 'failed':
            exc = getExcByCode(result['error']['code'])
            raise exc(result['error']['message'])

    def _hexEnc(self, raw):
        """
        Returns a "hex encoded" string per the Subsonic api docs

        raw:str     The string to hex encode
        """
        ret = ''
        for c in raw:
            ret += '%02X' % ord(c)
        return ret

    def _ts2milli(self, ts):
        """
        For whatever reason, Subsonic uses timestamps in milliseconds since
        the unix epoch.  I have no idea what need there is of this precision,
        but this will just multiply the timestamp times 1000 and return the int
        """
        if ts is None:
            return None
        return int(ts * 1000)

    def _separateServerPath(self):
        """
        separate REST portion of URL from base server path.
        """
        return urllib2.splithost(self._serverPath)[1].split('/')[0]

    def _fixLastModified(self, data):
        """
        This will recursively walk through a data structure and look for
        a dict key/value pair where the key is "lastModified" and change
        the shitty java millisecond timestamp to a real unix timestamp
        of SECONDS since the unix epoch.  JAVA SUCKS!
        """
        if isinstance(data, dict):
            for k, v in data.items():
                if k == 'lastModified':
                    data[k] = long(v) / 1000.0
                    return
                elif isinstance(v, (tuple, list, dict)):
                    return self._fixLastModified(v)
        elif isinstance(data, (list, tuple)):
            for item in data:
                if isinstance(item, (list, tuple, dict)):
                    return self._fixLastModified(item)

    def _process_netrc(self, use_netrc):
        """
        The use_netrc var is either a boolean, which means we should use
        the user's default netrc, or a string specifying a path to a
        netrc formatted file

        use_netrc:bool|str      Either set to True to use the user's default
                                netrc file or a string specifying a specific
                                netrc file to use
        """
        if not use_netrc:
            raise CredentialError('useNetrc must be either a boolean "True" '
                'or a string representing a path to a netrc file, '
                'not {0}'.format(repr(use_netrc)))
        if isinstance(use_netrc, bool) and use_netrc:
            self._netrc = netrc()
        else:
            # This should be a string specifying a path to a netrc file
            self._netrc = netrc(os.path.expanduser(use_netrc))
        auth = self._netrc.authenticators(self._hostname)
        if not auth:
            raise CredentialError('No machine entry found for {0} in '
                'your netrc file'.format(self._hostname))

        # If we get here, we have credentials
        self._username = auth[0]
        self._rawPass = auth[2]

    def _getSalt(self, length=12):
        salt = md5(os.urandom(100)).hexdigest()
        return salt[:length]
