#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os, weakref

class MediaContentsDirectory(object):
  def __init__(self, core, path, readonly=True):
    self._core = core
    self._path = path
    self._readonly = readonly
    
    if not self._core.storage.dir_exists(self._path):
      self._core.storage.make_dirs(self._path)
      
  def _item_path(self, item):
    if '/' in item or item == '..':
      raise KeyError('Invalid item name: %s' % str(item))
    return self._core.storage.join_path(self._path, item)
    
  def __contains__(self, item):
    return self._core.storage.file_exists(self._item_path(item))

  def __setitem__(self, item, contents):
    self._core.storage.save(self._item_path(item), contents)
    
  def __getitem__(self, item):
    path = self._item_path(item)
    if self._core.storage.file_exists(path):
      return self._core.storage.load(path)
    raise KeyError("The file named '%s' does not exist" % str(item))
    
  def __setitem__(self, item, data):
    if self._readonly:
      raise Framework.FrameworkException("The directory '%s' is read-only" % self._path)
    path = self._item_path(item)
    self._core.storage.save(path, data)
    
    
class MediaProxyContentsDirectory(MediaContentsDirectory):
  def __init__(self, core, path, readonly=True, el=None, parent=None):
    MediaContentsDirectory.__init__(self, core, path, readonly)
    self._proxies = dict()
    self._parent = weakref.proxy(parent)
    
    if el == None:
      return
      
    # If we were given an XML element, parse it
    for child in el:
      attrs = dict(child.attrib)
      if 'file' in attrs:
        p_type = 'LocalFile'
        p_value = attrs['file']
      elif 'media' in attrs:
        p_type = 'Media'
        # Store the extension in p_value
        p_value = str(attrs['media']).rsplit('.')[-1]
      else:
        continue
      p_name = attrs['name']
      if 'sort_order' in attrs:
        p_sort = attrs['sort_order']
      else:
        p_sort = None
      
      self._proxies[p_name] = (p_type, p_value, p_sort)
  
  
  def _element(self, tag='Directory', item_tag='Item'):
    el = self._core.data.xml.element(tag)
    for item in self._proxies:
      p_type, p_value, p_sort = self._proxies[item]
      
      item_el = self._core.data.xml.element(item_tag)
      item_el.set('name', item)
      if p_sort:
        item_el.set('sort_order', p_sort)
      
      if p_type == 'LocalFile':
        item_el.set('file', p_value)
      
      elif p_type == 'Media':
        name_hash = self._core.data.hashing.sha1(item)
        if p_value:
          name_hash += '.' + p_value
        item_el.set('media', name_hash)
      
      el.append(item_el)
    
    return el
    
        
  def _save(self):
    if self._parent and hasattr(self._parent, '_save'):
      self._parent._save()
        
        
  def __setitem__(self, item, value):
    if isinstance(value, Framework.modelling.attributes.ProxyObject):
      p_type = value._proxy_name
      p_sort = value._sort_order
      
      if p_type == 'LocalFile':
        p_value = value._data
        
      elif p_type == 'Media':
        name_hash = self._core.data.hashing.sha1(item)
        if value._ext != None:
          name_hash += '.' + value._ext
        MediaContentsDirectory.__setitem__(self, name_hash, value._data)
        p_value = value._ext
        
      else:
        raise ValueError("Invalid proxy type '%s'" % value._proxy_name)
      
      # Add the proxy to the dict
      self._proxies[item] = (p_type, p_value, p_sort)
      
      # Tell the parent object to save itself
      self._save()
    
    else:
      raise ValueError("Can't set object of type '%s'" % str(type(value)))
      
        
  def __getitem__(self, item):
    if item in self._proxies:
      p_type, p_value, p_sort = self._proxies[item]
      
      # We're accessing a local file proxy - load and return the contents of the file
      if p_type == 'LocalFile':
        return self._core.storage.load(p_value)
        
      # We're accessing a piece of media stored in the directory - call the superclass getitem method with the hash of the item name
      elif p_type == 'Media':
        name_hash = self._core.data.hashing.sha1(item)
        if p_value:
          name_hash += '.' + p_value
        return MediaContentsDirectory.__getitem__(self, name_hash)
    
    raise KeyError("No item found with name '%s'" % item)
    
    
  def __contains__(self, item):
    return item in self._proxies

    
  def __iter__(self):
    return self._proxies.__iter__()
    
    
  def _del(self, item):  
    # Check that the item exists in the proxy dict
    if item in self._proxies:
      p_type, p_value, p_sort = self._proxies[item]
      
      # If it's a media proxy, remove the file on disk
      if p_type == 'Media':
        # Calculate the SHA1 hash of the name
        name_hash = self._core.data.hashing.sha1(item)
        if p_value:
          name_hash += '.' + p_value
      
        self._core.storage.remove(self._core.storage.join_path(self._path, name_hash))
          
      # Remove the proxy
      del self._proxies[item]
      
    else:
      raise KeyError("No item found with name '%s'" % item)
  
  
  def __delitem__(self, item):
    self._del(item)
    self._save()  
    
    
  def validate_keys(self, valid_keys):
    # Check each proxy key to ensure it's in the list of valid keys, and remove it if not
    for key in self._proxies.keys():
      if key not in valid_keys:
        self._del(key)
    
    # Tell the parent object to save itself
    self._save()
        
  
    
