import sys
sys.path.insert(0,'lib')
import dbutils
import libsonic
import time


db = None
connection = None

db_filename = "subsonic_sqlite.db"

def get_db():
    global db_filename    
    global db
    print("Getting DB %s"%db_filename)  
    try:
        db = dbutils.SQLiteDatabase(db_filename)
    except Exception as e:
        print("Connecting to DB failed: %s"%e)    
    return db

def get_connection():
    global connection
    
    if connection==None:   
        connected = False  
        # Create connection      
        try:
            connection = libsonic.Connection(
                baseUrl="http://192.168.25.16",
                username="warwick.harris",
                password="ducatiMonsterSoundsGreat$",
                port="4040",
                apiVersion="1.15.1",
                insecure=False,
                legacyAuth=False,
                useGET=False,
            )            
            connected = connection.ping()
        except:
            pass

        if connected==False:
            print('Connection error')
            return False

    return connection

db = get_db()
connection = get_connection()

#cursor = db.get_cursor()
#cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
#print(cursor.fetchall())
artist_id = 635
artist_info = connection.getArtistInfo2(artist_id)
#print("Artist info: %s"%artist_info)
print(db.update_artist(artist_id, artist_info, time.time()))
print(db.get_artist_info(artist_id))
print(db.update_artist(artist_id, "replace", time.time()))
print(db.get_artist_info(1))



db.close()
