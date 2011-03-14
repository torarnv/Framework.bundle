
import Framework
from operator import itemgetter, attrgetter
import random, base64, urllib, string, uuid, unicodedata, os, re, datetime, dateutil.parser, email.utils, time

import pyamf
from pyamf.remoting.client import RemotingService
from pyamf import sol



class ArchiveKit(Framework.bases.BaseHTTPKit):
  
  def Zip(self, data=None):
    return self._core.data.archiving.zip_archive(data)
    
  def ZipFromURL(self, url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None, sleep=0):
    if self._context:
      self._context.update_cache_time(cacheTime)
    
    return self.Zip(self._core.networking.http_request(url, values, headers, cacheTime, autoUpdate, encoding, errors, immediate=True, sleep=sleep, opener=self._opener, txn_id=self._txn_id).content)



class SOL(object):
  def __init__(self, *args):
    if len(args) < 2:
      raise Framework.FrameworkException('AMF.SOL() requires at least two arguments')
      
    #TODO: Paths for Linux & Windows
    sol_path = os.path.expanduser("~/Library/Preferences/Macromedia/Flash Player/#SharedObjects")
    subdir = [d for d in os.listdir(sol_path) if re.match("^[A-Z0-9]{8}$", d)][0]  # hopefully there's only one...
    self._path = os.path.join(sol_path, subdir, *args) + '.sol'
    if os.path.exists(self._path):
      self._sol = sol.load(self._path)
    else:
      self._sol = sol.SOL(args[-1])
      
  def save(self, encoding=0):
    sol_dir = os.path.dirname(self._path)
    if not os.path.exists(sol_dir):
      os.makedirs(sol_dir)
    self._sol.save(self._path, encoding)
      
  def __cmp__(self, other):                   return self._sol.__cmp__(other)                   
  def __contains__(self, item):               return self._sol.__contains__(item)               
  def __hash__(self):                         return self._sol.__hash__()                       
  def __getitem__(self, name):                return self._sol.__getitem__(name)                
  def __setitem__(self, name, value):         return self._sol.__setitem__(name, value)         
  def __delitem__(self, name):                return self._sol.__delitem__(name)                
                                                                                                
  def __lt__(self, other):                    return self._sol.__lt__(other)                    
  def __le__(self, other):                    return self._sol.__le__(other)                    
  def __eq__(self, other):                    return self._sol.__eq__(other)                    
  def __ne__(self, other):                    return self._sol.__ne__(other)                    
  def __gt__(self, other):                    return self._sol.__gt__(other)                    
  def __ge__(self, other):                    return self._sol.__ge__(other)                    
                                                                                                
  def clear(self):                            return self._sol.clear()                          
  def get(self, key, default=None):           return self._sol.get(key, default)                
  def has_key(self, key):                     return self._sol.has_key(key)                     
  def items(self):                            return self._sol.items()                          
  def iteritems(self):                        return self._sol.iteritems()                      
  def iterkeys(self):                         return self._sol.iterkeys()                       
  def keys(self):                             return self._sol.keys()                           
  def pop(self, key, default=None):           return self._sol.pop(key, default)                
  def popitem(self):                          return self._sol.popitem()                        
  def setdefault(self, key, default=None):    return self._sol.setdefault(key, default)
  def update(self, *args, **kwargs):          return self._sol.update(*args, **kwargs)
  def values(self):                           return self._sol.values()                           
  
  

class AMFKit(Framework.bases.BaseKit):
  def _init(self):
    self.RemotingService = RemotingService
    self.RegisterClass = pyamf.register_class
    self.SOL = SOL
    


class HashKit(Framework.bases.BaseKit):
  def MD5(self, data):
    return self._core.data.hashing.md5(data)

  def SHA1(self, data):
    return self._core.data.hashing.sha1(data)

  def SHA224(self, data):
    return self._core.data.hashing.sha224(data)

  def SHA256(self, data):
    return self._core.data.hashing.sha256(data)

  def SHA384(self, data):
    return self._core.data.hashing.sha384(data)

  def SHA512(self, data):
    return self._core.data.hashing.sha512(data)

  def CRC32(self, data):
    return self._core.data.hashing.crc32(data)



class StringKit(Framework.bases.BaseKit):

  def Encode(self, s):
    return Framework.utils.safe_encode(s)

  def Decode(self, s):
    return Framework.utils.safe_decode(s)

  def Quote(self, s, usePlus=False):
    if usePlus:
      return urllib.quote_plus(s)
    else:
      return urllib.quote(s)

  def URLEncode(self, s):
    return Framework.utils.urlencode(s)

  def Unquote(self, s, usePlus=False):
    if usePlus:
      return urllib.unquote_plus(s)
    else:
      return urllib.unquote(s)

  def Join(self, words, sep=None):
    return string.join(words, sep)

  def StripTags(self, s):
    return re.sub(r'<[^<>]+>', '', s)

  def UUID(self):
    return str(uuid.uuid4())

  def StripDiacritics(self, s):
    u = unicode(s).replace(u"\u00df", u"ss").replace(u"\u1e9e", u"SS")
    nkfd_form = unicodedata.normalize('NFKD', u)
    only_ascii = nkfd_form.encode('ASCII', 'ignore')
    return only_ascii

  def Pluralize(self, s):
    return Framework.utils.plural(s)



class DatetimeKit(Framework.bases.BaseKit):

  def Now(self):
    return datetime.datetime.now()

  def ParseDate(self, date):
    if date == None or len(date) == 0:
      return None #TODO: Should we return None or throw an exception here?
    try:
      year_only = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
      if year_only.match(date):
        result = datetime.datetime.strptime(date, "%Y-%m-%d")
      else:
        result = datetime.datetime.fromtimestamp(time.mktime(email.utils.parsedate(date)))
    except:
      result = dateutil.parser.parse(date)
    return result

  def Delta(self, **kwargs):
    return datetime.timedelta(**kwargs)

  def TimestampFromDatetime(self, dt):
    return Framework.utils.timestamp_from_datetime(dt)



class UtilKit(Framework.bases.BaseKit):

  def _init(self):
    self._amf = AMFKit(self._core, self._policy_instance)
    self._hash = HashKit(self._core, self._policy_instance)
    self._string = StringKit(self._core, self._policy_instance)
    self._datetime = DatetimeKit(self._core, self._policy_instance)
    self._archive = ArchiveKit(self._core, self._policy_instance)
    
    self._globals = dict(
      AMF = self._amf,
      Hash = self._hash,
      String = self._string,
      Datetime = self._datetime,
      Archive = self._archive,
      E = self._string.Encode,
      D = self._string.Decode
    )
  
  def ListSortedByKey(self, l, key):
    return sorted(l, key=itemgetter(key))
  
  def ListSortedByAttr(self, l, attr):
    return sorted(l, key=attrgetter(attr))
    
  def LevenshteinDistance(self, first, second):
    return Framework.utils.levenshtein_distance(first, second)
    
  def LongestCommonSubstring(self, first, second):
    return Framework.utils.longest_common_substring(first, second)
    
  def Random(self):
    return random.random()
    
  def RandomInt(self, a, b):
    return random.randint(a, b)
    
  def RandomItemFromList(self, l):
    return l[random.randint(0,len(l)-1)]
