import re
import xbmc
import xbmcvfs
import os
import xbmcaddon
import time
import random

# Add the /lib folder to sys
sys.path.append(xbmcvfs.translatePath(os.path.join(xbmcaddon.Addon("plugin.audio.subsonic").getAddonInfo("path"), "lib")))

import dbutils
import libsonic
import musicbrainz

connection = None
db = None
mb = None

serviceEnabled = True

refresh_age = 3600     #multiple of random to age info records - needs some validation
check_freq = 30   #How often to run a refresh cycle - needs some validation

db_filename = "subsonic_sqlite.db"

last_db_check = 0
current_artist_index = 0

from simpleplugin import Plugin
from simpleplugin import Addon

# Create plugin instance
plugin = Plugin()

try:
    enhancedInfo = Addon().get_setting('enhanced_info')
except:
    enhancedInfo = False

try:
    scrobbleEnabled = Addon().get_setting('scrobble')
except:
    scrobbleEnabled = False

scrobbled = False

def check_address_format():
    address = Addon().get_setting('subsonic_url')
    port = Addon().get_setting('port')
    if len(address.split(":"))>2:
        found_port = address.split(":")[2]            
        plugin.log("Found port %s in address %s, splitting"%(found_port, address))
        plugin.log("Changing port from %s to %s"%(port, found_port))
        Addon().set_setting('port', int(found_port))
        Addon().set_setting('subsonic_url', "%s:%s"%(address.split(":")[0],address.split(":")[1]))
        
def popup(text, time=5000, image=None):
    title = plugin.addon.getAddonInfo('name')
    icon = plugin.addon.getAddonInfo('icon')
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (title, text, time, icon))

def get_connection():
    global connection    
    if connection==None:   
        connected = False    
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
                appName="Kodi-Subsonic",
            )            
            connected = connection.ping()
        except:
            pass

        if connected==False:
            popup('Connection error')
            return False

    return connection

def get_mb():
    global mb
    mb = musicbrainz.MBConnection()
    return mb

def get_db():
    global db
    db_path = os.path.join(plugin.profile_dir, db_filename)   
    plugin.log("Getting DB %s"%db_path)  
    try:
        db = dbutils.SQLiteDatabase(db_path)
    except Exception as e:
        plugin.log("Connecting to DB failed: %s"%e)    
    return db   

def refresh_artist(artist_id):
    db = get_db()
    connection = get_connection()
    artist = connection.getArtist(artist_id)#['subsonic-response']
    artist_name = artist['artist']['name']
    db.update_value(artist_id, 'artist_name', artist_name)
    artist_info = connection.getArtistInfo2(artist_id)
    try:
        artist_info = artist_info['artistInfo2']['biography']
        #pattern = '<a target=\'_blank\' href="https://www.last.fm/music/Afrojack">Read more on Last.fm</a>
        artist_info = re.sub('<a.*?</a>', '', artist_info)
        plugin.log("subbed: %s"%artist_info)
    except:
        artist_info = ""
    if(enhancedInfo):
        mb = get_mb()        
        mb_artist_id = mb.get_artist_id(artist_name)
        artist_image_url = mb.get_artist_image(mb_artist_id)
        wikipedia_url = mb.get_artist_wikpedia(mb_artist_id)
        artist_wiki_extract = mb.get_wiki_extract(wikipedia_url)
        wikipedia_image = mb.get_wiki_image(wikipedia_url)
        db.update_value(artist_id, 'artist_info', artist_info)
        db.update_value(artist_id, 'mb_artist_id', mb_artist_id)
        db.update_value(artist_id, 'image_url', artist_image_url)
        db.update_value(artist_id, 'wikipedia_url', wikipedia_url)
        db.update_value(artist_id, 'wikipedia_extract', artist_wiki_extract)
        db.update_value(artist_id, 'wikipedia_image', wikipedia_image)

def check_db_status():
    global last_db_check
    global current_artist_index 
    try:             
        if(time.time()-check_freq > last_db_check): #Won't check on every run uses check_freq
            plugin.log("DB check starting %s %s" % (time.time(), last_db_check))
            db = get_db()
            connection = get_connection()
            response = connection.getArtists()
            current_index_content = response["artists"]["index"][current_artist_index] #Completes refresh for alpha index
            plugin.log("Starting info load for index %s"%current_index_content['name'])
            for artist in current_index_content["artist"]:
                artist_id = artist['id']
                record_age = db.get_record_age(artist_id) 
                plugin.log("Record age %s vs %s for %s"%(record_age, (random.randint(1,111)*refresh_age), artist_id))
                if(not record_age or (record_age > (random.randint(1,111)*refresh_age))):
                    plugin.log("Record age %s vs %s for %s"%(record_age, (random.randint(1,111)*refresh_age), artist_id)) 
                    plugin.log("Refreshing %s" % (artist_id))
                    refresh_artist(artist_id)
                    plugin.log("Refresh complete for %s" % (artist_id))
            plugin.log("Finished info loading for index %s"%current_index_content['name'])
            current_artist_index+=1
            if(current_artist_index>=len(response["artists"]["index"])):current_artist_index=0
            last_db_check = time.time()
    except Exception as e:
        plugin.log("Refresh check failed %s"%e)

    return

def check_player_status():
    global scrobbled
    if (scrobbleEnabled and xbmc.getCondVisibility("Player.HasMedia")):
        try:             
            currentFileName = xbmc.getInfoLabel("Player.Filenameandpath")
            currentFileProgress = xbmc.getInfoLabel("Player.Progress")   
            pattern = re.compile(r'plugin:\/\/plugin\.audio\.subsonic\/\?action=play_track&id=(.*?)&')
            currentTrackId = re.findall(pattern, currentFileName)[0]                
            #xbmc.log("Name %s Id %s Progress %s"%(currentFileName,currentTrackId,currentFileProgress), xbmc.LOGDEBUG)                
            if (int(currentFileProgress)<50):
                scrobbled = False
            elif (int(currentFileProgress)>=50 and scrobbled == False):
                xbmc.log("Scrobbling Track Id %s"%(currentTrackId), xbmc.LOGDEBUG)
                success = scrobble_track(currentTrackId)
                if success:
                    scrobbled = True
            else:
                pass
        except IndexError:
            plugin.log ("Not a Subsonic track")
            scrobbled = True
        except Exception as e:
            xbmc.log("Subsonic scrobble check failed %e"%e, xbmc.LOGINFO)
    return                

def scrobble_track(track_id):
    connection = get_connection()
    if connection==False:
        return False
    res = connection.scrobble(track_id)
    #xbmc.log("response %s"%(res), xbmc.LOGINFO)
    if res['status'] == 'ok':
        popup("Scrobbled track")
        return True
    else:
        popup("Scrobble failed")
        xbmc.log("Scrobble failed", xbmc.LOGERROR)
        return False


if __name__ == '__main__':
    if serviceEnabled:  
        check_address_format()        
        monitor = xbmc.Monitor()
        xbmc.log("Subsonic service started", xbmc.LOGINFO)
        popup("Subsonic service started")
        while not monitor.abortRequested():
            if monitor.waitForAbort(10):
                break
            check_player_status()
            check_db_status()
    else:
        plugin.log("Subsonic service not enabled")
