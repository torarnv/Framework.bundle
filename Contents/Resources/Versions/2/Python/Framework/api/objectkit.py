#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import urllib
from Framework.modelling.objects import generate_class, generate_model_interface_class, generate_model_interface_container_class

class indirect_callback_string(unicode): pass

class ProviderObject(Framework.modelling.objects.Object):
  xml_tag = 'Provider'
  _attribute_list = ['key', 'title', 'type']

class PartObject(Framework.modelling.objects.Object):
  xml_tag = 'Part'
  _attribute_list = ['key', 'file']

  def __init__(self, **kwargs):
    if 'file' not in kwargs:
      kwargs['file'] = ''
    Framework.modelling.objects.Object.__init__(self, **kwargs)
        
class MediaObject(Framework.modelling.objects.Container):
  xml_tag = 'Media'

  _children_attr_name = 'parts'
  _child_types = [PartObject]
  _attribute_list = ['protocols', 'platforms', 'bitrate', 'aspect_ratio', 'audio_channels', 'audio_codec', 'video_codec', 'video_resolution', 'container', 'video_frame_rate']
  
  def __init__(self, **kwargs):
    
    def get_list(name):
      
      if name in kwargs:
        result = kwargs[name]
        del kwargs[name]
        return result
      else:
        return []
        
    self._platforms = get_list('platforms')
    self._protocols = get_list('protocols')
    
    # If the core attribute for the given name contains one value, return it
    def set_default_attr(attr_name, attr_key):
      if attr_name not in kwargs and attr_key in self._core.attributes and len(self._core.attributes[attr_key]) == 1:
        kwargs[attr_name] = self._core.attributes[attr_key][0]
    
    set_default_attr('audio_codec', Framework.core.AUDIO_CODEC_KEY)
    set_default_attr('video_codec', Framework.core.VIDEO_CODEC_KEY)
    set_default_attr('container', Framework.core.MEDIA_CONTAINER_KEY)
    
    Framework.modelling.objects.Container.__init__(self, **kwargs)
    
  @property
  def platforms(self):
    return self._platforms
    
  @property
  def protocols(self):
    return self._protocols
    
  def _to_xml(self, context=None):
    el = Framework.modelling.objects.Container._to_xml(self, context)
    
    if context:
      if len(self) > 0:
        # If the item defines a list of platforms, check that the current platform is a valid one
        if len(self.platforms) > 0:
          if context.platform in self.platforms:
            el.set('playable', '1')
          else:
            return None
      
        # If the first media part is an IndirectFunction instance, flag it as 'indirect'
        if isinstance(self._objects[0].key, indirect_callback_string):
          el.set('indirect', '1')
      
      # If the context's protocol list contains one of this item's protocols, flag the item as 'playable'
      for protocol in context.protocols:
        if protocol in self.protocols:
          el.set('playable', '1')
          break
  
    return el

