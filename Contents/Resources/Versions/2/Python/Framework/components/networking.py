#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import urllib, cookielib, gzip, socket, os, weakref, select, random, time, sys

if sys.platform == 'win32':
  import urllib2, httplib
  GLOBAL_DEFAULT_TIMEOUT = socket._GLOBAL_DEFAULT_TIMEOUT
else:
  import urllib2_new as urllib2
  import httplib_new as httplib
  GLOBAL_DEFAULT_TIMEOUT = httplib._GLOBAL_DEFAULT_TIMEOUT
  
import cStringIO as StringIO
from OpenSSL import SSL

class SSLSocket(object):
  def __init__(self):
    self._sock = socket.socket()
    self._con = SSL.Connection(SSL.Context(SSL.SSLv23_METHOD), self._sock)
  
  def do_handshake(self):
    while True:
      try:
        self._con.do_handshake()
        break
      except SSL.WantReadError:
        select.select([self._sock], [], [], 1.0)
        
  def recv(self, count):
    while True:
      try:
        return self._con.recv(count)
      except SSL.WantReadError:
        select.select([self._sock], [], [], 1.0)
        
  def disconnect(self):
    self._sock.shutdown(socket.SHUT_RDWR)
    self._sock.close()
        
  def __getattr__(self, name):
    return getattr(self._con, name)
    
class CookieObject(Framework.objects.XMLObject):
  def __init__(self, *args, **kwargs):
    Framework.objects.XMLObject.__init__(self, *args, **kwargs)
    self.tagName = 'Cookie'

class HTTPHeaderProxy(object):
  def __init__(self, headers):
    if headers:
      self._headers = dict(headers)
    else:
      self._headers = {}
    
  def __getitem__(self, name):
    return self._headers[name.lower()]
    
  def __repr__(self):
    return repr(self._headers)

class HTTPRequest(object):
  def __init__(self, core, request, cache, encoding, timeout, immediate, sleep, opener, txn_id):
    self._core = core
    self._request = request
    self._cache = cache
    self._data = None
    self._headers = None
    self._encoding = encoding
    self._timeout = timeout
    self._opener = opener
    self._txn_id = txn_id
    self._sleep = sleep
    if immediate:
      self._load_if_needed()
    
  def _load_if_needed(self):
    if not self._data:
      if self._cache != None and self._cache['content'] and not self._cache.expired:
        self._core.log_debug(self._txn_id, "Fetching %s from the HTTP cache", self._request.get_full_url())
        self._data = self._cache['content']
        self._headers = HTTPHeaderProxy(self._cache.headers)
      else:
        self._core.log_debug(self._txn_id, "Requesting %s", self._request.get_full_url())

        f = None
        try:
          f = self._opener.open(self._request, timeout=self._timeout)

          if f.headers.get('Content-Encoding') == 'gzip':
            stream = StringIO.StringIO(f.read())
            gzipper = gzip.GzipFile(fileobj=stream)
            self._data = gzipper.read()
            del gzipper
            del stream
          else:
            self._data = f.read()

          #TODO: Move to scheduled save method when the background worker is finished
          self._core.networking._save()

          info = f.info()
          self._headers = HTTPHeaderProxy(info.dict)
          del info

          if self._cache != None:
            self._cache['content'] = self._data
            self._cache.headers = self._headers._headers
          
          if self._sleep > 0:
            time.sleep(self._sleep)

        except urllib2.HTTPError, e:
          e.close()
          self._core.log_error(self._txn_id, "Error opening URL '%s'", self._request.get_full_url())
          raise

        finally:
          if f:
            f.fp._sock.recv = None  # Hack to stop us leaking file descriptors on errors.
            f.close()
            del f
        
  @property
  def headers(self):
    self._load_if_needed()
    return self._headers
  
  def __str__(self):
    self._load_if_needed()
    if self._encoding:
      result = str(unicode(self._data, self._encoding))
    else:
      result = self._data
    return result
    
  def __len__(self):
    self._load_if_needed()
    return len(self._data)
    
  def __add__(self, other):
    return str(self) + other
    
  def __radd__(self, other):
    return other + str(self)
    
  @property
  def content(self):
    return self.__str__()
    

