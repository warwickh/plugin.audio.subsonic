#!/usr/bin/python
# -*- coding: utf-8 -*-

# Module: main
# Author: Roman V. M.
# Created on: 28.11.2014
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

from simpleplugin import Plugin
from simpleplugin import Addon
import os
import json
from datetime import datetime
import dateutil.parser



# Make sure library folder is on the path
sys.path.append(xbmc.translatePath(
    os.path.join(Addon().addon.getAddonInfo('path'), 'lib')))

# Create plugin instance
plugin = Plugin()


# initialize_gettext
#_ = plugin.initialize_gettext()

connection = None
cache_minutes = int(Addon().get_setting('cache_minutes'))

import libsonic_extra

def popup(text, time=5000, image=None):
    title = Addon().addon.getAddonInfo('name')
    icon = Addon().addon.getAddonInfo('icon')
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (title, text,
                        time, icon))

def get_connection():
    global connection
    
    if connection is None:
        # Create connection

        try:
            connection = libsonic_extra.SubsonicClient(
                Addon().get_setting('subsonic_url'),
                Addon().get_setting('username'),
                Addon().get_setting('password'),
                Addon().get_setting('apiversion'),
                Addon().get_setting('insecure') == 'true',
                Addon().get_setting('legacyauth') == 'true',
                )
            connected = connection.ping()
        except:
            pass

        if connected is False:
            popup('Connection error')
            return False

    return connection

@plugin.action()
def root(params):
    
    # get connection
    connection = get_connection()
    
    listing = []

    menus = {
        'artists': {
            'name':     'Artists',
            'callback': 'list_artists',
            'thumb': None
        },
        'albums': {
            'name':     'Albums',
            'callback': 'menu_albums',
            'thumb': None
        },
        'tracks': {
            'name':     'Tracks',
            'callback': 'menu_tracks',
            'thumb': None
        },
        'playlists': {
            'name':     'Playlists',
            'callback': 'list_playlists',
            'thumb': None
        }
    }

    # Iterate through categories

    for mid in menus:
        
        # image
        if 'thumb' in menus[mid]:
            thumb = menus[mid]['thumb']
        
        listing.append({
            'label':    menus[mid]['name'],
            'thumb':    thumb, # Item thumbnail
            'fanart':   thumb, # Item thumbnail
            'url':      plugin.get_url(
                            action=menus[mid]['callback'],
                            mid=mid
                        )
        })  # Item label

    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        #cache_to_disk = True, #cache this view to disk.
        #sort_methods = None, #he list of integer constants representing virtual folder sort methods.
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        #content = None #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )

@plugin.action()
def menu_albums(params):
    
    # get connection
    connection = get_connection()
    
    listing = []

    menus = {
        'newest': {
            'name':     'Newest albums',
            'thumb':    None,
            'args':     {"ltype": "newest"}
        },
        'frequent': {
            'name':     'Most played albums',
            'thumb': None,
            'args':     {"ltype": "frequent"}
        },
        'recent': {
            'name':     'Recently played albums',
            'thumb': None,
            'args':     {"ltype": "recent"}
        },
        'random': {
            'name':     'Random albums',
            'thumb': None,
            'args':     {"ltype": "random"}
        }
    }

    # Iterate through categories

    for mid in menus:
        
        menu = menus.get(mid)
        
        # image
        if 'thumb' in menu:
            thumb = menu.get('thumb')

        listing.append({
            'label':    menu.get('name'),
            'thumb':    menu.get('thumb'), # Item thumbnail
            'fanart':   menu.get('thumb'), # Item thumbnail
            'url':      plugin.get_url(
                            action=         'list_albums',
                            page=           1,
                            query_args=     json.dumps(menu.get('args'))
                        )
        })  # Item label

    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        #cache_to_disk = True, #cache this view to disk.
        #sort_methods = None, #he list of integer constants representing virtual folder sort methods.
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        #content = None #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )

@plugin.action()
def menu_tracks(params):
    
    # get connection
    connection = get_connection()
    
    listing = []

    menus = {
        'starred': {
            'name':     'Starred tracks',
            'thumb':    None,
            'starred':  True
        }
    }

    # Iterate through categories

    for mid in menus:
        
        menu = menus.get(mid)
        
        # image
        if 'thumb' in menu:
            thumb = menu.get('thumb')

        listing.append({
            'label':    menu.get('name'),
            'thumb':    menu.get('thumb'), # Item thumbnail
            'fanart':   menu.get('thumb'), # Item thumbnail
            'url':      plugin.get_url(
                            action=         'list_tracks',
                            starred=        menu.get('starred')
                        )
        })  # Item label

    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        #cache_to_disk = True, #cache this view to disk.
        #sort_methods = None, #he list of integer constants representing virtual folder sort methods.
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        #content = None #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )

