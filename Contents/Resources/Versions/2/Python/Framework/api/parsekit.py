#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import plistlib, feedparser, sys


if sys.platform == 'win32':
  import socket
  GLOBAL_DEFAULT_TIMEOUT = socket._GLOBAL_DEFAULT_TIMEOUT
else:
  import httplib_new as httplib
  GLOBAL_DEFAULT_TIMEOUT = httplib._GLOBAL_DEFAULT_TIMEOUT

class Plist(Framework.bases.BaseHTTPKit):
  
  def ObjectFromString(self, text):
    return plistlib.readPlistFromString(text)
    
  def ObjectFromURL(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0):
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
    
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
        
    user_headers = self._add_headers(headers)
    return self.ObjectFromString(self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, errors, timeout=timeout, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content)
    
  def StringFromObject(self, obj):
    return plistlib.writePlistToString(obj)



class JSON(Framework.bases.BaseHTTPKit):
  
  def ObjectFromString(self, string, encoding=None):
    return self._core.data.json.from_string(string, encoding)
  
  def ObjectFromURL(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0):
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
    
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
      
    user_headers = self._add_headers(headers)
    return self.ObjectFromString(self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, encoding, errors, timeout=timeout, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content, encoding)
    
  def StringFromObject(self, obj):
    return self._core.data.json.to_string(obj)
    
    

class RSS(Framework.bases.BaseHTTPKit):

  def FeedFromString(self, string):
    return feedparser.parse(string)

  def FeedFromURL(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0):
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
  
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
      
    user_headers = self._add_headers(headers)
    return self.FeedFromString(self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, encoding, errors, timeout=timeout, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content)
    


class YAML(Framework.bases.BaseHTTPKit):
  
  def ObjectFromString(self, string):
    obj = yaml.load(string)

  def ObjectFromURL(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0):
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
    
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
    
    user_headers = self._add_headers(headers)  
    return self.ObjectFromString(self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, encoding, errors, timeout=timeout, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content)
    
    
    
class XML(Framework.bases.BaseHTTPKit):
  def Element(self, name, text=None, **kwargs):
    return self._core.data.xml.element(name, text, **kwargs)

  def StringFromElement(self, el, encoding='utf8', method=None):
    if method:
      self._core.log.warning('The method argument of XML.StringFromElement is deprecated - use HTML.StringFromElement instead.')
    return self._core.data.xml.to_string(el, encoding, method)

  def ElementFromString(self, string, isHTML=False, encoding=None):
    if isHTML:
      self._core.log.warning('The isHTML argument of XML.ElementFromString and XML.ElementFromURL is deprecated - use HTML.ElementFromString or HTML.ElementFromURL instead.')
    return self._core.data.xml.from_string(string, isHTML, encoding)

  def ElementFromURL(self, url, isHTML=False, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0):
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
    
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
    
    user_headers = self._add_headers(headers)  
    return self.ElementFromString(self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, encoding, errors, timeout=timeout, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content, isHTML=isHTML, encoding=encoding)
    
  def ObjectFromString(self, string):
    return self._core.data.xml.object_from_string(string)
    
  def StringFromObject(self, obj, encoding='utf-8'):
    return self._core.data.xml.object_to_string(obj, encoding)
    
  def ObjectFromURL(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0):
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
    
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
    
    user_headers = self._add_headers(headers)  
    return self.ObjectFromString(self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, encoding, errors, timeout=timeout, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content)
    
    
    
class HTML(Framework.bases.BaseHTTPKit):
  def Element(self, name, text=None, **kwargs):
    return self._core.data.xml.html_element(name, text, **kwargs)

  def StringFromElement(self, el, encoding='utf8'):
    return self._core.data.xml.to_string(el, encoding, 'html')

  def ElementFromString(self, string):
    return self._core.data.xml.from_string(string, isHTML=True)

  def ElementFromURL(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, timeout=GLOBAL_DEFAULT_TIMEOUT, sleep=0):
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
    
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
        
    user_headers = self._add_headers(headers)
    return self.ElementFromString(self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, encoding, errors, timeout=timeout, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content)
  
  
class ParseKit(Framework.bases.BaseKit):
  
  root_object = False
  
  def _init(self):
    self._globals = dict(
      JSON    = JSON(self._core, self._policy_instance),
      Plist   = Plist(self._core, self._policy_instance),
      RSS     = RSS(self._core, self._policy_instance),
      YAML    = YAML(self._core, self._policy_instance),
      XML     = XML(self._core, self._policy_instance),
      HTML    = HTML(self._core, self._policy_instance)
    )
