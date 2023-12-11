#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmcvfs
import os
import xbmcaddon
import xbmcplugin
import xbmcgui
import json
import shutil
import time
import hashlib
import random
from datetime import datetime
from collections.abc import MutableMapping
from collections import namedtuple

# Add the /lib folder to sys
sys.path.append(xbmcvfs.translatePath(os.path.join(xbmcaddon.Addon("plugin.audio.subsonic").getAddonInfo("path"), "lib")))

import libsonic

from simpleplugin import Plugin
from simpleplugin import Addon

# Create plugin instance
plugin = Plugin()

connection = None
cachetime = int(Addon().get_setting('cachetime'))

local_starred = set({})
ListContext = namedtuple('ListContext', ['listing', 'succeeded','update_listing', 'cache_to_disk','sort_methods', 'view_mode','content', 'category'])
PlayContext = namedtuple('PlayContext', ['path', 'play_item', 'succeeded'])
def popup(text, time=5000, image=None):
    title = plugin.addon.getAddonInfo('name')
    icon = plugin.addon.getAddonInfo('icon')
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (title, text,
                        time, icon))

def get_connection():
    global connection
    
    if connection==None:   
        connected = False  
        # Create connection      
        try:
            connection = libsonic.Connection(
                baseUrl=Addon().get_setting('subsonic_url'),
                username=Addon().get_setting('username', convert=False),
                password=Addon().get_setting('password', convert=False),
                port=Addon().get_setting('port'),
                apiVersion=Addon().get_setting('apiversion'),
                insecure=Addon().get_setting('insecure'),
                legacyAuth=Addon().get_setting('legacyauth'),
                useGET=Addon().get_setting('useget'),
            )            
            connected = connection.ping()
        except:
            pass

        if connected==False:
            popup('Connection error')
            return False

    return connection

@plugin.action()
def root(params):
    
    # get connection
    connection = get_connection()
    
    if connection==False:
        return
    
    listing = []

    menus = {
        'folders': {
            'name':     Addon().get_localized_string(30038),
            'callback': 'browse_folders',
            'thumb': None
        },
        'library': {
            'name':     Addon().get_localized_string(30019),
            'callback': 'browse_library',
            'thumb': None
        },
        'albums': {
            'name':     Addon().get_localized_string(30020),
            'callback': 'menu_albums',
            'thumb': None
        },
        'tracks': {
            'name':     Addon().get_localized_string(30021),
            'callback': 'menu_tracks',
            'thumb': None
        },
        'playlists': {
            'name':     Addon().get_localized_string(30022),
            'callback': 'list_playlists',
            'thumb': None
        },
        'search': {
            'name':     Addon().get_localized_string(30039),
            'callback': 'search',
            'thumb': None
        },  
        'searchalbum': {
            'name':     Addon().get_localized_string(30045),
            'callback': 'search_album',
            'thumb': None
        },  
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

    add_directory_items(create_listing(
        listing,
        sort_methods = None,
    ))

@plugin.action()
def menu_albums(params):
    
    # get connection
    connection = get_connection()
    
    if connection==False:
        return
    
    listing = []

    menus = {
        'albums_newest': {
            'name':     Addon().get_localized_string(30023),
            'thumb':    None,
            'args':     {"ltype": "newest"}
        },
        'albums_frequent': {
            'name':     Addon().get_localized_string(30024),
            'thumb': None,
            'args':     {"ltype": "frequent"}
        },
        'albums_recent': {
            'name':     Addon().get_localized_string(30025),
            'thumb': None,
            'args':     {"ltype": "recent"}
        },
        'albums_random': {
            'name':     Addon().get_localized_string(30026),
            'thumb': None,
            'args':     {"ltype": "random"}
        },
        'albums_favorites': {
            'name':     Addon().get_localized_string(30027),
            'thumb': None,
            'args':     {"starred": True}
        }
    }

    # Iterate through albums

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

    add_directory_items(create_listing(
        listing,
    ))

@plugin.action()
def menu_tracks(params):
    
    # get connection
    connection = get_connection()
    
    if connection==False:
        return
    
    listing = []

    menus = {
        'tracks_starred': {
            'name':             Addon().get_localized_string(30036),
            'thumb':            None
        },
        'tracks_random': {
            'name':             Addon().get_localized_string(30037),
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
                menu_id=        menu_id
            )
        })  # Item label

    add_directory_items(create_listing(
        listing,
    ))

