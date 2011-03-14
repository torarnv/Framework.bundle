#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

class interface(object):
  pipe = 'pipe'
  socket = 'socket'
  
class context(object):
  media = 'media'
  agent = 'agent'
  
class header(object):
  client_capabilities = 'X-Plex-Client-Capabilities'
  client_platform = 'X-Plex-Client-Platform'
  transaction_id = 'X-Plex-Transaction-Id'
  language = 'X-Plex-Language'
  preferences = 'X-Plex-Preferences'
  proxy_cookies = 'X-Plex-Proxy-Cookies'