class Networking(Framework.bases.BaseComponent):
  def _init(self):
    self._os_versions = ['10_4_10', '10_4_11', '10_5_0', '10_5_1', '10_5_2', '10_5_3', '10_5_4', '10_5_5', '10_5_6', '10_5_7']
    self._languages = ['en-gb', 'it-it', 'ja-jp', 'nb-no', 'en-us', 'fr-fr', 'pl-pl', 'es-es', 'de-de']
    
    self._safari_versions = [
      ['528.16', '4.0', '528.16'], 
      ['528.10+', '4.0', '528.1'],
      ['525.27.1', '3.2.1', '525.27.1'],
      ['528.8+', '3.2.1', '525.27.1'],
      ['530.1+', '3.2.1', '525.27.1'],
      ['528.5+', '3.2.1', '525.27.1'],
      ['528.16', '3.2.1', '525.27.1'],
      ['525.26.2', '3.2', '525.26.12'],
      ['528.7+', '3.1.2', '525.20.1'],
      ['525.18.1', '3.1.2', '525.20.1'],
      ['525.18', '3.1.2', '525.20.1'],
      ['525.7+', '3.1.2', '525.20.1'],
      ['528.1', '3.1.2', '525.20.1'],
      ['527+', '3.1.1', '525.20'],
      ['525.18', '3.1.1', '525.20'],
      ['525.13', '3.1', '525.13']
    ]
    
    self._firefox_versions = [
      ['1.9.2.8', '20100805', '3.6.8'],
      ['1.9.2.4', '20100611', '3.6.4'],
      ['1.9.2.3', '20100401', '3.6.3'],
      ['1.9.2.2', '20100316', '3.6.2'],
      ['1.9.2', '20100115', '3.6'],
      ['1.9.1.6', '20091201', '3.5.6'],
      ['1.9.1.3', '20090824', '3.5.3'],
      ['1.9.1.1', '20090715', '3.5.1'],
    ]
    
    self._firefox_ua_string = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X %s; %s; rv:%s) Gecko/%s Firefox/%s"
    self._safari_ua_string = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X %s; %s) AppleWebKit/%s (KHTML, like Gecko) Version/%s Safari/%s"
    
    self.headers = {
      'Accept-Encoding': 'gzip'
    }
    self.randomize_user_agent()
    self._cookie_jar = cookielib.MozillaCookieJar()
    self._password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    self._auth_handler = urllib2.HTTPBasicAuthHandler(self._password_mgr)
    self.default_timeout = self._core.config.default_network_timeout
    self.user_headers = {}
    
    self._cookie_file_path = "%s/HTTPCookies" % self._core.storage.data_path
    if os.path.isfile(self._cookie_file_path):
      try:
        self._cookie_jar.load(self._cookie_file_path)
        self._core.log.debug('Loaded HTTP cookies')
      except:
        self._core.log_except(None, 'Exception loading HTTP cookies')
    else:
      self._core.log.debug("No cookie jar found")
    
    # Build & install an opener with the cookie jar & auth handler
    self._opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cookie_jar), self._auth_handler)
    
    self.cache_time = 0
    self._cache_mgr = self._core.caching.get_cache_manager('HTTP', system=True)
    
    self.ssl_socket = SSLSocket
    
  def randomize_user_agent(self, browser=None):
    os_version = self._os_versions[random.randint(0,len(self._os_versions)-1)]
    language = self._languages[random.randint(0,len(self._languages)-1)]

    if browser == None:
      browser = ['firefox', 'safari'][random.randint(0,1)]
    
    if browser == 'firefox':
      v1, v2, v3 = self._firefox_versions[random.randint(0,len(self._firefox_versions)-1)]
      self.headers['User-agent'] = self._firefox_ua_string % (os_version, language, v1, v2, v3)
    
    else:
      v1, v2, v3 = self._safari_versions[random.randint(0,len(self._safari_versions)-1)]
      self.headers['User-agent'] = self._safari_ua_string % (os_version, language, v1, v2, v3)
    
  def _save(self, cookie_jar=None):
    if cookie_jar == None or cookie_jar == self._cookie_jar:
      self._cookie_jar.save(self._cookie_file_path)
    
  def http_request(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, addToLog=True, timeout=GLOBAL_DEFAULT_TIMEOUT, immediate=False, sleep=0, opener=None, txn_id=None):
    if cacheTime == None: cacheTime = self.cache_time
    
    
    data = None
    if values:
      data = urllib.urlencode(values)
      cacheTime = 0
      immediate = True

    # If a custom opener was provided, don't save data for this request to the HTTP cache
    if opener == None:
      opener = self._opener
      cache_mgr = self._cache_mgr
      
      # Check whether we should trim the HTTP cache
      if cache_mgr.item_count > self._core.config.http_cache_max_items + self._core.config.http_cache_max_items_grace:
        cache_mgr.trim(self._core.config.http_cache_max_size, self._core.config.http_cache_max_items)
      
      url_cache = cache_mgr[url]
      
      if url_cache.autoUpdate != autoUpdate:
        url_cache.autoUpdate = autoUpdate
      url_cache.set_expiry_interval(cacheTime)
    
    else:
      url_cache = None
    
    h = dict(self.headers)
    h.update(headers)
    
    request = urllib2.Request(url, data, h)
    return HTTPRequest(self._core, request, url_cache, encoding, timeout, immediate, sleep, opener, txn_id)
  
  def set_http_password(self, url, username, password, realm=None, manager=None):
    # Strip http:// from the beginning of the url
    if url[0:6] == "http://":
      url = url[7:]
    if manager == None: manager = self._password_mgr
    manager.add_password(realm, url, username, password)
    
  def get_cookies_for_url(self, url, cookie_jar):
    if cookie_jar == None: cookie_jar = self._cookie_jar
    request = urllib2.Request(url)
    cookie_jar.add_cookie_header(request)
    if request.unredirected_hdrs.has_key('Cookie'):
      return request.unredirected_hdrs['Cookie']
    return None
    
  def cookie_container(self, **kwargs):
    container = Framework.objects.MediaContainer(self._core)
    
    for cookie in self._cookie_jar:
    
      should_append = True
      for name in kwargs:
        if hasattr(cookie, name) and getattr(cookie, name) != kwargs[name]:
          should_append = False
          break

      if should_append:
        container.Append(
          CookieObject(
            self._core,
            domain = cookie.domain,
            path = cookie.path,
            name = cookie.name,
            value = cookie.value,
            secure = cookie.secure,
          )
        )
    return container
    
  def clear_cookies(self, cookie_jar=None):
    if cookie_jar == None:
      cookie_jar = self._cookie_jar
    self._core.log.debug("Clearing HTTP cookies")
    cookie_jar.clear()
    self._core.storage.remove(self._cookie_file_path)
    self._save(cookie_jar)
    
  def clear_http_cache(self):
    self._cache_mgr.clear()
    
  @property
  def address(self):
    try:
      result = socket.gethostbyname(socket.gethostname())
      return result
    except:
      return None
      
  @property
  def hostname(self):
    return socket.gethostname()
    
  @property
  def default_timeout(self):
    return socket.getdefaulttimeout()
    
  @default_timeout.setter
  def default_timeout(self, timeout):
    self._core.log.debug('Setting the default network timeout to %.1f', float(timeout))
    return socket.setdefaulttimeout(timeout)
    
  #TODO: Allow args
  def socket(self):
    return socket.socket()
    
  def resolve_hostname_via_pms(self, hostname):
    url = 'http://127.0.0.1:32400/servers/resolve?name=%s' % hostname
    data = self.http_request(url).content
    xml = self._core.data.xml.from_string(data)
    return xml.xpath('//Address')[0].get('address')
    
  def resolve_hostname_if_required(self, hostname):
    # If running on Linux or Windows, and resolving a Bonjour host, request it via PMS.
    # This is faster on Windows (no two-second delay), and makes it possible on Linux 
    # (since gethostbyname doesn't work at all for mDNS names).
    #
    if hostname.endswith('.local.') and self._core.runtime.os in ('Linux', 'Windows'):
      return self.resolve_hostname_via_pms(hostname)
    # Otherwise, return the hostname unmodified, as the OS will be able to resolve it
    return hostname
    