class SubtitlesDirectory(object):
  
  def __init__(self, core, path):
    self._core = core
    self._path = path
    self._lang_dirs = dict()
    
    self._core.storage.ensure_dirs(self._path)
    self._load()
    
    
  def _load(self):
    # Check that the XML file exists
    path = self._path + '.xml'
    if not self._core.storage.file_exists(path):
      return
      
    data = self._core.storage.load(path)
    el = self._core.data.xml.from_string(data)
    
    # For each language in the file, create a contents directory object and allow it to parse the element
    for lang_el in el.xpath('//Language'):
      lang = lang_el.get('code')
      lang_path = self._core.storage.join_path(self._path, lang)
      proxy_dir = MediaProxyContentsDirectory(self._core, lang_path, readonly=False, el=lang_el, parent=self)
      self._lang_dirs[lang] = proxy_dir
      
    
  def __getitem__(self, lang):
    # Check that the language code is valid
    if not self._core.localization.language_code_valid(lang):
      raise KeyError("The language code '%s' is invalid")
      
    # If we don't have the language dir loaded, create a new object
    if lang not in self._lang_dirs:
      path = self._core.storage.join_path(self._path, lang)
      self._lang_dirs[lang] = MediaProxyContentsDirectory(self._core, path, readonly=False, parent=self)
      
    return self._lang_dirs[lang]
    
    
  def __contains__(self, item):
    return item in self._lang_dirs


  def __iter__(self):
    return self._lang_dirs.__iter__()
    
    
  def keys(self):
    return self._lang_dirs.keys()
    
    
  def _save(self):
    # Write an XML file containing all languages and proxy info
    root_el = self._core.data.xml.element('Subtitles')
    for lang in self._lang_dirs:
      lang_dir = self._lang_dirs[lang]
      el = lang_dir._element('Language', 'Subtitle')
      el.set('code', lang)
      root_el.append(el)
    
    data = self._core.data.xml.to_string(root_el)
    path = self._path + '.xml'
    self._core.storage.save(path, data)
    
    
    