class ObjectKit(Framework.bases.BaseKit):

  root_object = False
  
  def _generate_object(self, model, media=True):
    if media:
      child_types = [MediaObject]
    else:
      child_types = []
    return generate_model_interface_class(self._core, model, child_types = child_types, children_attr_name = 'items')

  
  def _requires_context(self):
    return True
  
    
  def _web_video_url(self, url):
    prefix = self._core.runtime.prefix_handlers.keys()[0]
    return "plex://127.0.0.1/video/:/webkit?url=%s&prefix=%s" % (urllib.quote_plus(url), prefix)
    
    
  def _rtmp_video_url(self, url, clip=None, clips=None, width=None, height=None, live=False):
    final_url = "http://www.plexapp.com/player/player.php" + \
      "?url=" + urllib.quote(url) + \
      "&live="
    if live:
      final_url += "true"
    else:
      final_url += "false"
    if clip:
      final_url += "&clip=" + urllib.quote(clip)
    if clips:
      for c in clips:
        final_url += "&clip[]=" + str(c)
    if width:
      final_url += "&width=" + str(width)
    if height:
      final_url += "&height=" + str(height)
      
    return self._web_video_url(final_url)
    
    
  def _windows_media_video_url(self, url, width=None, height=None):
    final_url = "http://www.plexapp.com/player/silverlight.php" + \
      "?stream=" + urllib.quote(url)
    if width:
      final_url += "&width=" + str(width)
    if height:
      final_url += "&height=" + str(height)
    
    return self._web_video_url(final_url)
    
  
  def _init(self):
    self._accessor = self._core._metadata_model_accessor
    self._access_point = self._accessor.get_access_point(self._core.identifier)

    self._globals = dict(
      # Old-school objects
      XMLObject             = Framework.objects.ObjectFactory(self._core, Framework.objects.XMLObject),
      XMLContainer          = Framework.objects.ObjectFactory(self._core, Framework.objects.XMLContainer),
      MediaContainer        = Framework.objects.ObjectFactory(self._core, Framework.objects.MediaContainer),
      MessageContainer      = Framework.objects.ObjectFactory(self._core, Framework.objects.MessageContainer),
      DirectoryItem         = Framework.objects.ObjectFactory(self._core, Framework.objects.DirectoryItem),
      PopupDirectoryItem    = Framework.objects.ObjectFactory(self._core, Framework.objects.PopupDirectoryItem),
      SearchDirectoryItem   = Framework.objects.ObjectFactory(self._core, Framework.objects.SearchDirectoryItem),
      InputDirectoryItem    = Framework.objects.ObjectFactory(self._core, Framework.objects.InputDirectoryItem),
      VideoItem             = Framework.objects.ObjectFactory(self._core, Framework.objects.VideoItem),
      WebVideoItem          = Framework.objects.ObjectFactory(self._core, Framework.objects.WebVideoItem),
      RTMPVideoItem         = Framework.objects.ObjectFactory(self._core, Framework.objects.RTMPVideoItem),
      WindowsMediaVideoItem = Framework.objects.ObjectFactory(self._core, Framework.objects.WindowsMediaVideoItem),
      PhotoItem             = Framework.objects.ObjectFactory(self._core, Framework.objects.PhotoItem),
      TrackItem             = Framework.objects.ObjectFactory(self._core, Framework.objects.TrackItem),
      Function              = Framework.objects.ObjectFactory(self._core, Framework.objects.Function),
      IndirectFunction      = Framework.objects.ObjectFactory(self._core, Framework.objects.IndirectFunction),
      PrefsItem             = Framework.objects.ObjectFactory(self._core, Framework.objects.PrefsItem),
      Redirect              = Framework.objects.ObjectFactory(self._core, Framework.objects.Redirect),
      ContextMenu           = Framework.objects.ObjectFactory(self._core, Framework.objects.ContextMenu),
      DataObject            = Framework.objects.ObjectFactory(self._core, Framework.objects.DataObject),
      MetadataSearchResult  = Framework.objects.ObjectFactory(self._core, Framework.objects.MetadataSearchResult),
      
      # New model interface objects
      ObjectContainer       = generate_model_interface_container_class(self._core, 'MediaContainer', child_types = [Framework.modelling.objects.ModelInterfaceObject, ProviderObject]),
      MovieObject           = self._generate_object(self._access_point.Movie),
      VideoClipObject       = self._generate_object(self._access_point.VideoClip),
      EpisodeObject         = self._generate_object(self._access_point.Episode),
      SeasonObject          = self._generate_object(self._access_point.Season, media=False),
      TVShowObject          = self._generate_object(self._access_point.TV_Show, media=False),
      MediaObject           = generate_class(MediaObject, self._core),
      PartObject            = generate_class(PartObject, self._core),
      ProviderObject        = generate_class(ProviderObject, self._core),
      
      # New convenience functions
      WebVideoURL           = self._web_video_url,
      RTMPVideoURL          = self._rtmp_video_url,
      WindowsMediaVideoURL  = self._windows_media_video_url
    )
      