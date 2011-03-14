import Framework
import urllib, os


class Pref(object):
  def __init__(self, pref_type, label, default_value=None, secure=False):
    self.type = pref_type
    self.label = label
    self.default_value = default_value
    self.value = self.default_value
    self.secure = secure
    self.valid = True
    
  def reset(self):
    self.value = self.default_value
    
  def string_value(self):
    if self.value == None:
      return ''
    return str(self.value)
    
  def string_default_value(self):
    return str(self.default_value)
    
  def set_value(self, value):
    self.value = value
    
  def get_value(self):
    return self.value
    
  def info_dict(self, core, locale, **kwargs):
    d = dict(
      label = core.localization.localize(self.label, locale),
      type = self.type,
      value = self.string_value(),
      default = self.string_default_value()
    )
    if self.secure:
      d['secure'] = 'true'
    else:
      d['secure'] = 'false'
    d.update(**kwargs)
    return d
    
class TextPref(Pref):
  def __init__(self, label, default_value, options=[], secure=False):
    if default_value == None:
      default_value = ''
    Pref.__init__(self, 'text', label, default_value, secure) 
    self.options = options
    
  def info_dict(self, core, locale, **kwargs):
    return Pref.info_dict(self, core, locale,
      option = ','.join(self.options)
    )
  
  def set_value(self, value):
    if value == None or len(value) == 0:
      self.value = None
    else:
      self.value = value

    
class BooleanPref(Pref):
  def __init__(self, label, default_value, secure=False):
    default_value = self.test_bool(default_value)
    Pref.__init__(self, 'bool', label, default_value, secure)

  def test_bool(self, value):
    return value == True or value == 1 or value == '1' or str(value).lower() == 'true'
    
  def string_value(self):
    if self.value == True:
      return 'true'
    else:
      return 'false'
  
  def string_default_value(self):
    if self.default_value == True:
      return 'true'
    else:
      return 'false'
      
  def set_value(self, value):
    self.value = self.test_bool(value)

class EnumPref(Pref):
  def __init__(self, label, default_value, values=[], secure=False):
    if default_value not in values:
      if len(values) > 0:
        default_value = values[0]
      else:
        default_value = None
    Pref.__init__(self, 'enum', label, default_value, secure)
    self.values = values
    
  def set_value(self, value):
    try:
      int_val = int(value)
      if int_val < len(self.values):
        self.value = self.values[int_val]
    except:
      pass
      
  def info_dict(self, core, locale, **kwargs):
    value_labels = []
    for value in self.values:
      value_labels.append(core.localization.localize(value, locale))
    return Pref.info_dict(self, core, locale,
      values = '|'.join(value_labels)
    )
    
  def string_value(self):
    return str(self.values.index(self.value))
    
  def string_default_value(self):
    return str(self.values.index(self.default_value))
      

