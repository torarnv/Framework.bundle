#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import xmlrpclib, cookielib, cerealizer, sys

if sys.platform == 'win32':
  import urllib2, httplib, socket
  GLOBAL_DEFAULT_TIMEOUT = socket._GLOBAL_DEFAULT_TIMEOUT
else:
  import urllib2_new as urllib2
  import httplib_new as httplib
  GLOBAL_DEFAULT_TIMEOUT = httplib._GLOBAL_DEFAULT_TIMEOUT

cerealizer.register(cookielib.Cookie)

class FrameworkTransport(xmlrpclib.Transport):
  
  def __init__(self, httpkit):
    self._httpkit = httpkit
    xmlrpclib.Transport.__init__(self, use_datetime=True)
    
  @property
  def user_agent(self):
    return self._httpkit._user_agent

class XMLRPC(object):
  
  def __init__(self, httpkit):
    self._httpkit = httpkit
    
  def Proxy(self, url, encoding=None):
    if url[0:8] == 'https://':
      raise Framework.FrameworkException('HTTPS URLs are not currently supported')
    return xmlrpclib.ServerProxy(url, FrameworkTransport(self._httpkit), encoding, use_datetime=True)
  

class HTTP(Framework.bases.BaseHTTPKit):
  
  def _init(self):
    # It'd be nicer to have separate cache times for the API and the internal components, but we have
    # to set it in the networking component so the same setting gets used by all HTTP-accessing APIs. 
    self.CacheTime = Framework.utils.AttrProxy(self._core.networking, 'cache_time')
    
  @property
  def Headers(self):
    return self._user_headers
    
  #Deprecated
  def SetCacheTime(self, cacheTime):
    self._core.log.warn('The HTTP.SetCacheTime() function is deprecated. Use the HTTP.CacheTime property instead.')
    self._core.networking.cache_time = cacheTime
    
  #Deprecated
  def SetHeader(self, header, value):
    self._core.log.warn('The HTTP.SetHeader() function is deprecated. Use HTTP.Headers[] to get and set headers instead.')
    self._core.networking.user_headers[header] = value
    
  #Deprecated
  def SetTimeout(self, timeout):
    self._core.log.warn('The HTTP.SetTimeout() function is deprecated. Use the Network.Timeout property instead.')
    self._core.networking.default_timeout = timeout
    
  def Request(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, addToLog=True, timeout=GLOBAL_DEFAULT_TIMEOUT, immediate=False, sleep=0):
    if self._context:
      if values == None:
        self._context.update_cache_time(cacheTime)
      else:
        self._context._cache_time = 0
        
    if url.find(':32400/') > -1 and self._core._policy.elevated_execution == False:
      raise Framework.FrameworkException("Accessing the media server's HTTP interface is not permitted.")
    user_headers = self._add_headers(headers)
    return self._core.networking.http_request(url, values, user_headers, cacheTime, autoUpdate, encoding, errors, addToLog, timeout, immediate, sleep=sleep, opener=self._opener)
    
  def GetCookiesForURL(self, url):
    if self._context:
      cookie_jar = self._context.cookie_jar
    else:
      cookie_jar = None
    return self._core.networking.get_cookies_for_url(url, cookie_jar=cookie_jar)
    
  def SetPassword(self, url, username, password, realm=None):
    return self._core.networking.set_http_password(url, username, password, realm)
    
  def PreCache(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None):
    self._core.runtime.create_thread(self._precache, txn_id=self._txn_id, url=url, values=values, headers=headers, cacheTime=cacheTime, autoUpdate=autoUpdate, encoding=encoding, errors=errors)
    
  def _precache(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None):
    self.Request(url=url, values=values, headers=headers, cacheTime=cacheTime, autoUpdate=autoUpdate, encoding=encoding, errors=errors, immediate=True)
    
  def ClearCookies(self):
    self._core.networking.clear_cookies(self._cookie_jar)
    
  def ClearCache(self):
    self._core.networking.clear_http_cache()
    
  def RandomizeUserAgent(self, browser=None):
    self._core.networking.randomize_user_agent(browser=browser)
  
  def _end_context(self, response_headers):
    if self._context.cache_time != None:
      if self._context.cache_time == 0:
        response_headers['Cache-Control'] = 'no-cache'
      else:
        response_headers['Cache-Control'] = 'max-age=%d' % self._context.cache_time
      
    # Create a packed cookie containing all HTTP cookies and custom headers
    cookie_list = []
    if self._context.cookie_jar != None:
      for cookie in self._context.cookie_jar:
        cookie_list.append(cookie)
      
    state_data = {}
    if len(self._context.http_headers) > 0:
      state_data["http_headers"] = self._context.http_headers
      
    if len(cookie_list) > 0:
      packed_cookies = Framework.utils.pack(cookie_list)
      response_headers['Set-Cookie'] = self._core.identifier + '=' + packed_cookies
    
  @property
  def _user_agent(self):
    if 'User-agent' in self.Headers:
      return self.Headers['User-agent']
    return self._core.networking.headers['User-agent']
    
class NetworkKit(Framework.bases.BaseKit):
  def _init(self):
    self._http = HTTP(self._core, self._policy_instance)
    self._xmlrpc = XMLRPC(self._http)
    self._globals = dict(
      HTTP    = self._http,
      XMLRPC  = self._xmlrpc,
    )
    self.Timeout = Framework.utils.AttrProxy(self._core.networking, 'default_timeout')
    
  @property
  def Address(self):
    return self._core.networking.address
  
  @property
  def PublicAddress(self):
    return self._core.networking.http_request("http://www.plexapp.com/ip.php", cacheTime=7200).content.strip()
  
  @property
  def Hostname(self):
    return self._core.networking.hostname
    
  def Socket(self):
    return self._core.networking.socket()
    
  def SSLSocket(self):
    return self._core.networking.ssl_socket()
