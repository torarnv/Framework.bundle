#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework

def _super(*args):
  return super(*args)

class ElevatedPolicy(Framework.bases.BasePolicy):

  api = dict(
    Core                  = Framework.api.CoreKit,
    Player                = Framework.api.PlayerKit,
    Parse                 = Framework.api.ParseKit,
    Runtime               = Framework.api.RuntimeKit,
    Resource              = Framework.api.ResourceKit,
    Locale                = Framework.api.LocaleKit,
    Network               = Framework.api.NetworkKit,
    Service               = Framework.api.ServiceKit,
    Data                  = Framework.api.DataKit,
    Thread                = Framework.api.ThreadKit,
    Message               = Framework.api.MessageKit,
    Helper                = Framework.api.HelperKit,
    Agent                 = Framework.api.AgentKit,
    Model                 = Framework.api.ModelKit,
    Object                = Framework.api.ObjectKit,
    Const                 = Framework.api.ConstKit,
    Log                   = Framework.api.LogKit,
    Util                  = Framework.api.UtilKit,
    User                  = Framework.api.UserKit,
    Stream                = Framework.api.StreamKit,
    Prefs                 = Framework.api.PrefsKit,
  )

  environment = dict(
    hasattr               = hasattr,
    getattr               = getattr,
    setattr               = setattr,
    dir                   = dir,
    super                 = _super,
    type                  = type,
  )
  
  allow_whitelist_extension = True
  allow_bundled_libraries = True
  elevated_execution = True