@plugin.action()
@plugin.cached(cache_minutes) #if cache is enabled, cache data for the following function
def list_artists(params):
    
    # get connection
    connection = get_connection()

    listing = []

    # Get items
    items = connection.walk_artists()

    # Iterate through items

    for item in items:
        listing.append({
            'label':    item['name'],
            'thumb':    connection.getCoverArtUrl(item.get('id')),
            'fanart':   connection.getCoverArtUrl(item.get('id')),
            'url':      plugin.get_url(action='list_artist_albums',
                                  artist_id=item.get('id')
                        ),
            'info': {
                'music': { ##http://romanvm.github.io/Kodistubs/_autosummary/xbmcgui.html#xbmcgui.ListItem.setInfo
                    'count':    item.get('albumCount'),
                    'artist':   item.get('name')
                }
            }
        })
        
    # Sort methods - List of integer constants representing virtual folder sort methods. - see SortFileItem.h from Kodi core
    sortable_by = ( 
        0,  #SORT_METHOD_NONE
        11,  #SORT_METHOD_ARTIST
        40 #SORT_METHOD_UNSORTED
    )
        
    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        cache_to_disk = True, #cache this view to disk.
        sort_methods = sortable_by, #he list of integer constants representing virtual folder sort methods.
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        content = 'artists' #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )

@plugin.action()
@plugin.cached(cache_minutes) #if cache is enabled, cache data for the following function
def list_albums(params):
    
    listing = []
    
    # get connection
    connection = get_connection()

    query_args_json = params['query_args']
    query_args = json.loads(query_args_json)

    #size
    albums_per_page = int(Addon().get_setting('albums_per_page'))
    query_args["size"] = albums_per_page
    
    #offset
    offset = int(params.get('page')) - 1;
    if offset > 0:
        query_args["offset"] = offset * albums_per_page
     
    #TO FIX this test is for pagination
    #query_args["fromYear"] = 2016
    #query_args["toYear"] = 2016
    #query_args["ltype"] = 'byYear'
        

    #debug
    query_args_json = json.dumps(query_args)
    plugin.log('list_albums with args:' + query_args_json);
    #popup(json.dumps(query_args_json))

    #Get items
    items = connection.walk_albums(**query_args)

    # Iterate through items
    for item in items:
        album = get_album_entry(item, params)
        listing.append(album)
        
    # Root menu
    link_root = navigate_root()
    listing.append(link_root)
        
    # Pagination if we've not reached the end of the lsit
    # if type(items) != type(True): TO FIX
    link_next = navigate_next(params)
    listing.append(link_next)
    
    # Sort methods - List of integer constants representing virtual folder sort methods. - see SortFileItem.h from Kodi core
    sortable_by = (
            0,  #SORT_METHOD_NONE
            1,  #SORT_METHOD_LABEL
            #3,  #SORT_METHOD_DATE
            11, #SORT_METHOD_ARTIST
            #14, #SORT_METHOD_ALBUM
            18, #SORT_METHOD_YEAR
            #21 #SORT_METHOD_DATEADDED
            40 #SORT_METHOD_UNSORTED
    )

    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        cache_to_disk = True, #cache this view to disk.
        sort_methods = sortable_by, 
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        content = 'albums' #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )

@plugin.action()
@plugin.cached(cache_minutes) #if cache is enabled, cache data for the following function
def list_artist_albums(params):
    
    # get connection
    connection = get_connection()

    listing = []

    # Get items
    artist_id =             params['artist_id']
    params['hide_artist']   = True
    items = connection.walk_artist(artist_id)

    # Iterate through items
    for item in items:
        album = get_album_entry(item, params)
        listing.append(album)

    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        cache_to_disk = True, #cache this view to disk.
        #sort_methods = None, #he list of integer constants representing virtual folder sort methods.
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        content = 'albums' #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )

def get_album_entry(item, params):

    # name

    if 'hide_artist' in params:
        title = item.get('name', '<Unknown>')
    else:
        title = '%s - %s' % (item.get('artist', '<Unknown>'),
                             item.get('name', '<Unknown>'))

    return {
        'label': title,
        'thumb': item.get('coverArt'),
        'fanart': item.get('coverArt'),
        'url': plugin.get_url(
            action=         'list_tracks',
            album_id=       item.get('id'),
            hide_artist=    item.get('hide_artist')
        ),
        'info': {
            'music': { ##http://romanvm.github.io/Kodistubs/_autosummary/xbmcgui.html#xbmcgui.ListItem.setInfo
                'count':    item.get('songCount'),
                'date':     convert_date_from_iso8601(item.get('created')), #date added
                'duration': item.get('duration'),
                'artist':   item.get('artist'),
                'album':    item.get('name'),
                'year':     item.get('year')
            }
        },
    }

