#
#  Plex Media Framework
#  Copyright (C) 2008-2009 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import demjson as json
import HTTP

####################################################################################################

def ObjectFromString(string, encoding=None, errors=None):
  if string is None: return None
  if not (encoding is None and errors is None):
    if encoding is None: encoding = "utf8"
    if errors is None: errors = "strict"
    string = string.encode(encoding, errors)
  return json.decode(string)
  
####################################################################################################
  
def ObjectFromURL(url, values=None, headers={}, cacheTime=None, autoUpdate=False, encoding=None, errors=None):
  return ObjectFromString(HTTP.Request(url, values=values, headers=headers, cacheTime=cacheTime, autoUpdate=autoUpdate, encoding=encoding, errors=errors), encoding=encoding, errors=errors)

####################################################################################################

def StringFromObject(obj):
  return json.encode(obj)
  
####################################################################################################