class MediaPart(object):
  def __init__(self, core, el):
    self._core = core
    
    self.file = str(el.get('file'))
    self.openSubtitleHash = str(el.get('openSubtitleHash'))
    self.plexHash = str(el.get('hash'))
    if el.get('size'):
      self.size = long(el.get('size'))
    
    try:
      self._path = self._core.storage.join_path(self._core.app_support_path, 'Media', 'localhost', self.plexHash[0], self.plexHash[1:] + '.bundle')
    
    except:
      self._path = None
      self._core.log.error('We seem to be missing the hash for media item [%s]', self.file)
    
    if self._path:
      self.thumbs = MediaContentsDirectory(self._core, self._core.storage.join_path(self._path, 'Contents', 'Thumbnails'))
      self.art = MediaContentsDirectory(self._core, self._core.storage.join_path(self._path, 'Contents', 'Art'))
      self.subtitles = SubtitlesDirectory(self._core, self._core.storage.join_path(self._path, 'Contents', 'Subtitles'))

      
class MediaItem(object):
  def __init__(self, core, el):
    self._core = core
    self.parts = []
    for child in el:
      if child.tag == 'MediaPart':
        part = MediaPart(self._core, child)
        self.parts.append(part)
        
class MediaDict(dict):
  def __contains__(self, item):
    ret = dict.__contains__(self, item)
    if ret:
      return True
    else:
      return dict.__contains__(self, str(item))
      
  def __getitem__(self, item):
    if dict.__contains__(self, str(item)):
      return dict.__getitem__(self, str(item))
    return dict.__getitem__(self, item)
        
class MediaTree(object):
  def __init__(self, core, el, level_names=[]):
    self._core = core
    self.items = []
    self.title = el.get('title')
    
    level_name = None
    subitems = None
    next_level_names = []
    
    if len(level_names) > 0:
      level_name = level_names[0]
      if len(level_names) > 1:
        next_level_names = level_names[1:]
      subitems = MediaDict()
      
    for child in el:
      if child.tag == 'MetadataItem':
        if subitems == None:
          print "No subitems can be set for level", level_name
          continue
        index = child.get('index')
        subitem = MediaTree(self._core, child, next_level_names)
        subitems[index] = subitem
      elif child.tag == 'MediaItem':
        item = MediaItem(self._core, child)
        self.items.append(item)
      else:
        self._core.log.error('Unknown tag: %s', child.tag)
        
    if level_name and subitems and len(subitems) > 0:
      setattr(self, level_name, subitems)


class MediaObject(object):
  """
    A MediaObject represents a media item discovered by PMS and encapsulates any information
    provided by the server. It is intended to provide hints to metadata agents when
    finding metadata to download.
  """
  
  _attrs = dict()
  _model_name = None
  _parent_model_name = None
  _parent_link_name = None
  _parent_set_attr_name = None
  _type_id = 0
  _level_names = []
  
  def __init__(self, access_point, **kwargs):
    self._access_point = access_point
    self.primary_agent = None
    self.primary_metadata = None
    self.guid = None
    self.filename = None
    self.parent_metadata = None
    self.parentGUID = None
    self.tree = None
    self.id = None
    self.plexHash = None
    
    cls = type(self)
    for name in cls._attrs:
      setattr(self, name, cls._attrs[name])
    
    for name in kwargs:
      if hasattr(self, name):
        setattr(self, name, kwargs[name])

    # Get the media tree if we got an ID passed down.
    if self.id != None:
      try:
        setattr(self, 'tree', Media.TreeForDatabaseID(self.id, type(self)._level_names))
      except:
        self._access_point._core.log_except(None, "Exception when constructing media object")

    # Load primary agent's metadata.
    if self.primary_agent != None and self.guid != None:
      primary_access_point = self._access_point._accessor.get_access_point(self.primary_agent, read_only=True)
      model_cls = getattr(primary_access_point, cls._model_name)
      self.primary_metadata = model_cls[self.guid]
      
    # Load the parent's metadata.
    if self.parentGUID and cls._parent_model_name:
      model_cls = getattr(self._access_point, cls._parent_model_name)
      self.parent_metadata = model_cls[self.parentGUID]
      
    del self.parentGUID
    
  def __getattr__(self, name):
    if hasattr(self, 'tree') and hasattr(self.tree, name):
      return getattr(self.tree, name)
    else:
      return object.__getattr__(self, name)
      
        
