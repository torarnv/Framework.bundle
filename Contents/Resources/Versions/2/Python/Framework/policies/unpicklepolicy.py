#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import pickle

class UnpicklePolicy(Framework.bases.BasePolicy):

  environment = dict(
    unpickle = pickle.loads
  )