@plugin.action()
@plugin.cached(cache_minutes) #if cache is enabled, cache data for the following function
def list_tracks(params):

    listing = []
    
    # get connection
    connection = get_connection()

    # Album
    if 'album_id' in params:
        items = connection.walk_album(params['album_id'])
        
    # Playlist
    if 'playlist_id' in params:
        items = connection.walk_playlist(params['playlist_id'])
        
        #TO FIX
        #tracknumber = 0
        #for item in items:
        #    tracknumber += 1
        #    items[item]['tracknumber'] = tracknumber
        
    # Starred
    if 'starred' in params:
        items = connection.walk_tracks_starred()

        
    # Iterate through items
    key = 0;
    for item in items:
        track = get_track_entry(item,params)
        listing.append(track)
        key +=1
        
    # Root menu
    link_root = navigate_root()
    listing.append(link_root)
        
    # Pagination if we've not reached the end of the lsit
    # if type(items) != type(True): TO FIX
    #link_next = navigate_next(params)
    #listing.append(link_next)
    
    # Sort methods - List of integer constants representing virtual folder sort methods. - see SortFileItem.h from Kodi core
    sortable_by = ( 
            0,  #SORT_METHOD_NONE
            1,  #SORT_METHOD_LABEL
            #3, #SORT_METHOD_DATE
            7,  #SORT_METHOD_TRACKNUM
            11, #SORT_METHOD_ARTIST
            #14,#SORT_METHOD_ALBUM
            18, #SORT_METHOD_YEAR
            #21 #SORT_METHOD_DATEADDED
            40  #SORT_METHOD_UNSORTED
    )

    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        #cache_to_disk = True, #cache this view to disk.
        sort_methods = sortable_by, #he list of integer constants representing virtual folder sort methods.
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        content = 'songs' #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )


def get_track_entry(item,params):

    # name
    if 'hide_artist' in params:
        title = item.get('title', '<Unknown>')
    else:
        title = '%s - %s' % (
            item.get('artist', '<Unknown>'),
            item.get('title', '<Unknown>')
        )

    return {
        'label':    title,
        'thumb':    item.get('coverArt'),
        'fanart':   item.get('coverArt'),
        'url':      plugin.get_url(
                        action='play_track',
                        id=item.get('id')
                    ),
        'is_playable':  True,
        'mime':         item.get("contentType"),
        'info': {'music': { #http://romanvm.github.io/Kodistubs/_autosummary/xbmcgui.html#xbmcgui.ListItem.setInfo
            'title':        item.get('title'),
            'album':        item.get('album'),
            'artist':       item.get('artist'),
            'tracknumber':  item.get('tracknumber'),
            'year':         item.get('year'),
            'genre':        item.get('genre'),
            'size':         item.get('size'),
            'duration':     item.get('duration')
            }},
        }

@plugin.action()
def play_track(params):
    
    id = params['id']
    plugin.log('play_track #' + id);
    
    # get connection
    connection = get_connection()

    url = connection.streamUrl(sid=id,
        maxBitRate=Addon().get_setting('bitrate_streaming'),
        tformat=Addon().get_setting('transcode_format_streaming')
    )

    return url

def navigate_next(params):
  
    page =      int(params['page'])
    page +=     1
    
    title = "Next page (%d)" % (page)

    return {
        'label':    title,
        'url':      plugin.get_url(
                        action=         params['action'],
                        page=           page,
                        query_args=      params['query_args']
                    )
    }

def navigate_root():
    return {
        'label':    "Back to menu",
        'url':      plugin.get_url(action='root')
    }

#converts a date string from eg. '2012-04-17T19:53:44' to eg. '17.04.2012'
def convert_date_from_iso8601(iso8601):
    date_obj = dateutil.parser.parse(iso8601)
    return date_obj.strftime('%d.%m.%Y')

@plugin.action()
@plugin.cached(cache_minutes) #if cache is enabled, cache data for the following function
def list_playlists(params):
    
    # get connection
    connection = get_connection()

    listing = []

    # Get items
    items = connection.walk_playlists()

    # Iterate through items

    for item in items:

        listing.append({
            'label':    item['name'],
            'thumb':    connection.getCoverArtUrl(item.get('id')),
            'fanart':   connection.getCoverArtUrl(item.get('id')),
            'url':      plugin.get_url(action='list_tracks',
                            playlist_id=item.get('id'),
                           
                        ),
            'info': {'music': { ##http://romanvm.github.io/Kodistubs/_autosummary/xbmcgui.html#xbmcgui.ListItem.setInfo
                'title':        item.get('name'),
                'count':        item.get('songCount'),
                'duration':     item.get('duration'),
                'date':         convert_date_from_iso8601(item.get('created'))
            }}
        })
    return plugin.create_listing(
        listing,
        #succeeded = True, #if False Kodi won’t open a new listing and stays on the current level.
        #update_listing = False, #if True, Kodi won’t open a sub-listing but refresh the current one. 
        #cache_to_disk = True, #cache this view to disk.
        #sort_methods = None, #he list of integer constants representing virtual folder sort methods.
        #view_mode = None, #a numeric code for a skin view mode. View mode codes are different in different skins except for 50 (basic listing).
        #content = None #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    )


# Start plugin from within Kodi.
if __name__ == "__main__":
    # Map actions
    # Note that we map callable objects without brackets ()
    plugin.actions['list_playlists'] = list_playlists
    plugin.run()





    
    
    
    
    
