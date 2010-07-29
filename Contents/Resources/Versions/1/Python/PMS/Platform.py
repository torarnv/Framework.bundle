import os

class PlatformMetaclass(type):
  def __getattr__(self, name):
    if name == "HasSilverlight":
      return os.path.exists("/Library/Internet Plug-ins/Silverlight.plugin")
    return type.__getattr__(self, name)

class Platform(object):
  __metaclass__ = PlatformMetaclass
