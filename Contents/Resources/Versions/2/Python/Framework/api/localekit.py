#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework

class LocaleKit(Framework.bases.BaseKit):
  def _init(self):
    self._globals = dict(
      L = self.LocalString,
      F = self.LocalStringWithFormat,
    )
    self.DefaultLocale = Framework.utils.AttrProxy(self._core.localization, 'default_locale')
    self.Language = self._core.localization.language
    
  @property
  def Geolocation(self):
    return self._core.networking.http_request("http://geo.plexapp.com/geolocate.php", cacheTime=86400).content
  
  @property
  def CurrentLocale(self):
    if self._context and Framework.constants.header.language in self._context.headers:
      return self._context.headers[Framework.constants.header.language]
    return None
  
  def LocalString(self, key):
    return self._core.localization.local_string(key, self.CurrentLocale)
    
  def LocalStringWithFormat(self, key, *args):
    return self._core.localization.local_string_with_format(key, self.CurrentLocale, *args)
    
  def _requres_context(self, context):
    return Framework.constants.header.language in self._context.headers