#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os, socket, sys

if sys.platform == 'win32':
  import urllib2
else:
  import urllib2_new as urllib2

class Exceptions(object):
  FrameworkException  = Framework.FrameworkException
  ContextException    = Framework.ContextException
  SocketError         = socket.error
  HTTPError           = urllib2.HTTPError
  URLError            = urllib2.URLError

class Route(Framework.bases.BaseKit):
    
  def _connect_route_decorator(self, path, method='GET', **kwargs):
    def connect_route_decorator_inner(f):
      self.Connect(path, f, method, **kwargs)
      return f
    return connect_route_decorator_inner
    
  def _generate_route(self, f, method='GET', **kwargs):
    return self._core.runtime.generate_route(f, method, **kwargs)
    
  def __call__(self, f, method='GET', **kwargs):
    return self._generate_route(f, method, **kwargs)
    
  def Connect(self, path, f, method='GET', **kwargs):
    return self._core.runtime.connect_route(path, f, method, **kwargs)


class Request(Framework.bases.BaseKit):
  
  @property
  def Headers(self):
    if self._context:
      return self._context.headers
    else:
      self._core.log.warn('Attempting to access request headers outside a request context')
      return {}
    
  def _requires_context(self, context):
    return True
    
    
class Response(Framework.bases.BaseKit):

  @property
  def Headers(self):
    if self._context:
      return self._context.response_headers
    else:
      self._core.log.warn('Attempting to access response headers outside a request context')
      return {}
      
  @property
  def Status(self):
    if self._context:
      return self._context.response_status
    else:
      self._core.log.warn('Attempting to access response status outside a request context')
      return None
      
  @Status.setter
  def Status(self, status):
    if self._context:
      self._context.response_status = status
    else:
      self._core.log.warn('Attempting to access response status outside a request context')
      
  def _requires_context(self, context):
    return True
    

class Client(Framework.bases.BaseKit):

  def _requires_context(self, context):
    return (Framework.constants.header.client_platform in context.headers or Framework.constants.header.client_capabilities in context.headers or Framework.constants.header.transaction_id in context.headers)

  @property
  def Platform(self):
    if self._context == None:
      self._core.log.error('Client platform information is unavailable in this context.')
      return None
    return self._context.platform

  @property
  def Protocols(self):
    if self._context == None:
      self._core.log.error('Client protocol information is unavailable in this context.')
      return []
    return self._context.protocols
    

class Plugin(Framework.bases.BaseKit):
  
  @property
  def Identifier(self):
    return self._core.identifier
    
  def AddPrefixHandler(self, prefix, handler, name, thumb="icon-default.png", art="art-default.png", titleBar="titlebar-default.png", share=False):
    self._core.runtime.add_prefix_handler(prefix, handler, name, thumb, art, titleBar, share)
    
  def AddViewGroup(self, name, viewMode="List", mediaType="items", type=None, menu=None, cols=None, rows=None, thumb=None, summary=None):
    self._core.runtime.add_view_group(name, viewMode, mediaType, type, menu, cols, rows, thumb, summary)
    
  def _handler_decorator(self, prefix, name, thumb="icon-default.png", art="art-default.png", titleBar="titlebar-default.png", share=False):
    def handler_decorator_inner(f):
      self._core.runtime.add_prefix_handler(prefix, f, self._core.localization.local_string(name), thumb, art, titleBar, share)
      return f
    return handler_decorator_inner
    
  @property
  def Prefixes(self):
    return self._core.runtime.prefix_handlers.keys()
    
  @property
  def ViewGroups(self):
    return dict(self._core.runtime.view_groups)
    
  def Traceback(self, msg='Traceback'):
    return self._core.traceback(msg)

  def Nice(self, value):
    if sys.platform == "win32":
      return
    if (value < 0):
      value = 0
    nice_inc = value - os.nice(0)
    os.nice(nice_inc)


class Platform(Framework.bases.BaseKit):

  @property
  def HasSilverlight(self):
    #TODO: Check all paths here
    return os.path.exists("/Library/Internet Plug-ins/Silverlight.plugin")

  @property
  def OS(self):
    return self._core.runtime.os

  @property
  def CPU(self):
    return self._core.runtime.cpu    


class RuntimeKit(Framework.bases.BaseKit):
  
  root_object = False
  
  def _init(self):
    self._route = Route(self._core, self._policy_instance)
    self._plugin = Plugin(self._core, self._policy_instance)
    
    self._globals = dict(
      Client = Client(self._core, self._policy_instance),
      Platform = Platform(self._core, self._policy_instance),
      Callback = self._core.runtime.generate_callback_path,
      Ex = Exceptions
    )
    
    if not isinstance(self._policy_instance, Framework.policies.ServicePolicy):
      self._globals.update(dict(
        Plugin = self._plugin,
        handler = self._plugin._handler_decorator,
        Route = self._route,
        route = self._route._connect_route_decorator,
        Request = Request(self._core, self._policy_instance),
        Response = Response(self._core, self._policy_instance),
      ))
      
      
    # If we're not creating a context (i.e. this will be the global kit object), and we're not running under the service policy, add a request handler
    if self._context == None and not isinstance(self._policy_instance, Framework.policies.ServicePolicy):
      self._core.runtime.add_private_request_handler(self._runtime_request_handler)

  def _runtime_request_handler(self, pathNouns, kwargs, context):
    if len(pathNouns) == 3 and pathNouns[2] == 'root':
      # Get a list of all handler paths
      keys = self._core.runtime.prefix_handlers.keys()
      
      # Try to find a video handler first
      for handler in keys:
        if handler.startswith('/video'):
          return Framework.objects.Redirect(self._core, handler)
          
      # No video handler found? Look for a music one
      for handler in self._core.runtime.prefix_handlers.keys():
        if handler.startswith('/music'):
          return Framework.objects.Redirect(self._core, handler)
  
      # Otherwise, return the first one in the list
      return Framework.objects.Redirect(self._core, keys[0])
      