#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework


class ModelPolicy(Framework.bases.BasePolicy):

  api = dict(
    Template = Framework.api.TemplateKit
  )
  
  environment = dict(
    __name__ = '__model__',
  )

  ext = 'pym'