class Media(object):
  _core = None
  
  @classmethod
  def _class_named(cls, media_type):
    if hasattr(cls, media_type):
      media_class = getattr(cls, media_type)
      if isinstance(media_class, type):
        return media_class
        
  @classmethod
  def TreeForDatabaseID(cls, dbid, level_names=[], host='127.0.0.1'):
    xml_str = cls._core.networking.http_request('http://%s:32400/library/metadata/%s/tree' % (host, str(dbid)), cacheTime=0, immediate=True)
    xml_obj = cls._core.data.xml.from_string(xml_str)
    tree = MediaTree(cls._core, xml_obj[0], level_names)
    if tree.title == None:
      xml_str = cls._core.networking.http_request('http://%s:32400/library/metadata/%s' % (host, str(dbid)), cacheTime=0, immediate=True)
      xml_obj = cls._core.data.xml.from_string(xml_str)
      try:
        tree.title = xml_obj.xpath('//Video')[0].get('title')
      except:
        cls._core.log.error('Unable to set title for metadata item %s', str(dbid))
    return tree
      
  class Movie(MediaObject):
    _model_name = 'Movie'
    _type_id = 1
    _attrs = dict(
      primary_metadata = None,
      name = None,
      openSubtitlesHash = None,
      year = None,
      duration = None,
    )
    
  class TV_Show(MediaObject):
    _model_name = 'TV_Show'
    _type_id = 2
    _attrs = dict(
      show = None,
      season = None,
      episode = None,
      name = None,
      openSubtitlesHash = None,
      year = None,
      duration = None,
    )
    _level_names = ['seasons', 'episodes']
    
  class Album(MediaObject):
    _model_name = 'Album'
    _parent_model_name = 'Artist'
    _parent_link_name = 'artist'
    _parent_set_attr_name = 'albums'
    _type_id = 9
    _attrs = dict(
      artist = None,
      album = None,
      track = None,
      index = None,
      parentGUID = None
    )
    _level_names = ['tracks']
    
  class Artist(MediaObject):
    _model_name = 'Artist'
    _type_id = 8
    _attrs = dict(
      artist = None,
      album = None,
      track = None,
      index = None
    )
    _level_names = ['albums', 'tracks']
    
class MetadataModelClassWrapper(object):
  def __init__(self, cls):
    self._cls = cls
    
  @property
  def _core(self):
    return self._cls._core
    
  @property
  def _access_point(self):
    return self._cls._access_point
    
  def search(self, lang, **kwargs):
    media_class = Media._class_named(self._cls.__name__)
    if media_class == None:
      return
    media_type = media_class._type_id
    identifier = self._access_point._identifier
    return self._core.messaging.call_external_function(
      '..system',
      '_AgentService:Search',
      kwargs = dict(
        identifier = identifier,
        mediaType = media_type,
        lang = lang,
        **kwargs
      )
    )
  
  def __getattr__(self, name):
    return getattr(self._cls, name)
    
  def __setattr__(self, name, value):
    if name[0] != '_':
      setattr(self._cls, name, value)
    else:
      object.__setattr__(self, name, value)
    
  def __getitem__(self, name):
    return self._cls[name]
    
  def __call__(self, *args, **kwargs):
    return self._cls(*args, **kwargs)
    

class MetadataAccessPointWrapper(object):
  def __init__(self, access_point):
    self._access_point = access_point
    
  @property
  def _core(self):
    return self._access_point._core
    
  def __getattr__(self, name):
    metadata_class = getattr(self._access_point, name)
    return MetadataModelClassWrapper(metadata_class)
    
  def __getitem__(self, name):
    new_access_point = self._access_point[name]
    return MetadataAccessPointWrapper(new_access_point)
  