class PrefsKit(Framework.bases.BaseKit):
  def _init(self):
    self._core.storage.make_dirs(self._core.storage.join_path(self._core.plugin_support_path, 'Preferences'))
    self._prefs_json = None
    self._prefs = dict()
    self._pref_names = list() # We maintain a separate names list so we know in which order to return prefs for the GUI 
    self._user_prefs_mtime = None
    
    # If we're creating a context, grab the contents of DefaultPrefs.json from the global kit
    if self._context and self._global_kit._prefs_json != None:
      self._prefs_json = list(self._global_kit._prefs_json)
    
    # If we're being created under the service policy, defer loading until later so the correct identifier can be set
    if isinstance(self._policy_instance, Framework.policies.ServicePolicy):
      self._identifier = None
    else:
      self._identifier = self._core.identifier
      self._load()

      # If we're not creating a context (i.e. this will be the global kit object) add a request handler
      if self._context == None:
        self._core.runtime.add_private_request_handler(self._prefs_request_handler)

      self._save_user_prefs()

      
  def _load(self):
    # Create pref objects from the defaults
    self._load_default_prefs()
    
    # If we're not creating a context (i.e. this will be the global kit object) load the user preferences from disk
    if self._context == None:
      self._load_user_prefs()
    
    
  def _prefs_request_handler(self, pathNouns, kwargs, context):
    if len(pathNouns) == 1 and pathNouns[0] == 'prefs':
      return self._container(context=context)
      
    if len(pathNouns) == 2 and pathNouns[0] == 'prefs' and pathNouns[1] == 'set':
      for name in kwargs:
        if name in self._prefs:
          self._prefs[name].set_value(kwargs[name])
      if len(kwargs) > 0:
        self._save_user_prefs()
      result = self._core.host.call_named_function('ValidatePrefs', context=context)
      if result != None:
        return result
      else:
        return ''
    
    if len(pathNouns) == 2 and pathNouns[0] == 'prefs' and pathNouns[1] == 'list':
      return self._container(show_values=False)
        
        
  def _container(self, show_values=True, context=None):
    mc = Framework.objects.MediaContainer(self._core)
    
    if context == None:
      context = self._context
    if context and Framework.constants.header.language in context.headers:
      locale = context.headers[Framework.constants.header.language]
    else:
      locale = None
    for name in self._pref_names:
      pref = self._prefs[name]
      info_dict = pref.info_dict(self._core, locale)
      
      if not show_values and 'value' in info_dict:
        del info_dict['value']
      
      obj = Framework.objects.XMLObject(self._core, tagName='Setting', id=name, **info_dict)
      mc.Append(obj)
    return mc
    
    
  def _load_prefs_json(self, prefs_file):
    if not self._core.storage.file_exists(prefs_file):
      return
  
    json = self._core.storage.load(prefs_file)
    json_array = self._core.data.json.from_string(json)
    self._prefs_json.extend(json_array)
    
    self._core.log.debug("Loaded preferences from %s", os.path.split(prefs_file)[1])
    
    
  def _load_default_prefs(self):
    # Load the JSON if we don't have it already
    if self._prefs_json != None:
      return
      
    self._prefs_json = []
    
    # Load the plug-in's DefaultPrefs.json file if we're not running under the service policy
    if not isinstance(self._policy_instance, Framework.policies.ServicePolicy):
      default_prefs_path = self._core.storage.join_path(self._core.bundle_path, 'Contents', 'DefaultPrefs.json')
      self._load_prefs_json(default_prefs_path)
    
    # Check to see if a linked URL service exists for this plug-in
    for service_name in self._core.services.url_services:
      service = self._core.services.url_services[service_name]
      if service.linked_plugin == self._identifier:
        
        # If a linked service is found, attempt to load the service prefs
        service_prefs_path = self._core.storage.join_path(service.path, 'ServicePrefs.json')
        self._load_prefs_json(service_prefs_path)
          
    # Iterate through the dict loaded from the JSON files
    for pref in self._prefs_json:
      name = pref['id']
      
      # If a pref object with this name doesn't exist, try to create one
      if name not in self._pref_names:
        # Grab the type, default value and label
        pref_type = pref['type']
        pref_secure = 'secure' in pref and (pref['secure'] == True or str(pref['secure']).lower() == 'true')
        
        if 'default' in pref:
          pref_default = pref['default']
        else:
          pref_default = None
        pref_label = pref['label']
        
        # Find a suitable class...
        if pref_type == 'text':
          
          # Text prefs support options, so parse these too
          if 'option' in pref:
            pref_option = pref['option'].split(',')
          else:
            pref_option = []
          self._prefs[name] = TextPref(pref_label, pref_default, pref_option, pref_secure)
        
        elif pref_type == 'bool':
          self._prefs[name] = BooleanPref(pref_label, pref_default, pref_secure)
          
        elif pref_type == 'enum':
          # Enum prefs have a set of values - grab these
          if 'values' in pref:
            pref_values = pref['values']
          else:
            pref_values = []
          self._prefs[name] = EnumPref(pref_label, pref_default, pref_values, pref_secure)
          
        # Whoops - no class found. Ignore this pref.
        else:
          continue
          
        # Add the name to the names list
        self._pref_names.append(name)
  
  def _user_prefs_path(self):
    return self._core.storage.join_path(self._core.plugin_support_path, 'Preferences', self._identifier + '.xml')
    
  def _load_user_prefs(self):
    # Check whether the prefs file exists
    prefs_file = self._user_prefs_path()
    if not self._core.storage.file_exists(prefs_file):
      return
    
    # Load the prefs file
    prefs_xml_str = self._core.storage.load(prefs_file)
    prefs_xml = self._core.data.xml.from_string(prefs_xml_str)
    
    # Iterate through each element
    for el in prefs_xml:
      pref_name = str(el.tag)
      if el.text == None:
        pref_value = None
      else:
        pref_value = str(el.text)
      
      # If a pref exists with this name, set its value
      if pref_name in self._prefs:
        self._prefs[pref_name].set_value(pref_value)
        
    if self._user_prefs_mtime == None:
      self._core.log.debug("Loaded the user preferences for %s", self._identifier)
    else:
      self._core.log.debug("Reloaded the user preferences for %s", self._identifier)
    
    self._user_prefs_mtime = self._current_user_prefs_mtime()
    
  def _current_user_prefs_mtime(self):
    path = self._user_prefs_path()
    if self._core.storage.file_exists(path):
      return self._core.storage.last_modified(path)
    else:
      return 0
  
  def _save_user_prefs(self):
    el = self._core.data.xml.element('PluginPreferences')
    
    for name in self._prefs:
      el.append(self._core.data.xml.element(name, self._prefs[name].string_value()))
      
    prefs_xml = self._core.data.xml.to_string(el)
    prefs_file = self._user_prefs_path()
    self._core.storage.save(prefs_file, prefs_xml)
    self._core.log.debug("Saved the user preferences")
  
  def __getitem__(self, name):
    # Reload the user preferences if the file's modification time has changed
    if self._user_prefs_mtime != self._current_user_prefs_mtime():
      self._load_user_prefs()
      
    if name in self._prefs:
      if self._prefs[name].valid:
        return self._prefs[name].get_value()
      raise Framework.UnauthorizedException
    raise KeyError("No preference named '%s'" % name)
    
  def Get(self, name):
    self._core.log.warn("Prefs.Get() is deprecated. Use Prefs[] instead.")
    return self[name]
    
  def _requires_context(self, context):
    return Framework.constants.header.preferences in context.headers or Framework.constants.header.transaction_id in context.headers or Framework.constants.header.language in context.headers
    
  def _begin_context(self):
    if Framework.constants.header.preferences in self._context.headers:
      request_prefs = self._context.headers[Framework.constants.header.preferences].split('&')
      contextual_prefs = {}
      for request_pref in request_prefs:
        if '=' in request_pref:
          name, value = request_pref.split('=')
          contextual_prefs[name] = urllib.unquote(value)
      self._core.log_debug(self._txn_id, "Setting contextual prefs: %s" % contextual_prefs)
      for name in self._prefs:
        if name in contextual_prefs:
          self._prefs[name].set_value(contextual_prefs[name])
        elif self._prefs[name].secure == True:
          self._prefs[name].valid = False
    
  def _end_context(self, response_headers):
    pass
