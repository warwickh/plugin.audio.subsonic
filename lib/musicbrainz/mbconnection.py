import os
import json
import urllib.request
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import re

urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler))

class MBConnection(object):
    def __init__(self, lang = "en"):
        self._lang = lang        
        self._baseUrl = "https://musicbrainz.org/ws/2"
        self._wikipediaBaseUrl = "https://{}.wikipedia.org/wiki".format(self._lang)
        self._wikidataBaseUrl = "https://www.wikidata.org/wiki/Special:EntityData"
        self._opener = self._getOpener()

    def _getOpener(self):
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler)
        return opener

    def search(self, entity, query, limit=None, offset=None):
        viewName = '%s' % entity
        q = self._getQueryDict({'query': query, 'limit': limit, 'offset': offset})
        req = self._getRequest(self._baseUrl, viewName, q)
        res = self._doInfoReqXml(req)
        return res

    def get_wiki_extract(self, title):
        try:        
            if('http' in title):
                #accepts search text or full url https://en.wikipedia.org/wiki/Alex_Lloyd
                pattern = 'wikipedia.org/wiki/(.+)'
                title = re.search(pattern, title).group(1)
            viewName = 'api.php'
            q = self._getQueryDict({'format' : 'json', 'action' : 'query', 'prop' : 'extracts', 'redirects' : 1, 'titles' : title})
            req = self._getRequest(self._wikipediaBaseUrl[:-3], viewName, q, 'exintro&explaintext&')
            res = self._doInfoReqJson(req)
            pages = res['query']['pages']
            extract = list(pages.values())[0]['extract']
            return extract
        except Exception as e:
            print("get_artist_wikpedia failed %s"%e)
        return

#https://en.wikipedia.org/w/api.php?exintro&explaintext&format=json&action=query&prop=extracts&redirects=1&titles=%C3%89milie_Simon
    def get_wiki_image(self, title):
        try:
            if('http' in title):
                #accepts search text or full url https://en.wikipedia.org/wiki/Alex_Lloyd
                pattern = 'wikipedia.org/wiki/(.+)'
                title = re.search(pattern, title).group(1)
            viewName = 'api.php'
            q = self._getQueryDict({'format' : 'json', 'action' : 'query', 'prop' : 'pageimages', 'pithumbsize' : 800, 'titles' : title})
            req = self._getRequest(self._wikipediaBaseUrl[:-3], viewName, q)
            res = self._doInfoReqJson(req)
            pages = res['query']['pages']
            print(res['query']['pages'])
            image_url = list(pages.values())[0]['thumbnail']['source']
            return image_url
        except Exception as e:
            print("get_wiki_image failed %s"%e)
        return

    def get_artist_id(self, query):
        try:
            dres = self.search('artist', query)
            artist_list = dres.find('{http://musicbrainz.org/ns/mmd-2.0#}artist-list')
            artist = artist_list.find('{http://musicbrainz.org/ns/mmd-2.0#}artist') 
            return artist.attrib['id']
        except Exception as e:
            print("get_artist_id failed %s"%e)
        return

    def get_relation(self, artist_id, rel_type):
        try:
            viewName = 'artist/%s' % artist_id
            q = self._getQueryDict({'inc': "url-rels"})
            req = self._getRequest(self._baseUrl, viewName, q)
            res = self._doInfoReqXml(req)
            for relation in res.iter('{http://musicbrainz.org/ns/mmd-2.0#}relation'):
                if relation.attrib['type'] == rel_type:
                    return relation.find('{http://musicbrainz.org/ns/mmd-2.0#}target').text
        except Exception as e:
            print("get_artist_image failed %s"%e)
        return

    def get_artist_image(self, artist_id):
        try:
            image = self.get_relation(artist_id, 'image')       
            return image
        except Exception as e:
            print("get_artist_image failed %s"%e)
        return

    def get_artist_wikpedia(self, artist_id):   
        wikidata_url = self.get_relation(artist_id, 'wikidata') 
        pattern = 'www.wikidata.org/wiki/(Q\d+)'
        try:
            wikidata_ref = re.search(pattern, wikidata_url).group(1)
            viewName = '%s.rdf' % wikidata_ref
            q = self._getQueryDict({})
            req = self._getRequest(self._wikidataBaseUrl, viewName, q )
            res = self._doInfoReqXml(req)
            for item in res.iter('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description'):
                try:
                    url = item.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']
                    if self._wikipediaBaseUrl in url:
                        #print(urlencode(url))
                        #print((url.encode().decode('unicode-escape')))
                        return urllib.parse.unquote(url)
                except KeyError:
                    pass
        except Exception as e:
            print("get_artist_wikpedia failed %s"%e)
        return

    def _getQueryDict(self, d):
        """
        Given a dictionary, it cleans out all the values set to None
        """
        for k, v in list(d.items()):
            if v is None:
                del d[k]
        return d    

    def _getRequest(self, baseUrl, viewName, query={}, prefix=""):
        qdict = {}
        qdict.update(query)
        url = '%s/%s' % (baseUrl, viewName)
        if(prefix!='' or qdict!={}):
            url += "?%s%s" % (prefix, urlencode(qdict))
        print("UseGET URL %s" % (url))
        req = urllib.request.Request(url)
        return req

    def _doInfoReqXml(self, req):
        res = urllib.request.urlopen(req)
        data = res.read().decode('utf-8')   
        dres = ET.fromstring(data)
        return dres

    def _doInfoReqJson(self, req):
        res = urllib.request.urlopen(req)
        dres = json.loads(res.read().decode('utf-8'))
        return dres
