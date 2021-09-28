import sqlite3 as sql
import time

tbl_artist_info_ddl = str('CREATE TABLE artist_info ('
                            'artist_id                  TEXT NOT NULL PRIMARY KEY,'
                            'artist_name                TEXT,'
                            'artist_info                TEXT,'
                            'mb_artist_id               TEXT,'
                            'image_url                  TEXT,'
                            'wikidata_url               TEXT,'
                            'wikipedia_url              TEXT,'
                            'wikipedia_image            TEXT,'
                            'wikipedia_extract          TEXT,'
                            'last_update                TEXT);')

class SQLiteDatabase(object):
    def __init__(self, db_filename):
        print("Init %s"%db_filename) 
        self.db_filename = db_filename
        self.conn = None
    
        self.connect()

    def connect(self):
        try:
            #xbmc.log("Trying connection to the database %s"%self.db_filename, xbmc.LOGINFO)
            print("Trying connection to the database %s"%self.db_filename)
            self.conn = sql.connect(self.db_filename)
            cursor = self.conn.cursor()
            cursor.execute(str('SELECT SQLITE_VERSION()'))
            #xbmc.log("Connection %s was successful %s"%(self.db_filename, cursor.fetchone()[0]), xbmc.LOGINFO)
            print("Connection %s was successful %s"%(self.db_filename, cursor.fetchone()[0]))
            cursor.row_factory = lambda cursor, row: row[0]
            cursor.execute(str('SELECT name FROM sqlite_master WHERE type=\'table\' ''AND name NOT LIKE \'sqlite_%\''))
            list_tables = cursor.fetchall()
            if not list_tables:
                # If no tables exist create a new one
                #xbmc.log("Creating Subsonic local DB", xbmc.LOGINFO)
                print("Creating Subsonic local DB")
                cursor.execute(tbl_artist_info_ddl)
        except sql.Error as e:
            #xbmc.log("SQLite error %s"%e.args[0], xbmc.LOGINFO)
            print("SQLite error %s"%e.args[0])

    def get_cursor(self):
        return self.conn.cursor()

    def run_query(self, query, params=None, cursor=None):
        #print("Processing query %s params %s"%(str(query),str(params)))      
        try:
            if cursor is None:
                cursor = self.get_cursor()
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            #print("%s rows affected"%cursor.rowcount)
            return cursor
        except sql.Error as e:
            print("SQLite error %s"%e.args[0])
        except ValueError:
            pass
            #print("Error query %s"%str(query))  
            #print("Error query type %s"%type(query))
            #print("Error params %s"%str(params))  
            #print("Error params type %s"%type(params))

    def get_record_age(self, artist_id):
        try:
            last_update = self.get_value(artist_id, 'last_update')
            record_age = round(time.time())-round(float(last_update[0][0]))
            return record_age
        except IndexError:
            print("No existing record for artist %s" % artist_id)
        except Exception as e:
            print("get_record_age failed %s" % e)
        return 0

    def get_artist_info(self, artist_id):   
        query = 'SELECT * FROM artist_info WHERE artist_id = ?'# %str(artist_id)
        params = [str(artist_id)]    
        cursor = self.run_query(query, params)
        return cursor.fetchall()

    def get_all(self):
        query = 'SELECT * FROM artist_info'
        #params = [str(artist_id)]    
        cursor = self.run_query(query)#, params)
        return cursor.fetchall()

    def update_value(self, artist_id, field_name, field_value):
        success = False
        query = 'UPDATE artist_info SET %s = ?, last_update = ? WHERE artist_id = ?' % str(field_name)        
        params = [str(field_value), str(time.time()), str(artist_id)] 
        cursor = self.run_query(query, params)
        if (cursor.rowcount == 0):
            query = 'INSERT OR IGNORE INTO artist_info (artist_id, %s, last_update) VALUES (?, ?, ?)' % str(field_name)        
            params = [str(artist_id), str(field_value), str(time.time())] 
            cursor = self.run_query(query, params)
        try:
            self.conn.commit()
            success = True
        except Exception as e:
            print("Exception %s"%e)                
            pass
        return success

    def get_value(self, artist_id, field_name):   
        query = 'SELECT %s FROM artist_info WHERE artist_id = ?' % str(field_name)
        params = [str(artist_id)]    
        cursor = self.run_query(query, params)
        return cursor.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()
        
