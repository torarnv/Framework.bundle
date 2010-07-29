#!/usr/bin/python2.5
#
#  Plex Media Framework
#  Copyright (C) 2008-2009 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import os, sys
from xml.dom import minidom

# Set the default encoding
__plist_path = os.path.join(sys.argv[1], "Contents/Info.plist")
__plist = minidom.parse(__plist_path)
__encoding = "utf-8"
for el in __plist.getElementsByTagName("plist")[0].getElementsByTagName("dict")[0].getElementsByTagName("key"):
  if el.childNodes[0].nodeValue == "PlexPluginEncoding":
    __encoding = el.nextSibling.nextSibling.childNodes[0].nodeValue
reload(sys)
sys.setdefaultencoding(__encoding)

# Make the libraries available
PMSLibPath = os.path.join(sys.path[0], "../Libraries")
sys.path.append(PMSLibPath)

# Import the Plugin module
import PMS.Plugin, PMS.JSON, PMS.Resource

# Load the default MIME types
f = open(os.path.join(os.path.split(sys.argv[0])[0], "PMS/MimeTypes.json"), "r")
PMS.Resource.__mimeTypes = PMS.JSON.ObjectFromString(f.read())
f.close()

# Run the plugin
if len(sys.argv) == 2: PMS.Plugin.__run(sys.argv[1])
