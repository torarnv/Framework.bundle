#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os


def ProxyObjectGenerator(proxy_name):
  def ProxyFunction(data, sort_order=None, ext=None):
    return Framework.modelling.attributes.ProxyObject(proxy_name, proxy_name.lower(), data, sort_order, ext)
  return ProxyFunction

class ProxyKit(object):
  def __init__(self):
    self.Preview     = ProxyObjectGenerator('Preview')
    self.Media       = ProxyObjectGenerator('Media')
    self.LocalFile   = ProxyObjectGenerator('LocalFile')
    
    
class ModelKit(Framework.bases.BaseKit):
  
  root_object = False
  
  def _init(self):
    template_file = os.path.join(self._core.bundle_path, 'Contents', 'Models', '__init__.pym')
    self._globals = dict()
    
    if os.path.exists(template_file):
      self._accessor = Framework.modelling.ModelAccessor(
        self._core,
        'usermodels',
        template_file,
        os.path.join(self._core.storage.data_path, 'ModelData')
      )
    
      self._globals['Model'] = Model = self._accessor.get_access_point(self._core.identifier)
    
    self._globals['Proxy'] = ProxyKit()