#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework

    
class Messaging(Framework.bases.BaseComponent):
  """
    The messaging component manages all message-related features of the framework.
  """
  
  def _init(self):
    self._functions = dict()
    self._responders = dict()
    
    self._core.runtime.add_private_request_handler(self._handle_messaging_request)
    
    if self._core.identifier != self._core.config.system_bundle_identifier:
      self._send_system_message('clear_events')
    
    
  def _handle_messaging_request(self, pathNouns, kwargs, context):
    """
      Private request handler for messaging calls.
    """
    if len(pathNouns) > 3 and (pathNouns[0] == 'plugins' and pathNouns[1] == self._core.identifier and pathNouns[2] == 'messaging'):
      pathNouns = pathNouns[3:]
      count = len(pathNouns)
      
      # Function calls
      if pathNouns[0] == 'function' and count == 4:

        # Get the function name
        name = Framework.utils.safe_decode(pathNouns[1])
        
        # Unpack the arguments & keyword arguments
        args = Framework.utils.unpack(pathNouns[2])
        kwargs = Framework.utils.unpack(pathNouns[3])
        
        return self._core.messaging._process_function_call(name, args, kwargs)
      
      
      elif pathNouns[0] == 'event' and count == 4:
        
        # Get the event key
        key = Framework.utils.safe_decode(pathNouns[1])
        
        # Unpack the arguments & keyword arguments
        args = Framework.utils.unpack(pathNouns[2])
        kwargs = Framework.utils.unpack(pathNouns[3])
        
        self._core.messaging._process_event(key, args, kwargs)
        
      
      elif pathNouns[0] == 'wait' and count == 1:
        return Framework.utils.pack(True)
  
  
  def generate_messaging_url(self, target, key, *args):
    """
      Generates a messaging URL with the given key and arguments.
    """
    url = 'http://127.0.0.1:32400/:/plugins/%s/messaging/%s' % (target, key)
    if len(args) > 0:
      url += '/' + '/'.join(args)
    return url
    
  
  def _generate_system_url(self, key, *args):
    """
      Generates a message system URL with the given arguments.
    """
    url = 'http://127.0.0.1:32400/system/messaging/%s/%s' % (key, self._core.identifier)
    if len(args) > 0:
      url += '/' + '/'.join(args)
    return url
    
  def _system_request(self, key, args):
    try:
      url = self._generate_system_url(key, *args)
      self._core.networking.http_request(url = url, cacheTime=0, timeout=None, immediate=True)
    except:
      self._core.log.error('Unable to reach the system bundle.')
    
  def _send_system_message(self, key, *args):
    """
      Sends an asynchronous message to the system bundle
    """
    
    self._core.runtime.create_thread(
      self._system_request,
      key = key,
      args = args,
    )
    
    
  def expose_function(self, f, name):
    """
      Makes a function remotely callable via the dispatch node.
    """
    if self._core.config.log_internal_component_usage or name[0] != '_':
      self._core.log.debug("Exposing function %s for remote access", f.__name__)
    self._functions[name] = f
  
  
  def call_external_function(self, identifier, name, args=[], kwargs={}, txn_id=None):
    """
      Calls a function in a remote plug-in and returns its result
    """
    target = self._core.runtime._expand_identifier(identifier)

    encoded_name = Framework.utils.safe_encode(name)
    packed_args = Framework.utils.pack(args)
    packed_kwargs = Framework.utils.pack(kwargs)

    url = self.generate_messaging_url(target, 'function', encoded_name, packed_args, packed_kwargs)
    
    try:
      packed_result = self._core.networking.http_request(url, cacheTime=0, timeout=None, immediate=True).content
      result = Framework.utils.unpack(packed_result)
      if hasattr(result, '_bind'):
        result._bind(self._core)
      return result
    except:
      self._core.log_exception('Exception in call_external_function')
      #TODO: Raise, a 404 will mean an incorrect identifier
      return None


  def _process_function_call(self, name, args, kwargs):
    """
      Processes an incoming function call from another plug-in. Call the given function, then send
      the response back to the message service, with the given callback ID.
    """
    if name in self._functions:
      try:
        result = self._functions[name](*args, **kwargs)
        if hasattr(result, '_release'):
          result._release()
        return Framework.utils.pack(result)
      except:
        self._core.log_except(None, 'Exception in _process_function_call')
        #TODO: Return exception data
        return None
    else:
      #TODO: Return "no function" message 
      return None
    

  def register_for_notification(self, f, identifier, name):
    """
      Registers for a framework notification event of a given name generated by a given plug-in.
      Uses the underlying event functionality, but provides a safe way of calling via MessageKit.
    """
    self.register_for_event(f, self._make_notification_key(self._core.runtime._expand_identifier(identifier), name))
    
    
  def send_notification(self, name, args=[], kwargs={}):
    """
      Sends a framework notification event via the message hub. Uses the underlying event
      functionality, but provides a safe way of calling via MessageKit.
    """
    self.send_event(self._make_notification_key(self._core.identifier, name=name), args, kwargs)
    
    
  def _make_notification_key(self, identifier, name):
    """
      Returns an event key for a framework notification event generated using the given identifier and name
    """
    return "Notification:%s:%s" % (identifier, name)


  def register_for_event(self, f, key):
    """
      Adds a responder for the given event key. Events received matching the key will be dispatched to the
      function provided.
    """
    if self._core.config.log_internal_component_usage or key[0] != '_':
      self._core.log.debug("Adding function '%s' as a responder for the event %s", f.__name__, key)
    if key not in self._responders:
      self._responders[key] = []
    self._responders[key].append(f)
    
    encoded_key = Framework.utils.safe_encode(key)
    self._send_system_message('register_for_event', encoded_key)
    
    
  def send_event(self, key, args=[], kwargs={}):
    """
      Sends a generic event via the message hub.
    """
    packed_args = Framework.utils.pack(args)
    packed_kwargs = Framework.utils.pack(kwargs)
    encoded_key = Framework.utils.safe_encode(key)
    self._send_system_message('broadcast_event', encoded_key, packed_args, packed_kwargs)
    
  
  def _process_event(self, key, args, kwargs):
    """
      Processes an incoming event. If there are responders registered, spawn each one in a separate thread.
    """
    if key in self._responders:
      if self._core.config.log_internal_component_usage or key[0] != '_':
        self._core.log.debug("Processing event %s", key)
      for f in self._responders[key]:
        self._core.runtime.create_thread(f, args=args, kwargs=kwargs, important=True)
        
        
  def wait_for_presence(self, identifier, timeout=None):
    """
      Causes the current thread to block until the given plug-in has started.
    """
    url = self.generate_messaging_url(target, 'wait')
    try:
      self._core.networking.http_request(url, cacheTime=0, timeout=timeout, immediate=True)
      return True
    except:
      return False
      
    
  def plugin_list(self):
    """
      Returns a list of plug-ins known to the media server.
    """
    xml_str = self._core.networking.http_request('http://127.0.0.1:32400/:/plugins', timeout=None, cacheTime=0).content
    xml = self._core.data.xml.from_string(xml_str)
    result = list()
    for plugin in xml:
      identifier = plugin.attrib['identifier']
      if len(identifier) > 0:
        result.append(identifier)
    return result