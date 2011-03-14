#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

def generate_class(access_point, namespace_name, template, storage_path):
  import namespace
  namespace.__name__ = 'Framework.models.'+namespace_name+'.'+access_point._identifier.replace('.','_')
  access_point._core.log.debug("Generating class for '%s' model in namespace '%s' with access point '%s'", template.__name__, namespace_name, access_point._identifier)
  cls = namespace.generate_class(access_point, template, storage_path)
  del namespace
  return cls