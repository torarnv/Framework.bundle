#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework


class CoreKit(Framework.bases.BaseKit):
  
  root_object = False
  
  def _init(self):
    self._globals = dict(
      Core = self._core,
      Framework = Framework,
      Factory = self._factory,
      FactoryClass = self._factory_class,
    )
    
  def _factory(self, cls):
    return Framework.objects.ObjectFactory(self._core, cls)
    
  def _factory_class(self, fac):
    return fac._object_class