@plugin.action()
def browse_folders(params):
    # get connection
    connection = get_connection()
    
    if connection==False:
        return

    listing = []

    # Get items
    items = walk_folders()

    # Iterate through items
    for item in items:
        entry = {
            'label':    item.get('name'),
            'url':      plugin.get_url(
                        action=         'browse_indexes',
                        folder_id=      item.get('id'),
                        menu_id=        params.get('menu_id')

            )
        }
        listing.append(entry)

    if len(listing) == 1:
        plugin.log('One single Media Folder found; do return listing from browse_indexes()...')
        return browse_indexes(params)
    else:
        add_directory_items(create_listing(listing))

@plugin.action()
def browse_indexes(params):
    # get connection
    connection = get_connection()
    
    if connection==False:
        return

    listing = []
    
    # Get items 
    # optional folder ID
    folder_id = params.get('folder_id')
    items = walk_index(folder_id)

    # Iterate through items
    for item in items:
        entry = {
            'label':    item.get('name'),
            'url':      plugin.get_url(
                        action=     'list_directory',
                        id=         item.get('id'),
                        menu_id=    params.get('menu_id')
            )
        }
        listing.append(entry)
        
    add_directory_items(create_listing(
        listing
    ))

@plugin.action()
def list_directory(params):
    # get connection
    connection = get_connection()
    merge_artist = Addon().get_setting('merge')
    
    if connection==False:
        return

    listing = []
    
    # Get items
    id = params.get('id')
    items = walk_directory(id, merge_artist)

    # Iterate through items
    for item in items:
        
        #is a directory
        if (item.get('isDir')==True):
            entry = {
                'label':    item.get('title'),
                'url':      plugin.get_url(
                            action=     'list_directory',
                            id=         item.get('id'),
                            menu_id=    params.get('menu_id')
                )
            }
        else:
            entry = get_entry_track(item,params)
        

        listing.append(entry)
        
    add_directory_items(create_listing(
        listing
    ))

