#!/usr/bin/python
# -*- coding: utf-8 -*-

# Module: main
# Author: G.Breant
# Created on: 04.10.2016
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html


import xbmcgui
import json
import os
import shutil
import dateutil.parser
from datetime import datetime


#check for Simpleplugin.  Official repos are not up to date so let's do this nasty trick.
#TO FIX : version check. https://github.com/romanvm/script.module.simpleplugin/issues/4
try:
    from simpleplugin import Plugin
    from simpleplugin import Addon
except:
    xbmcgui.Dialog().ok('SimplePlugin 2.0.1 required', "The Subsonic Addon requires SimplePlugin 2.0.1 framework.", "Please download and install it !", "https://github.com/romanvm/script.module.simpleplugin/releases") 
    sys.exit()


# Create plugin instance
plugin = Plugin()

# Make sure library folder is on the path
sys.path.append(xbmc.translatePath(
    os.path.join(plugin.addon.getAddonInfo('path'), 'lib')))

# initialize_gettext
#_ = plugin.initialize_gettext()

connection = None
cachetime = int(Addon().get_setting('cachetime'))

import libsonic_extra

def popup(text, time=5000, image=None):
    title = plugin.addon.getAddonInfo('name')
    icon = plugin.addon.getAddonInfo('icon')
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (title, text,
                        time, icon))

