#!/usr/bin/python2.5
#
#  Plex Media Framework
#  Copyright (C) 2008-2009 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import os, sys

PMSLibPath = os.path.join(sys.path[0], "PMS/__lib")
sys.path.append(PMSLibPath)

# Import the Plugin module
import PMS.Plugin, PMS.JSON

# Load the default MIME types
PMS.Plugin.MimeTypes = PMS.JSON.DictFromFile(os.path.join(os.path.split(sys.argv[0])[0], "PMS/MimeTypes.json"))

# Run the plugin
if len(sys.argv) == 2: PMS.Plugin.__run(sys.argv[1])