@plugin.action()
def browse_library(params):
    """
    List artists from the library (ID3 tags)
    """
    
    # get connection
    connection = get_connection()
    
    if connection==False:
        return

    listing = []

    # Get items
    items = walk_artists()

    # Iterate through items

    for item in items:
        entry = get_entry_artist(item,params)

        #context menu actions
        context_actions = []
        if can_star('artist',item.get('id')):
            action_star =  context_action_star('artist',item.get('id'))
            context_actions.append(action_star)
        
        if len(context_actions) > 0:
            entry['context_menu'] = context_actions
        
        listing.append(entry)
 
    add_directory_items(create_listing(
        listing,
        cache_to_disk = True, #cache this view to disk.
        sort_methods = get_sort_methods('artists',params), #he list of integer constants representing virtual folder sort methods.
        content = 'artists' #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    ))

@plugin.action()
def list_albums(params):
    
    """
    List albums from the library (ID3 tags)
    """
    
    listing = []
    
    # get connection
    connection = get_connection()
    
    if connection==False:
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
    if 'artist_id' in params:
        generator = walk_artist(params.get('artist_id'))
    else:
        generator = walk_albums(**query_args)
    
    #make a list out of the generator so we can iterate it several times
    items = list(generator)
    
    #check if there==only one artist for this album (and then hide it)
    artists = [item.get('artist',None) for item in items]
    if len(artists) <= 1:
        params['hide_artist']   = True

    # Iterate through items
    for item in items:
        album = get_entry_album(item, params)
        listing.append(album)
        
     # Root menu
    link_root = navigate_root()
    listing.append(link_root)

    if 'starred' in query_args:
        if len(items) == albums_per_page:
            link_next = navigate_next(params)
            listing.append(link_next)
    else:
        if not 'artist_id' in params:
            # Pagination if we've not reached the end of the lsit
            # if type(items) != type(True): TO FIX
            link_next = navigate_next(params)
            listing.append(link_next)

    add_directory_items(create_listing(
        listing,
        cache_to_disk = True, #cache this view to disk.
        sort_methods = get_sort_methods('albums',params), 
        content = 'albums' #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    ))

@plugin.action()
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
    
    if connection==False:
        return

    # Album
    if 'album_id' in params:
        generator = walk_album(params['album_id'])
        
    # Playlist
    elif 'playlist_id' in params:
        generator = walk_playlist(params['playlist_id'])
        
        #TO FIX
        #tracknumber = 0
        #for item in items:
        #    tracknumber += 1
        #    items[item]['tracknumber'] = tracknumber
        
    # Starred
    elif menu_id == 'tracks_starred':
        generator = walk_tracks_starred()
        
    
    # Random
    elif menu_id == 'tracks_random':
        generator = walk_tracks_random(**query_args)
    # Filters
    #else:
        #TO WORK
        
    #make a list out of the generator so we can iterate it several times
    items = list(generator)

    #check if there==only one artist for this album (and then hide it)
    artists = [item.get('artist',None) for item in items]
    if len(artists) <= 1:
        params['hide_artist']   = True
    
    #update stars
    if menu_id == 'tracks_starred':
        ids_list = [item.get('id') for item in items]
        #stars_local_update(ids_list)
        cache_refresh(True)

    # Iterate through items
    key = 0;
    for item in items:
        track = get_entry_track(item,params)
        listing.append(track)
        key +=1
        
    # Root menu
    #link_root = navigate_root()
    #listing.append(link_root)
        
    # Pagination if we've not reached the end of the lsit
    # if type(items) != type(True): TO FIX
    #link_next = navigate_next(params)
    #listing.append(link_next)

    add_directory_items(create_listing(
        listing,
        sort_methods=       get_sort_methods('tracks',params),
        content =           'songs' #string - current plugin content, e.g. ‘movies’ or ‘episodes’.
    ))

@plugin.action()
def list_playlists(params):
    
    # get connection
    connection = get_connection()
    
    if connection==False:
        return

    listing = []

    # Get items
    items = walk_playlists()

    # Iterate through items

    for item in items:
        entry = get_entry_playlist(item,params)
        listing.append(entry)
        
    add_directory_items(create_listing(
        listing,
        sort_methods = get_sort_methods('playlists',params), #he list of integer constants representing virtual folder sort methods.
    ))

@plugin.action()
def search(params):

    dialog = xbmcgui.Dialog()
    d = dialog.input(Addon().get_localized_string(30039), type=xbmcgui.INPUT_ALPHANUM)

    listing = []

    if d:
        # get connection
        connection = get_connection()

        if connection == False:
            return

        # Get items
        items = connection.search2(query=d)
        # Iterate through items
        songs = items.get('searchResult2').get('song')
        if songs:
            for item in songs:
                entry = get_entry_track( item, params)
                listing.append(entry)

    if len(listing) == 0:
        plugin.log('No songs found; do return listing from browse_indexes()...')
        return browse_indexes(params)
    else:
        add_directory_items(create_listing(listing))


@plugin.action()
def search_album(params):

    dialog = xbmcgui.Dialog()
    d = dialog.input(Addon().get_localized_string(30045), type=xbmcgui.INPUT_ALPHANUM)

    listing = []

    if d:
        # get connection
        connection = get_connection()
        if connection==False:
            return
        # Get items, we are only looking for albums here
        # so artistCount and songCount is set to 0
        items = connection.search2(query=d, artistCount=0, songCount=0)
        # Iterate through items
    
        album_list = items.get('searchResult2').get('album')
        if album_list:
            for item in items.get('searchResult2').get('album'):
                entry = get_entry_album( item, params)
                listing.append(entry)

    # I believe it is ok to return an empty listing if
    # the search gave no result
    # maybe inform the user?
    if len(listing) == 0:
        plugin.log('No albums found; do return listing from browse_indexes()...')
        return browse_indexes(params)
    else:
        add_directory_items(create_listing(listing))


@plugin.action()
def play_track(params):
    
    id = params['id']
    plugin.log('play_track #' + id);
    
    # get connection
    connection = get_connection()
    
    if connection==False:
        return

    url = connection.streamUrl(sid=id,
        maxBitRate=Addon().get_setting('bitrate_streaming'),
        tformat=Addon().get_setting('transcode_format_streaming')
    )

    #return url
    _set_resolved_url(resolve_url(url))

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
    
    if connection==False:
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

    if did_action:
        
        if unstar:
            message = Addon().get_localized_string(30031)
            plugin.log('Unstarred %s #%s' % (type,json.dumps(ids)))
        else: #star
            message = Addon().get_localized_string(30032)
            plugin.log('Starred %s #%s' % (type,json.dumps(ids)))
            
        #stars_local_update(ids,unstar)
        cache_refresh(True)
       
        popup(message)
            
        #TO FIX clear starred lists caches ?
        #TO FIX refresh current list after star set ?
        
    else:
        if unstar:
            plugin.log_error('Unable to unstar %s #%s' % (type,json.dumps(ids)))
        else:
            plugin.log_error('Unable to star %s #%s' % (type,json.dumps(ids)))

    #return did_action
    return    

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

def get_entry_playlist(item,params):
    image = connection.getCoverArtUrl(item.get('coverArt'))
    return {
        'label':    item.get('name'),
        'thumb':    image,
        'fanart':   image,
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
    }

def get_artist_info(artist_id, forced=False):
    print("Updating artist info for id: %s"%(artist_id))
    popup("Updating artist info\nplease wait")
    last_update = 0
    artist_info = {}
    cache_file = 'ar-%s'%hashlib.md5(artist_id.encode('utf-8')).hexdigest()
    with plugin.get_storage(cache_file) as storage:
        try:
            last_update = storage['updated']
        except KeyError as e:
            plugin.log("Artist keyerror, is this a new cache file? %s"%cache_file)    
        if(time.time()-last_update>(random.randint(1,111)*360) or forced):
            plugin.log("Artist cache expired, updating %s elapsed vs random %s forced %s"%(int(time.time()-last_update),(random.randint(1,111)*3600), forced))
            try:
                artist_info = connection.getArtistInfo2(artist_id).get('artistInfo2')
                storage['artist_info'] = artist_info
                storage['updated']=time.time()
            except AttributeError as e:
                plugin.log("Attribute error, probably couldn't find any info")
        else:
            print("Cache ok for %s retrieving"%artist_id)
            artist_info = storage['artist_info']
    return artist_info

def get_entry_artist(item,params):
    image = connection.getCoverArtUrl(item.get('coverArt'))
    #artist_info = get_artist_info(item.get('id'))
    #artist_bio = artist_info.get('biography')
    #fanart = artist_info.get('largeImageUrl')
    fanart = image
    return {
        'label':    get_starred_label(item.get('id'),item.get('name')),
	'label2': "test label",
	'offscreen': True,
        'thumb':    image,
        'fanart':   fanart,
        'url':      plugin.get_url(
                        action=     'list_albums',
                        artist_id=  item.get('id'),
                        menu_id=    params.get('menu_id')
                    ),
        'info': {
            'music': { ##http://romanvm.github.io/Kodistubs/_autosummary/xbmcgui.html#xbmcgui.ListItem.setInfo
                'count':    item.get('albumCount'),
                'artist':   item.get('name'),
		        #'title':    "testtitle",
		        #'album':    "testalbum",
		        #'comment':  "testcomment"
                #'title':    artist_bio
            }
        }
    }

def get_entry_album(item, params):
    
    image = connection.getCoverArtUrl(item.get('coverArt'))

    entry = {
        'label':    get_entry_album_label(item,params.get('hide_artist',False)),
        'thumb':    image,
        'fanart':   image,
        'url': plugin.get_url(
            action=         'list_tracks',
            album_id=       item.get('id'),
            hide_artist=    item.get('hide_artist'),
            menu_id=        params.get('menu_id')
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
        action_star =  context_action_star('album',item.get('id'))
        context_actions.append(action_star)

    if can_download('album',item.get('id')):
        action_download =  context_action_download('album',item.get('id'))
        context_actions.append(action_download)

    if len(context_actions) > 0:
        entry['context_menu'] = context_actions

    return entry

def get_entry_track(item,params):
    menu_id = params.get('menu_id')
    image = connection.getCoverArtUrl(item.get('coverArt'))

    entry = {
        'label':    get_entry_track_label(item,params.get('hide_artist')),
        'thumb':    image,
        'fanart':   image,
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
            'date':         item.get('created')
            }
        }
    }
    
    #context menu actions
    context_actions = []

    if can_star('track',item.get('id')):
        action_star =  context_action_star('track',item.get('id'))
        context_actions.append(action_star)

    if can_download('track',item.get('id')):
        action_download =  context_action_download('track',item.get('id'))
        context_actions.append(action_download)

    if len(context_actions) > 0:
        entry['context_menu'] = context_actions
    

    return entry

def get_starred_label(id,label):
    if is_starred(id):
        label = '[COLOR=FF00FF00]%s[/COLOR]' % label
    return label

def is_starred(id):
    starred = stars_cache_get()
    #id = int(id)
    if id in starred:
        return True
    else:
        return False

def get_entry_track_label(item,hide_artist = False):
    if hide_artist:
        label = item.get('title', '<Unknown>')
    else:
        label = '%s - %s' % (
            item.get('artist', '<Unknown>'),
            item.get('title', '<Unknown>')
        )

    return get_starred_label(item.get('id'),label)

def get_entry_album_label(item,hide_artist = False):
    if hide_artist:
        label = item.get('name', '<Unknown>')
    else:
        label = '%s - %s' % (item.get('artist', '<Unknown>'),
                             item.get('name', '<Unknown>'))
    return get_starred_label(item.get('id'),label)

def get_sort_methods(type,params):
    #sort method for list types
    #https://github.com/xbmc/xbmc/blob/master/xbmc/SortFileItem.h
    #TO FIX _DATE or _DATEADDED ?
    
    #TO FIX
    #actually it seems possible to 'restore' the default sorting (by labels)
    #so our starred items don't get colorized.
    #so do not sort stuff
    #see http://forum.kodi.tv/showthread.php?tid=293037
    return []

    sortable = [
        xbmcplugin.SORT_METHOD_NONE,
        xbmcplugin.SORT_METHOD_LABEL,
        xbmcplugin.SORT_METHOD_UNSORTED
    ]
    
    if type=='artists':
        
        artists = [
            xbmcplugin.SORT_METHOD_ARTIST
        ]

        sortable = sortable + artists
        
    elif type=='albums':
        
        albums = [
            xbmcplugin.SORT_METHOD_ALBUM,
            xbmcplugin.SORT_METHOD_DURATION,
            xbmcplugin.SORT_METHOD_DATE,
            #xbmcplugin.SORT_METHOD_YEAR
        ]
        
        if not params.get('hide_artist',False):
            albums.append(xbmcplugin.SORT_METHOD_ARTIST)

        sortable = sortable + albums
        
    elif type=='tracks':

        tracks = [
            xbmcplugin.SORT_METHOD_TITLE,
            xbmcplugin.SORT_METHOD_ALBUM,
            xbmcplugin.SORT_METHOD_TRACKNUM,
            #xbmcplugin.SORT_METHOD_YEAR,
            xbmcplugin.SORT_METHOD_GENRE,
            xbmcplugin.SORT_METHOD_SIZE,
            xbmcplugin.SORT_METHOD_DURATION,
            xbmcplugin.SORT_METHOD_DATE,
            xbmcplugin.SORT_METHOD_BITRATE
        ]
        
        if not params.get('hide_artist',False):
            tracks.append(xbmcplugin.SORT_METHOD_ARTIST)
        
        if params.get('playlist_id',False):
            xbmcplugin.SORT_METHOD_PLAYLIST_ORDER,
        
        
        sortable = sortable + tracks
        
    elif type=='playlists':

        playlists = [
            xbmcplugin.SORT_METHOD_TITLE,
            xbmcplugin.SORT_METHOD_DURATION,
            xbmcplugin.SORT_METHOD_DATE
        ]
        
        sortable = sortable + playlists

    return sortable
    
def cache_refresh(forced=False):
    global local_starred
    #cachetime = 5
    last_update = 0
    with plugin.get_storage() as storage:
        #storage['starred_ids'] = starred
        try:
            last_update = storage['updated']
        except KeyError as e:
            plugin.log("keyerror, is this a new cache file?")    
        if(time.time()-(cachetime*60)>last_update) or forced:
            plugin.log("Cache expired, updating %s %s %s forced %s"%(time.time(),cachetime*60,last_update, forced))
            generator = walk_tracks_starred()
            items = list(generator)
            ids_list = [item.get('id') for item in items]
            #plugin.log("Retreived from server: %s"%ids_list)
            storage['starred_ids'] = ids_list
            storage['updated']=time.time()
            plugin.log("cache_refresh checking length of load to local %s items"%len(ids_list))
            local_starred = ids_list
        else:
            #plugin.log("Cache fresh %s %s %s forced %s remaining %s"%(time.time(),cachetime*60,last_update, forced, time.time()-(cachetime*60)-last_update))
            pass
        if(len(local_starred)==0):
            local_starred = storage['starred_ids']
    #plugin.log("cache_refresh returning %s items"%len(local_starred))
    return       

def stars_cache_get():
    global local_starred
    cache_refresh()    
    return local_starred

def navigate_next(params):
  
    page =      int(params.get('page',1))
    page +=     1
    
    title =  Addon().get_localized_string(30029) +"(%d)" % (page)

    return {
        'label':    title,
        'url':      plugin.get_url(
                        action=         params.get('action',None),
                        page=           page,
                        query_args=     params.get('query_args',None)
                    )
    }

def navigate_root():
    return {
        'label':    Addon().get_localized_string(30030),
        'url':      plugin.get_url(action='root')
    }

#converts a date string from eg. '2012-04-17T19:53:44' to eg. '17.04.2012'
def convert_date_from_iso8601(iso8601):
    format = "%Y-%m-%dT%H:%M:%S"    
    try:
        date_obj = datetime.strptime(iso8601.split(".")[0], format)
    except TypeError:
        date_obj = datetime(*(time.strptime(iso8601.split(".")[0], format)[0:6]))
    return date_obj.strftime('%d.%m.%Y')

def context_action_star(type,id):
    
    starred = is_starred(id)

    if not starred:

        label = Addon().get_localized_string(30033)
            
    else:
        
        #Should be available only in the stars lists;
        #so we don't have to fetch the starred status for each item
        #(since it is not available into the XML response from the server)

        label = Addon().get_localized_string(30034)
    
    xbmc.log('Context action star returning RunPlugin(%s)' % plugin.get_url(action='star_item',type=type,ids=id,unstar=starred),xbmc.LOGDEBUG)
    return (
        label, 
        'RunPlugin(%s)' % plugin.get_url(action='star_item',type=type,ids=id,unstar=starred)
    )

#Subsonic API says this==supported for artist,tracks and albums,
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
    
    label = Addon().get_localized_string(30035)
    
    return (
        label, 
        'RunPlugin(%s)' % plugin.get_url(action='download_item',type=type,id=id)
    )

def can_download(type,id = None):
    if id==None:
        return False
    
    if type == 'track':
        return True
    elif type == 'album':
        return True
    
def download_tracks(ids):

    #popup==fired before, in download_item
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
    
    if connection==False:
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
        progressdialog.update(pc_progress, 'Getting track informations...',get_entry_track_label(track))

        track_path_relative = track.get("path", None).encode('utf8', 'replace') # 'Radiohead/Kid A/Idioteque.mp3'
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
    
    if connection==False:
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

def create_listing(listing, succeeded=True, update_listing=False, cache_to_disk=False, sort_methods=None,view_mode=None, content=None, category=None):
        return ListContext(listing, succeeded, update_listing, cache_to_disk,sort_methods, view_mode, content, category)

def resolve_url(path='', play_item=None, succeeded=True):
    """
    Create and return a context dict to resolve a playable URL
    :param path: the path to a playable media.
    :type path: str or unicode
    :param play_item: a dict of item properties as described in the class docstring.
        It allows to set additional properties for the item being played, like graphics, metadata etc.
        if ``play_item`` parameter==present, then ``path`` value==ignored, and the path must be set via
        ``'path'`` property of a ``play_item`` dict.
    :type play_item: dict
    :param succeeded: if ``False``, Kodi won't play anything
    :type succeeded: bool
    :return: context object containing necessary parameters
        for Kodi to play the selected media.
    :rtype: PlayContext
    """
    return PlayContext(path, play_item, succeeded)

def create_list_item(item):
    """
    Create an :class:`xbmcgui.ListItem` instance from an item dict
    :param item: a dict of ListItem properties
    :type item: dict
    :return: ListItem instance
    :rtype: xbmcgui.ListItem
    """
    major_version = xbmc.getInfoLabel('System.BuildVersion')[:2]
    if major_version >= '18':
        list_item = xbmcgui.ListItem(label=item.get('label', ''),
                                     label2=item.get('label2', ''),
                                     path=item.get('path', ''),
                                     offscreen=item.get('offscreen', False))


    art = item.get('art', {})
    art['thumb'] = item.get('thumb', '')
    art['icon'] = item.get('icon', '')
    art['fanart'] = item.get('fanart', '')
    item['art'] = art
    cont_look = item.get('content_lookup')
    if cont_look is not None:
        list_item.setContentLookup(cont_look)
    if item.get('art'):
        list_item.setArt(item['art'])
    if item.get('stream_info'):
        for stream, stream_info in item['stream_info'].items():
            list_item.addStreamInfo(stream, stream_info)
    if item.get('info'):
        for media, info in item['info'].items():
            list_item.setInfo(media, info)
    if item.get('context_menu') is not None:
        list_item.addContextMenuItems(item['context_menu'])
    if item.get('subtitles'):
        list_item.setSubtitles(item['subtitles'])
    if item.get('mime'):
        list_item.setMimeType(item['mime'])
    if item.get('properties'):
        for key, value in item['properties'].items():
            list_item.setProperty(key, value)
    if major_version >= '17':
        cast = item.get('cast')
        if cast is not None:
            list_item.setCast(cast)
        db_ids = item.get('online_db_ids')
        if db_ids is not None:
            list_item.setUniqueIDs(db_ids)
        ratings = item.get('ratings')
        if ratings is not None:
            for rating in ratings:
                list_item.setRating(**rating)
    return list_item

def _set_resolved_url(context):
    plugin.log_debug('Resolving URL from {0}'.format(str(context)))
    if context.play_item==None:
        list_item = xbmcgui.ListItem(path=context.path)
    else:
        list_item = self.create_list_item(context.play_item)
    xbmcplugin.setResolvedUrl(plugin.handle, context.succeeded, list_item)


def add_directory_items(context):
    plugin.log_debug('Creating listing from {0}'.format(str(context)))
    if context.category is not None:
        xbmcplugin.setPluginCategory(plugin.handle, context.category)
    if context.content is not None:
        xbmcplugin.setContent(plugin.handle, context.content)  # This must be at the beginning
    for item in context.listing:
        is_folder = item.get('is_folder', True)
        if item.get('list_item') is not None:
            list_item = item['list_item']
        else:
            list_item = create_list_item(item)
            if item.get('is_playable'):
                list_item.setProperty('IsPlayable', 'true')
                is_folder = False
        xbmcplugin.addDirectoryItem(plugin.handle, item['url'], list_item, is_folder)
    if context.sort_methods is not None:
        if isinstance(context.sort_methods, (int, dict)):
            sort_methods = [context.sort_methods]
        elif isinstance(context.sort_methods, (tuple, list)):
            sort_methods = context.sort_methods
        else:
            raise TypeError(
                'sort_methods parameter must be of int, dict, tuple or list type!')
        for method in sort_methods:
            if isinstance(method, int):
                xbmcplugin.addSortMethod(plugin.handle, method)
            elif isinstance(method, dict):
                xbmcplugin.addSortMethod(plugin.handle, **method)
            else:
                raise TypeError(
                    'method parameter must be of int or dict type!')

    xbmcplugin.endOfDirectory(plugin.handle,
                              context.succeeded,
                              context.update_listing,
                              context.cache_to_disk)
    if context.view_mode is not None:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(context.view_mode))

def walk_index(folder_id=None):
    """
    Request Subsonic's index and iterate each item.
    """
    response = connection.getIndexes(folder_id)
    plugin.log("Walk index resp: %s"%response)
    try:
        for index in response["indexes"]["index"]:
            for artist in index["artist"]:
                plugin.log("artist: %s"%artist)
                yield artist
    except KeyError:
        yield from ()            

def walk_playlists():
    """
    Request Subsonic's playlists and iterate over each item.
    """
    response = connection.getPlaylists()
    try:
        for child in response["playlists"]["playlist"]:
            yield child
    except KeyError:
        yield from ()

def walk_playlist(playlist_id):
    """
    Request Subsonic's playlist items and iterate over each item.
    """
    response = connection.getPlaylist(playlist_id)
    try:
        for child in response["playlist"]["entry"]:
            yield child
    except KeyError:
        yield from ()

def walk_folders():
    response = connection.getMusicFolders()
    try:
        for child in response["musicFolders"]["musicFolder"]:
            yield child
    except KeyError:
        yield from ()

def walk_directory(directory_id, merge_artist = True):
    """
    Request a Subsonic music directory and iterate over each item.
    """
    response = connection.getMusicDirectory(directory_id)
   
    try:
        for child in response["directory"]["child"]:
            if merge_artist and child.get("isDir"):
                for child in walk_directory(child["id"], merge_artist):
                    yield child
            else:
                yield child
    except KeyError:
        yield from ()

def walk_artist(artist_id):
    """
    Request a Subsonic artist and iterate over each album.
    """

    response = connection.getArtist(artist_id)
    try:
        for child in response["artist"]["album"]:
            yield child
    except KeyError:
        yield from ()

def walk_artists():
    """
    (ID3 tags)
    Request all artists and iterate over each item.
    """
    response = connection.getArtists()
    try:
        for index in response["artists"]["index"]:
            for artist in index["artist"]:
                yield artist
    except KeyError:
        yield from ()

def walk_genres():
    """
    (ID3 tags)
    Request all genres and iterate over each item.
    """
    response = connection.getGenres()
    try:
        for genre in response["genres"]["genre"]:
            yield genre
    except KeyError:
        yield from ()

def walk_albums(ltype=None, size=None, fromYear=None,toYear=None, genre=None, offset=None, starred=None):
    """
    (ID3 tags)
    Request all albums for a given genre and iterate over each album.
    """

    if starred:
        response = connection.getStarred2()
        if not response['starred2']['album']: return
        albums = response['starred2']['album']
        offset = 0 if not offset else offset
        if offset >= len(albums): return
        albums_per_page = int(Addon().get_setting('albums_per_page'))
        upper = min(len(albums), offset + albums_per_page)
        albums = albums[offset:upper]
        for album in albums:
            yield album
    else:
        if ltype == 'byGenre' and genre is None:
            return
        
        if ltype == 'byYear' and (fromYear is None or toYear is None):
            return

        response = connection.getAlbumList2(
            ltype=ltype, size=size, fromYear=fromYear, toYear=toYear,genre=genre, offset=offset)

        if not response["albumList2"]["album"]:
            return

        for album in response["albumList2"]["album"]:
            yield album


def walk_album(album_id):
    """
    (ID3 tags)
    Request an album and iterate over each item.
    """
    response = connection.getAlbum(album_id)
    try:
        for song in response["album"]["song"]:
            yield song
    except KeyError:
        yield from ()

def walk_tracks_random(size=None, genre=None, fromYear=None,toYear=None):
    """
    Request random songs by genre and/or year and iterate over each song.
    """
    response = connection.getRandomSongs(
        size=size, genre=genre, fromYear=fromYear, toYear=toYear)
    try:
        for song in response["randomSongs"]["song"]:
            yield song
    except KeyError:
        yield from ()        

def walk_tracks_starred():
    """
    Request Subsonic's starred songs and iterate over each item.
    """
    response = connection.getStarred()
    try:
        for song in response["starred"]["song"]:
            yield song
    except KeyError:
        yield from ()

# Start plugin from within Kodi.
if __name__ == "__main__":
    # Map actions
    # Note that we map callable objects without brackets ()
    plugin.run()