def get_connection():
    global connection
    
    if connection is None:
        
        connected = False
        
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
    
    if connection is False:
        return
    
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
                            menu_id=mid
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
    
    if connection is False:
        return
    
    listing = []

    menus = {
        'albums_newest': {
            'name':     'Newest albums',
            'thumb':    None,
            'args':     {"ltype": "newest"}
        },
        'albums_frequent': {
            'name':     'Most played albums',
            'thumb': None,
            'args':     {"ltype": "frequent"}
        },
        'albums_recent': {
            'name':     'Recently played albums',
            'thumb': None,
            'args':     {"ltype": "recent"}
        },
        'albums_random': {
            'name':     'Random albums',
            'thumb': None,
            'args':     {"ltype": "random"}
        }
    }

    # Iterate through categories

    for menu_id in menus:
        
        menu = menus.get(menu_id)
        
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
                            query_args=     json.dumps(menu.get('args')),
                            menu_id=        menu_id
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
    
    if connection is False:
        return
    
    listing = []

    menus = {
        'tracks_starred': {
            'name':             'Starred tracks',
            'thumb':            None,
            'is_stars_list':    True
        },
        'tracks_random': {
            'name':             'Random tracks',
            'thumb':            None
        }
    }

    # Iterate through categories

    for menu_id in menus:
        
        menu = menus.get(menu_id)
        
        # image
        if 'thumb' in menu:
            thumb = menu.get('thumb')

        listing.append({
            'label':    menu.get('name'),
            'thumb':    menu.get('thumb'), # Item thumbnail
            'fanart':   menu.get('thumb'), # Item thumbnail
            'url':      plugin.get_url(
                action=         'list_tracks',
                menu_id=        menu_id,
                is_stars_list=  menu.get('is_stars_list')
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
#@plugin.cached(cachetime) #if cache is enabled, cache data for the following function
def list_artists(params):
    
    # get connection
    connection = get_connection()
    
    if connection is False:
        return

    listing = []

    # Get items
    items = connection.walk_artists()

    # Iterate through items

    for item in items:
        entry = {
            'label':    item['name'],
            'thumb':    connection.getCoverArtUrl(item.get('id')),
            'fanart':   connection.getCoverArtUrl(item.get('id')),
            'url':      plugin.get_url(
                            action=     'list_artist_albums',
                            artist_id=  item.get('id'),
                            menu_id=    params.get('menu_id')
                        ),
            'info': {
                'music': { ##http://romanvm.github.io/Kodistubs/_autosummary/xbmcgui.html#xbmcgui.ListItem.setInfo
                    'count':    item.get('albumCount'),
                    'artist':   item.get('name')
                }
            }
        }

        #context menu actions
        context_actions = []
        if can_star('artist',item.get('id')):
            action_star =  context_action_star('artist',item.get('id'),params.get('is_stars_list'))
            context_actions.append(action_star)
        
        if len(context_actions) > 0:
            entry['context_menu'] = context_actions
        
        listing.append(entry)
        
        
        
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
#@plugin.cached(cachetime) #if cache is enabled, cache data for the following function
def list_albums(params):
    
    listing = []
    
    # get connection
    connection = get_connection()
    
    if connection is False:
        return

    #query
    query_args = {}
    try:
        query_args_json = params['query_args']
        query_args = json.loads(query_args_json)
    except:
        pass

    #size
    albums_per_page = int(Addon().get_setting('albums_per_page'))
    query_args["size"] = albums_per_page
    
    #offset
    offset = int(params.get('page',1)) - 1;
    if offset > 0:
        query_args["offset"] = offset * albums_per_page

    #debug
    query_args_json = json.dumps(query_args)
    plugin.log('list_albums with args:' + query_args_json);

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
#@plugin.cached(cachetime) #if cache is enabled, cache data for the following function
def list_artist_albums(params):
    
    # get connection
    connection = get_connection()
    
    if connection is False:
        return

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
    
    menu_id = params.get('menu_id')
    is_stars_list=  params.get('is_stars_list')

    # name

    if 'hide_artist' in params:
        title = item.get('name', '<Unknown>')
    else:
        title = '%s - %s' % (item.get('artist', '<Unknown>'),
                             item.get('name', '<Unknown>'))

    entry = {
        'label': title,
        'thumb': item.get('coverArt'),
        'fanart': item.get('coverArt'),
        'url': plugin.get_url(
            action=         'list_tracks',
            album_id=       item.get('id'),
            hide_artist=    item.get('hide_artist'),
            menu_id=        menu_id,
            is_stars_list=  is_stars_list
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
        }
    }
    
    #context menu actions
    context_actions = []

    if can_star('album',item.get('id')):
        action_star =  context_action_star('album',item.get('id'),is_stars_list)
        context_actions.append(action_star)

    if can_download('album',item.get('id')):
        action_download =  context_action_download('album',item.get('id'))
        context_actions.append(action_download)

    if len(context_actions) > 0:
        entry['context_menu'] = context_actions

    return entry

@plugin.action()
#@plugin.cached(cachetime) #if cache is enabled, cache data for the following function
def list_tracks(params):
    
    menu_id = params.get('menu_id')

    listing = []
    
    #query
    query_args = {}
    try:
        query_args_json = params['query_args']
        query_args = json.loads(query_args_json)
    except:
        pass

    #size
    tracks_per_page = int(Addon().get_setting('tracks_per_page'))
    query_args["size"] = tracks_per_page

    #offset
    offset = int(params.get('page',1)) - 1;
    if offset > 0:
        query_args["offset"] = offset * tracks_per_page
        
    #debug
    query_args_json = json.dumps(query_args)
    plugin.log('list_tracks with args:' + query_args_json);
    
    # get connection
    connection = get_connection()
    
    if connection is False:
        return

    # Album
    if 'album_id' in params:
        items = connection.walk_album(params['album_id'])
        
    # Playlist
    elif 'playlist_id' in params:
        items = connection.walk_playlist(params['playlist_id'])
        
        #TO FIX
        #tracknumber = 0
        #for item in items:
        #    tracknumber += 1
        #    items[item]['tracknumber'] = tracknumber
        
    # Starred
    elif menu_id == 'tracks_starred':
        items = connection.walk_tracks_starred()
    
    # Random
    elif menu_id == 'tracks_random':
        items = connection.walk_tracks_random(**query_args)
    
    # Filters
    #else:
        #TO WORK
        

    # Iterate through items
    key = 0;
    for item in items:
        track = get_track_entry(item,params)
        listing.append(track)
        key +=1
        
    # Root menu
    #link_root = navigate_root()
    #listing.append(link_root)
        
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
    
    menu_id = params.get('menu_id')
    is_stars_list = params.get('is_stars_list')

    # name
    if 'hide_artist' in params:
        title = item.get('title', '<Unknown>')
    else:
        title = '%s - %s' % (
            item.get('artist', '<Unknown>'),
            item.get('title', '<Unknown>')
        )
        
    #date_create
    item_date = item.get('created')
        
    # star
    if (is_stars_list):
        item_date = item.get('starred')
        #TO FIX
        #starAscii = '★'
        #star =starAscii.encode('utf-8')
        #title = "%s %s" % (star,title)

    entry = {
        'label':    title,
        'thumb':    item.get('coverArt'),
        'fanart':   item.get('coverArt'),
        'url':      plugin.get_url(
                        action=     'play_track',
                        id=         item.get('id'),
                        menu_id=    menu_id
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
            'duration':     item.get('duration'),
            'date':         item_date
            }
        }
    }
    
    #context menu actions
    context_actions = []

    if can_star('track',item.get('id')):
        action_star =  context_action_star('track',item.get('id'),is_stars_list)
        context_actions.append(action_star)

    if can_download('track',item.get('id')):
        action_download =  context_action_download('track',item.get('id'))
        context_actions.append(action_download)

    if len(context_actions) > 0:
        entry['context_menu'] = context_actions
    

    return entry


@plugin.action()
def play_track(params):
    
    id = params['id']
    plugin.log('play_track #' + id);
    
    # get connection
    connection = get_connection()
    
    if connection is False:
        return

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
#@plugin.cached(cachetime) #if cache is enabled, cache data for the following function
def list_playlists(params):
    
    # get connection
    connection = get_connection()
    
    if connection is False:
        return

    listing = []

    # Get items
    items = connection.walk_playlists()

    # Iterate through items

    for item in items:

        listing.append({
            'label':    item['name'],
            'thumb':    connection.getCoverArtUrl(item.get('id')),
            'fanart':   connection.getCoverArtUrl(item.get('id')),
            'url':      plugin.get_url(
                            action=         'list_tracks',
                            playlist_id=    item.get('id'),
                            menu_id=        params.get('menu_id')
                           
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

#star (or unstar) an item
@plugin.action()
def star_item(params):

    ids=     params.get('ids'); #can be single or lists of IDs
    unstar=  params.get('unstar',False);
    unstar = (unstar) and (unstar != 'None') and (unstar != 'False') #TO FIX better statement ?
    type=    params.get('type');
    sids = albumIds = artistIds = None

    #validate type
    if type == 'track':
        sids = ids
    elif type == 'artist':
        artistIds = ids
    elif type == 'album':
        albumIds = ids
        
    #validate capability
    if not can_star(type,ids):
        return;
        
    #validate IDs
    if (not sids and not artistIds and not albumIds):
        return;

    # get connection
    connection = get_connection()
    
    if connection is False:
        return

    ###
    
    did_action = False

    try:
        if unstar:
            request = connection.unstar(sids, albumIds, artistIds)
        else:
            request = connection.star(sids, albumIds, artistIds)

        if request['status'] == 'ok':
            did_action = True

    except:
        pass

    ###
    
    if did_action:
        
        if unstar:
            message = 'Item has been unstarred.'
            plugin.log('Unstarred %s #%s' % (type,json.dumps(ids)))
        else: #star
            message = 'Item has been starred!'
            plugin.log('Starred %s #%s' % (type,json.dumps(ids)))
            
       
        popup(message)
            
        #TO FIX clear starred lists caches ?
        #TO FIX refresh current list after star set ?
        
    else:
        if unstar:
            plugin.log_error('Unable to unstar %s #%s' % (type,json.dumps(ids)))
        else:
            plugin.log_error('Unable to star %s #%s' % (type,json.dumps(ids)))

    return did_action
        

        
def context_action_star(type,id,is_stars_list):
    
    unstar = (is_stars_list) and (is_stars_list != 'None') and (is_stars_list != 'False') #TO FIX better statement ?

    if not unstar:

        if type == 'track':
            label = 'Star track'
        elif type == 'artist':
            label = 'Star artist'
        elif type == 'album':
            label = 'Star album'
            
    else:
        
        #Should be available only in the stars lists;
        #so we don't have to fetch the starred status for each item
        #(since it is not available into the XML response from the server)

        if type == 'track':
            label = 'Unstar track'
        elif type == 'artist':
            label = 'Unstar artist'
        elif type == 'album':
            label = 'Unstar album'
    
    return (
        label, 
        'XBMC.RunPlugin(%s)' % plugin.get_url(action='star_item',type=type,ids=id,unstar=unstar)
    )

#Subsonic API says this is supported for artist,tracks and albums,
#But I can see it available only for tracks on Subsonic 5.3, so disable it.
def can_star(type,ids = None):
    
    if not ids:
        return False
    
    if not isinstance(ids, list) or isinstance(ids, tuple):
        ids = [ids]
        if len(ids) == 0:
            return False
    
    if type == 'track':
        return True
    elif type == 'artist':
        return False
    elif type == 'album':
        return False

    
def context_action_download(type,id):
    if type == 'track':
        label = 'Download track'
    elif type == 'album':
        label = 'Download album'

    return (
        label, 
        'XBMC.RunPlugin(%s)' % plugin.get_url(action='download_item',type=type,id=id)
    )

def can_download(type,id = None):
    if id is None:
        return False
    
    if type == 'track':
        return True
    elif type == 'album':
        return True
    
@plugin.action()
def download_item(params):

    id=     params.get('id'); #can be single or lists of IDs
    type=    params.get('type');
    
    #validate path
    download_folder = Addon().get_setting('download_folder')
    
    if not download_folder:
        popup("Please set a directory for your downloads")
        plugin.log_error("No directory set for downloads")

    #validate capability
    if not can_download(type,id):
        return;
    
    if type == 'track':
        did_action = download_tracks(id)
    elif type == 'album':
        did_action = download_album(id)
    
    if did_action:
        plugin.log('Downloaded %s #%s' % (type,id))
        popup('Item has been downloaded!')
        
    else:
        plugin.log_error('Unable to downloaded %s #%s' % (type,id))

    return did_action
    
def download_tracks(ids):

    #popup is fired before, in download_item
    download_folder = Addon().get_setting('download_folder')
    if not download_folder:
        return
    
    if not ids:
        return False
    
    #make list
    if not isinstance(ids, list) or isinstance(ids, tuple):
        ids = [ids]
        
    
    ids_count = len(ids)
    
    #check if empty
    if ids_count == 0:
        return False
    
    plugin.log('download_tracks IDs:')
    plugin.log(json.dumps(ids))

    # get connection
    connection = get_connection()
    
    if connection is False:
        return

    #progress...
    pc_step = 100/ids_count
    pc_progress = 0
    ids_parsed = 0
    progressdialog = xbmcgui.DialogProgress()
    progressdialog.create("Downloading tracks...") #Title

    for id in ids:

        if (progressdialog.iscanceled()):
            return False

        # debug
        plugin.log('Trying to download track #'+str(id))

        # get track infos
        response = connection.getSong(id);
        track = response.get('song')
        plugin.log('Track info :')
        plugin.log(track)
        
        # progress bar
        pc_progress = ids_parsed * pc_step
        progressdialog.update(pc_progress, 'Getting track informations...',"%s - %s" % (track.get('artist','<Unknown>'),track.get('title','<Unknown>')))

        track_path_relative = track.get("path", None) # 'Radiohead/Kid A/Idioteque.mp3'
        track_path = os.path.join(download_folder, track_path_relative) # 'C:/users/.../Radiohead/Kid A/Idioteque.mp3'
        track_directory = os.path.dirname(os.path.abspath(track_path))  # 'C:/users/.../Radiohead/Kid A'

        #check if file exists
        if os.path.isfile(track_path):
            
            progressdialog.update(pc_progress, 'Track has already been downloaded!')
            plugin.log("File '%s' already exists" % (id))
            
        else:
            
            progressdialog.update(pc_progress, "Downloading track...",track_path)

            try:
                #get remote file (file-object like)
                file_obj = connection.download(id)

                #create directory if it does not exists
                if not os.path.exists(track_directory):
                    os.makedirs(track_directory)

                #create blank file
                file = open(track_path, 'a') #create a new file but don't erase the existing one if it exists

                #fill blank file
                shutil.copyfileobj(file_obj, file)
                file.close()

            except:
                popup("Error while downloading track #%s" % (id))
                plugin.log("Error while downloading track #%s" % (id))
                pass
        
        ids_parsed += 1
        
    progressdialog.update(100, "Done !","Enjoy !")
    xbmc.sleep(1000)
    progressdialog.close()

def download_album(id):

    # get connection
    connection = get_connection()
    
    if connection is False:
        return

    # get album infos
    response = connection.getAlbum(id);
    album = response.get('album')
    tracks = album.get('song')
    
    plugin.log('getAlbum:')
    plugin.log(json.dumps(album))

    ids = [] #list of track IDs
    
    for i, track in enumerate(tracks):
        track_id = track.get('id')
        ids.append(track_id)

    download_tracks(ids)



# Start plugin from within Kodi.
if __name__ == "__main__":
    # Map actions
    # Note that we map callable objects without brackets ()
    plugin.actions['list_playlists'] = list_playlists
    plugin.run()





    
    
    
    
    
