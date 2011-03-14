#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework


class StandardPolicy(Framework.bases.BasePolicy):

  api = dict(
    Parse                 = Framework.api.ParseKit,
    Runtime               = Framework.api.RuntimeKit,
    Resource              = Framework.api.ResourceKit,
    Locale                = Framework.api.LocaleKit,
    Network               = Framework.api.NetworkKit,
    Service               = Framework.api.ServiceKit,
    Data                  = Framework.api.DataKit,
    Thread                = Framework.api.ThreadKit,
    Message               = Framework.api.MessageKit,
    Agent                 = Framework.api.AgentKit,
    Model                 = Framework.api.ModelKit,
    Object                = Framework.api.ObjectKit,
    Const                 = Framework.api.ConstKit,
    Log                   = Framework.api.LogKit,
    Util                  = Framework.api.UtilKit,
    User                  = Framework.api.UserKit,
    Prefs                 = Framework.api.PrefsKit,
  )