class AgentKit(Framework.bases.BaseKit):
  """
    The AgentKit API class handles commmunication between plug-ins and the agent service,
    responding to incoming requests and forwarding them to custom Agent classes as appropriate.
  """
  
  _agents = list()
  _shared_instance = None
  
  def _init(self):
    # Generate the agent classes
    self.TV_Shows = BaseAgent.generate(self._core, 'TV_Shows', Media.TV_Show)
    self.Movies = BaseAgent.generate(self._core, 'Movies', Media.Movie)
    self.Artist = BaseAgent.generate(self._core, 'Artist', Media.Artist)
    self.Album = BaseAgent.generate(self._core, 'Album', Media.Album)
    
    self._setup_complete = False
    self._pushing_info_lock = self._core.runtime.lock()
    type(self)._shared_instance = self
    Media._core = self._core
    
    self._globals = dict(
      Media       = Media,
      Metadata    = self._metadata_access_point_wrapper,
    )
    
  def _setup(self):
    if self._setup_complete:
      return
      
    # Create a model access point
    self._accessor = self._core._metadata_model_accessor
    self._access_point = self._accessor.get_access_point(self._core.identifier)
    
    # Expose functions via the messaging component for access by the agent service
    self._core.messaging.expose_function(self._search, '_AgentKit:Search')
    self._core.messaging.expose_function(self._update, '_AgentKit:UpdateMetadata')
    self._core.messaging.expose_function(self._erase, '_AgentKit:EraseMetadata')
    
    self._access_point_wrapper = MetadataAccessPointWrapper(self._access_point)

  @property
  def _metadata_access_point_wrapper(self):
    self._setup()
    return self._access_point_wrapper
    
  def _push_agent_info(self):
    self._pushing_info_lock.acquire()
    try:
      agents = []
      for agent in AgentKit._agents:
      
        media_types = []
        for media_class in agent._media_types:
          media_types.append(media_class._model_name)
      
        should_add = True
        for lang in agent.languages:
          if not self._core.localization.language_code_valid(lang):
            self._core.log_error(None, "The agent named '%s' contains the invalid language code '%s' and will not be exposed to the media server.", agent.name, lang)
            should_add = False
            break
      
        if should_add:
          info_dict = dict(
            name = agent.name,
            languages = agent.languages,
            media_types = media_types,
            contributes_to = agent.contributes_to,
            accepts_from = agent.accepts_from,
            primary_provider = agent.primary_provider,
            fallback_agent = agent.fallback_agent,
            prefs = self._core.storage.file_exists(self._core.storage.join_path(self._core.bundle_path, 'Contents', 'DefaultPrefs.json'))
          )
          agents.append(info_dict)
      
      if len(agents) > 0:
        self._core.log.debug("Updating agent information: %s", agents)
      
        self._core.messaging.call_external_function(
          '..system',
          '_AgentService:UpdateInfo',
          kwargs = dict(
            identifier = self._core.identifier,
            agent_info = agents
          )
        )
    finally:
      self._pushing_info_lock.release()
    
  def _search(self, media_type, lang, manual, kwargs):
    """
      Received a search request - find an agent that handles the given media type, create a
      Media object from the given arguments and forward the request to the agent instance.
    """
    try:
      cls = Media._class_named(media_type)
      for agent in AgentKit._agents:
        if cls in agent._media_types:
          try:
            self._core.log.info("Searching for matches for "+str(kwargs))
            
            # Check to see if the 'manual' arg was passed
            media = cls(self._access_point, **kwargs)
            results = Framework.objects.MediaContainer(self._core)
            
            if Framework.utils.function_accepts_arg(agent.search, 'manual'):
              agent.search(results, media, lang, manual)
            else:
              agent.search(results, media, lang)
              
            results.Sort('year')
            results.Sort('score', descending=True)
            return results
          
          except:
            self._core.log_except(None, "Exception in the search function of agent named '%s', called with keyword arguments %s", agent.name, str(kwargs))
    except:
      self._core.log_except(None, "Exception finding an agent for type %s", media_type)

  def _update(self, media_type, guid, id, lang, dbid=None, parentGUID=None, force=False):
    """
      Received an update request. Find the agent that handles the given media type, get a
      metadata object with the specified model & GUID, instruct the agent to update it,
      then serialize it before returning.
    """
    try:
      cls = Media._class_named(media_type)
      for agent in AgentKit._agents:
        if cls in agent._media_types:
          metadata_cls = getattr(self._access_point, cls._model_name)
          obj = metadata_cls[guid]

          if id != None:
            if obj._id == None:
              obj._id = id
            elif obj._id != id:
              self._core.log.debug("Whacking existing data because the ID changed (%s -> %s)" % (obj._id, id))
              obj = metadata_cls()
              obj._uid = guid
              obj._id = id
            
          media = None
          try:
            if dbid:
              media = Media.TreeForDatabaseID(dbid, level_names=cls._level_names)
          except:
            self._core.log_except(None, "Exception when constructing media object for dbid %s", dbid)
            
          if parentGUID and cls._parent_model_name and cls._parent_link_name:
            if getattr(obj, cls._parent_link_name) == None:
              parent_model_cls = getattr(self._access_point, cls._parent_model_name)
              parent_obj = parent_model_cls[parentGUID]
              setattr(obj, cls._parent_link_name, parent_obj)
              if cls._parent_set_attr_name:
                child_set = getattr(parent_obj, cls._parent_set_attr_name)
                child_set.add(obj)
                parent_obj._write()
              
          try:
            if Framework.utils.function_accepts_arg(agent.update, 'force'):
              agent.update(obj, media, lang, force)
            else:
              agent.update(obj, media, lang)
          except:
            self._core.log_except(None, "Exception in the update function of agent named '%s', called with guid '%s'", agent.name, guid)
          obj._write()
    except:
      self._core.log_except(None, "Exception updating %s instance '%s'", media_type, guid)
      
  def _erase(self, media_type, guid):
    cls = Media._class_named(media_type)
    for agent in AgentKit._agents:
      if cls in agent._media_types:
        metadata_cls = getattr(self._access_point, cls._model_name)
        metadata_cls.erase(guid)
    
  @classmethod
  def _register_agent_class(cls, agent_class):
    """
      Registers an instance of a newly created agent class with AgentKit.
    """
    cls._shared_instance._setup()
    cls._agents.append(agent_class())
    cls._shared_instance._push_agent_info()
   
   
