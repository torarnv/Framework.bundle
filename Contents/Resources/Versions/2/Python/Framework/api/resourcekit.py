#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import mimetypes


class ResourceKit(Framework.bases.BaseKit):

  def _init(self):
    self._globals = dict(
      R = self.ExternalPath,
      S = self.SharedExternalPath,
    )
    
  def ExternalPath(self, itemname):
    return self._core.runtime.external_resource_path(itemname)
  
  def SharedExternalPath(self, itemname):
    return self._core.runtime.external_shared_resource_path(itemname)  
  
  def Load(self, itemname, binary=True):
    return self._core.storage.load_resource(itemname, binary)
    
  def LoadShared(self, itemname, binary=True):
    return self._core.storage.load_shared_resource(itemname, binary)
    
  def GuessMimeType(self, path):
    return mimetypes.guess_type(path, strict=False)[0]
    
  def AddMimeType(self, mimetype, extension):
    if extension[0] != '.': extension = '.' + extension
    mimetypes.add_type(mimetype, extension)