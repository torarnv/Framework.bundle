#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import plistlib, re
import urllib


class URLService(Framework.bases.BaseKit):
  
  def _init(self):
    self._service_hosts = {}
  
    # If we're not creating a context (i.e. this will be the global kit object), and we're not running under the service policy, add a request handler
    if self._context == None and not isinstance(self._policy_instance, Framework.policies.ServicePolicy):
      self._core.runtime.add_private_request_handler(self._service_request_handler)
      
  def _service_request_handler(self, pathNouns, kwargs, context):
    if len(pathNouns) == 5 and pathNouns[2] == 'urlservice_function':
      # Extract arguments from the request
      url = Framework.utils.unpack(pathNouns[3])
      f_name = pathNouns[4]
      f_args = Framework.utils.unpack(kwargs['args'])
      f_kwargs = Framework.utils.unpack(kwargs['kwargs'])
        
      # Call the named function and return the result
      self._core.log_debug(self._txn_id, "Calling function %s for '%s'", f_name, url)
      result = self._call_named_urlservice_function_for_url(f_name, url, f_args, f_kwargs)
      
      return result
      

  def _service_for_url(self, url):
    """ Find the path to a service that can handle the given URL """
    for service_name in self._core.services.url_services:
      service = self._core.services.url_services[service_name]
      if re.match(service.pattern, url, re.IGNORECASE):
        return service
    self._core.log_debug(self._txn_id, "No service found for URL '%s'", url)
    return None
    
    
  def _generate_urlservice_callback_path(self, url, function, args, kwargs, indirect):
    """ Generate a callback path for a function inside a service """
    path = "/:/plugins/%s/urlservice_function/%s/%s?args=%s&kwargs=%s" % (
      self._core.identifier,
      Framework.utils.pack(url),
      function.__name__,
      Framework.utils.pack(args),
      Framework.utils.pack(kwargs)
    )
    if indirect:
      path = Framework.api.objectkit.indirect_callback_string(path + "&indirect=1")
    return path
    
    
  def _call_named_urlservice_function_for_url(self, fname, url, f_args=[], f_kwargs={}):
    """ Call a named function in the service for a given URL with the given arguments and return the result """
    service = self._service_for_url(url)
    if service == None:
      return None
      
    # Create a new code host if one doesn't already exist for this service
    if service.name not in self._service_hosts:
      service_code_path = self._core.storage.join_path(service.path, 'ServiceCode.pys')
      code = self._core.loader.load(service_code_path)
      host = Framework.code.CodeHost(self._core, service_code_path, Framework.policies.ServicePolicy)
      host.execute(code)
      self._service_hosts[service.name] = host
      
      # If the service has a linked plug-in, load preferences
      if service.linked_plugin:
        prefs_kit = host.environment['Prefs']
        prefs_kit._identifier = service.linked_plugin
        prefs_kit._load()
        
    # Otherwise, use the host we have already
    else:
      host = self._service_hosts[service.name]
    
    
    # Substitute the default Function() and IndirectFunction() functions with service path generators
    def callback_path_generator(function, indirect=False, *args, **kwargs):
      return self._generate_urlservice_callback_path(url, function, args, kwargs, indirect)
      
    host.environment['Callback'] = callback_path_generator
    result = host.call_named_function(fname, self._context, *f_args, **f_kwargs)
    del host
    return result
    
    
  def MetadataItemForURL(self, url, add_items_automatically=True):
    """
      Calls MetadataItemForURL in the appropriate URL service and returns the result, setting
      the original URL on the object and populating media items if none were provided.
    """
    metadata = self._call_named_urlservice_function_for_url('MetadataItemForURL', url, [url])
    if metadata == None:
      return None
    setattr(metadata, 'url', url)
    if not metadata.key:
      metadata.key = self.LookupURLForMediaURL(url)
    if add_items_automatically and isinstance(metadata, Framework.modelling.objects.ModelInterfaceObject) and len(metadata) == 0:
      for item in self.MediaItemsForURL(url):
        metadata.add(item)
    return metadata
    
    
  def MediaItemsForURL(self, url):
    """ Calls MediaItemsForURL in the appropriate URL service and returns the result. """
    return self._call_named_urlservice_function_for_url('MediaItemsForURL', url, [url])
    
  def LookupURLForMediaURL(self, url):
    return 'http://localhost:32400/services/url/lookup?url='+urllib.quote(url)


class SearchService(Framework.bases.BaseKit):
  
  def _init(self):
    self._service_hosts = {}
  
  def Query(self, query, identifier):
    service = self._core.services.search_services[identifier]
    
    #TODO: Move this code into a common superclass
    # Create a new code host if one doesn't already exist for this service
    if service.name not in self._service_hosts:
      service_code_path = self._core.storage.join_path(service.path, 'ServiceCode.pys')
      code = self._core.loader.load(service_code_path)
      host = Framework.code.CodeHost(self._core, service_code_path, Framework.policies.ServicePolicy)
      host.execute(code)
      self._service_hosts[service.name] = host
        
    # Otherwise, use the host we have already
    else:
      host = self._service_hosts[service.name]
    
    result = host.call_named_function('Search', query = query)
    del host
    return result
    


class ServiceKit(Framework.bases.BaseKit):
  
  root_object = False
  
  def _init(self):
    self._urlservice = URLService(self._core, self._policy_instance)
    self._searchservice = SearchService(self._core, self._policy_instance)
    
    self._globals = dict(
      URLService    = self._urlservice,
      SearchService = self._searchservice
    )
    
