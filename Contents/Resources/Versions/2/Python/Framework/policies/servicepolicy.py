#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework


class ServicePolicy(Framework.bases.BasePolicy):
  """
    The service policy is very basic. It exposes very little - individual services should add
    additional functions prior to executing code.
  """
  api = dict(
    Parse       = Framework.api.ParseKit,
    Network     = Framework.api.NetworkKit,
    Log         = Framework.api.LogKit,
    Util        = Framework.api.UtilKit,
    Object      = Framework.api.ObjectKit,
    Const       = Framework.api.ConstKit,
    Prefs       = Framework.api.PrefsKit,
    Service     = Framework.api.ServiceKit,
    Runtime     = Framework.api.RuntimeKit,
  )
  
  environment = dict(
    __name__    = '__service__'
  )
  
  ext = 'pys'
  