class AgentMetaclass(type):
  base_class = None
  def __new__(meta, classname, bases, dct):
    """
      Called when creating a new agent class - registers the new class automatically with
      AgentKit. Make sure we don't call this when defining BaseAgent or its direct subclasses.
    """
    cls = type.__new__(meta, classname, bases, dct)
    if not (AgentMetaclass.base_class in bases or object in bases):
      if cls._core:
        cls._core.log.debug('Creating new agent class called %s', classname)
      AgentKit._register_agent_class(cls)
    return cls 
    
class BaseAgent(object):

  __metaclass__ = AgentMetaclass
  _class_media_types = []
  _core = None
  
  name = 'Unnamed Agent'
  languages = []
  primary_provider = True
  contributes_to = None
  accepts_from = None
  fallback_agent = None
  
  def __init__(self):
    self._media_types = list(type(self)._class_media_types)

  # Functions that agents should implement
  def search(self, media, lang): pass
  def update(self, metadata, lang): pass
    
  @classmethod
  def generate(cls, core, name, media_type):
    """
      Generates a new agent class with the given name that handles the given media type (to be used
      as a base class for custom agents)
    """
    media_types = list(cls._class_media_types)
    media_types.append(media_type)
    return type(name, (cls,), dict(__metaclass__ = cls.__metaclass__, _class_media_types = media_types, _core=core))

# We need to set this here because BaseAgent doesn't exist when AgentMetaclass is defined.
AgentMetaclass.base_class = BaseAgent