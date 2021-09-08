import re
import xbmc
import xbmcvfs
import os
import xbmcaddon
# Add the /lib folder to sys
sys.path.append(xbmcvfs.translatePath(os.path.join(xbmcaddon.Addon("plugin.audio.subsonic").getAddonInfo("path"), "lib")))

import libsonic

from simpleplugin import Plugin
from simpleplugin import Addon

# Create plugin instance
plugin = Plugin()
connection = None

scrobbleEnabled = Addon().get_setting('scrobble')
scrobbled = False

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

def scrobble_track(track_id):
    connection = get_connection()

    if connection==False:
        return False
    res = connection.scrobble(track_id)
    #xbmc.log("response %s"%(res), xbmc.LOGINFO)
    if res['status'] == 'ok':
        return True
    else:
        return False

if __name__ == '__main__':
    monitor = xbmc.Monitor()
    
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break
        if (xbmc.getCondVisibility("Player.HasMedia")):
            try:            
                if(scrobbleEnabled):           
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
            except Exception as e:
                xbmc.log("Script failed %e"%e, xbmc.LOGINFO)
        else:
            pass
            #xbmc.log("Playing stopped", xbmc.LOGINFO)

