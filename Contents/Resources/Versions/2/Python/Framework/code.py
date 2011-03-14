#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import RestrictedPython, os, sys, traceback, weakref, types, UserDict, cookielib

if sys.platform == 'win32':
  import urllib2
else:
  import urllib2_new as urllib2

from RestrictedPython.Guards import safe_builtins

class CodeLoader(object):
  def load(self, filename, elevated=False):
    name = os.path.basename(filename)
    
    f = open(filename, 'r')
    source = f.read()
    f.close()
    code = self.compile(str(source), str(uni(filename)), elevated)
    return code
    
    
  def compile(self, source, name, elevated=False):
    return RestrictedPython.compile_restricted(source, name, 'exec', elevated=elevated)
    
    
    
class EnvironmentAccessor(object):
  """
    Provides attribute-based access to objects in the hosted environment
  """
  def __init__(self, host):
    self._host = weakref.proxy(host)
    
    
  def __getattr__(self, name):
    return self._host.environment[name]
    
    
    
class ContextProxy(object):
  """
    Performs tests when getting or setting attributes to allow custom object code to run within request contexts
  """
  def __init__(self, host, obj, context):
    if isinstance(host, weakref.ProxyTypes):
      self._host = host
    else:
      self._host = weakref.proxy(host)
    if isinstance(obj, weakref.ReferenceType):
      self._obj = obj
    else:
      self._obj = weakref.ref(obj)
    self._context = weakref.ref(context)
    
    
  def _proxy(self, attr):
    if hasattr(self._context(), 'environment'):
      return self._host.contextualize(attr, self._context(), self)
    else:
      return attr

    
  def __getattribute__(self, name):
    if name[0] != '_':
      # First, check the class to see whether we're retrieving a property
      cls = type(self._obj())
      if hasattr(cls, name):
        attr = getattr(cls, name)
        if isinstance(attr, property):
          
          # If so, create a contextual getter function and call it with this ContextProxy
          getter = self._host.contextualize(attr.fget, self._context(), self)
          return getter(self)

      try:
        attr = getattr(self._obj(), name)
        return self._proxy(attr)
      except:
        try:
          if hasattr(attr, '_obj'):
            self._host._core.log_exception("Error in ContextProxy.__getattribute__ for %s -> %s (proxied)", name, str(attr._obj()))
          else:
            self._host._core.log_exception("Error in ContextProxy.__getattribute__ for %s -> %s", name, str(attr))
        except:
          self._host._core.log_exception("Error in ContextProxy.__getattribute__ for %s [%s]", name, str(self))
          
    if name != '_context' and name != '_proxy' and hasattr(self._context(), 'environment') and self._context().environment != None and name in self._context().environment:
      return object.__getattribute__(self, '_context')().environment[name]
    else:
      return object.__getattribute__(self, name)
  
    
  def __setattr__(self, name, value):
    if name[0] == '_':
      return object.__setattr__(self, name, value)
      
    # First, check the class to see whether we're setting a property
    cls = type(self._obj())
    if hasattr(cls, name):
      attr = getattr(cls, name)
      if isinstance(attr, property):
        
        # If so, create a contextual setter function and call it with this ContextProxy
        setter = self._host.contextualize(attr.fset, self._context(), self)
        return setter(name, value)
    
    # Otherwise, set the attribute the standard way
    setattr(self._obj(), name, value)
  
  
  
class CallableObj(object):
  def __init__(self, obj):
    self._obj = obj
  def __call__(self):
    return self._obj
    
    
    
class ContainerContextProxy(ContextProxy):
  def __init__(self, host, obj, context):
    if isinstance(host, weakref.ProxyTypes):
      self._host = host
    else:
      self._host = weakref.proxy(host)
    if isinstance(host, CallableObj):
      self._obj = obj
    else:
      self._obj = CallableObj(obj)
    self._context = weakref.ref(context)

  def __getitem__(self, name):
    item = self._obj()[name]
    return self._proxy(item)

  def __setitem__(self, name, value):
    self._obj()[name] = value

  def __delitem__(self, name):
    del self._obj()[name]

  def __contains__(self, name):
    return self._obj().__contains__(name)

  def __iter__(self):
    return self._obj().__iter__()
    
  def __len__(self):
    return self._obj().__len__()
    
    
    
class DictContextProxy(UserDict.DictMixin, ContainerContextProxy):

  #def __cmp__(self, other):                   return self._obj().__cmp__(other)                   
  def __contains__(self, item):               return self._obj().__contains__(item)               
  def __hash__(self):                         return self._obj().__hash__()                       
  def __setitem__(self, name, value):         return self._obj().__setitem__(name, value)         
  def __delitem__(self, name):                return self._obj().__delitem__(name)                
                                                                                                
  def __lt__(self, other):                    return self._obj().__lt__(other)                    
  def __le__(self, other):                    return self._obj().__le__(other)                    
  def __eq__(self, other):                    return self._obj().__eq__(other)                    
  def __ne__(self, other):                    return self._obj().__ne__(other)                    
  def __gt__(self, other):                    return self._obj().__gt__(other)                    
  def __ge__(self, other):                    return self._obj().__ge__(other)                    
                                                                                                
  def clear(self):                            return self._obj().clear()                          
  def get(self, key, default=None):           return self._obj().get(key, default)                
  def has_key(self, key):                     return self._obj().has_key(key)                     
  def items(self):                            return self._obj().items()                          
  def iteritems(self):                        return self._obj().iteritems()                      
  def iterkeys(self):                         return self._obj().iterkeys()                       
  def keys(self):                             return self._obj().keys()                           
  def pop(self, key, default=None):           return self._obj().pop(key, default)                
  def popitem(self):                          return self._obj().popitem()                        
  def setdefault(self, key, default=None):    return self._obj().setdefault(key, default)
  def update(self, *args, **kwargs):          return self._obj().update(*args, **kwargs)
  def values(self):                           return self._obj().values()
    
    
class ListContextProxy(ContainerContextProxy):
  pass
    

class RequestContext(object):
  def __init__(self, core, headers):
    self._core = core
    self.headers = headers
    self.http_headers = dict(self._core.networking.user_headers)
    self.response_headers = dict()
    self.response_status = None
    self.opener = None
    self.cookie_jar = None
    self.environment = None
    self.txn_id = None
    self.protocols = []
    self.platform = None
    self.cache_time = None
    self.proxy_user_data = False
    self.prefix = None
    
    if Framework.constants.header.client_platform in headers:
      self.platform = headers[Framework.constants.header.client_platform]

    if Framework.constants.header.client_capabilities in headers:
      caps = headers[Framework.constants.header.client_capabilities].split(';')
      for cap in caps:
        name, values = cap.split('=')
        if name == 'protocols':
          self.protocols = values.split(',')
          
  def update_cache_time(self, new_time):
    if new_time == None:
      self.cache_time = self._core.networking.cache_time
    elif self.cache_time == None or new_time < self.cache_time:
      self.cache_time = new_time
    
  def require_opener(self):
    if self.opener != None: return
    
    opener_args = []
    if Framework.constants.header.proxy_cookies in self.headers:
      self.proxy_user_data = True
      self.cookie_jar = cookielib.MozillaCookieJar()
      
      # If the cookie header is present, extract the key & value and try to match to the current identifier
      if 'Cookie' in self.headers and len(self.headers['Cookie']) > 0:
        for parts in [pair.strip().split('=') for pair in self.headers['Cookie'].split(',')]:
          if len(parts) < 2:
            continue
          key = parts[0].strip()
          value = parts[1].split(';')[0].strip()
          
          state_data = None
          # If found, unpack the encoded cookies and state data and populate the cookie jar and other dicts
          if key == self._core.identifier:
            cookie_list = Framework.utils.unpack(value)
            for cookie in cookie_list:
              if isinstance(cookie, dict):
                state_data = cookie
              else:
                self.cookie_jar.set_cookie(cookie)
            
            if state_data:
              if 'http_headers' in state_data:
                self.http_headers.update(state_data['http_headers'])
            
            break
      
      opener_args.append(urllib2.HTTPCookieProcessor(self.cookie_jar))
          
    if len(opener_args) > 0:
      self.opener = urllib2.build_opener(*opener_args)

def loader(path, host):
  class Loader(object):
    def load_module(self, name):
      lastname = name.split('.')[-1]
      if lastname in sys.modules:
        return sys.modules[lastname]
      if name not in sys.modules:
        sys.modules[name] = None
        module = RestrictedModule(name, path, host)
        sys.modules[name] = module
        if '.' in name:
          parent_name, child_name = name.rsplit('.', 1)
          setattr(sys.modules[parent_name], child_name, module)
      return sys.modules[name]
  return Loader()
   
class MetaImporter(object):
  """
    Searches for code files inside Contents/Code, and loads them with restrictions
  """
  
  def __init__(self, host):
    self._host = host
    
  def find_module(self, fullname, path=None):
    if self._host.code_path:
      lastname = fullname.rsplit('.', 1)[-1]
      possible_paths = []
      
      if path != None and isinstance(path, basestring) and path.startswith(self._host.code_path):
        root_path = path
      else:
        root_path = self._host.code_path
      
      possible_paths.append(os.path.join(root_path, lastname + '.' + self._host._policy_instance.ext))
      possible_paths.append(os.path.join(root_path, lastname, '__init__' + '.' + self._host._policy_instance.ext))
      
      for pyp in possible_paths:
        if os.path.exists(pyp):
          return loader(pyp, self._host)

    
class CodeHost(object):
  """
    CodeHost manages the loading, compilation and execution of restricted code within a plug-in.
    Multiple hosts can be created and used by the framework. Each host is bound to a Framework
    core object and a policy class. The policy dictates the API exposed to the hosted code and
    which security measures should be used.
  """
  def __init__(self, core, code_path, policy):
    self._core = core
    self.code_path = code_path
    self._policy_instance = policy(core)
    self._module_warnings = list()
    
    # Set up the default builtins
    standard_builtins = safe_builtins
    standard_builtins['__import__'] = self.__import__
    standard_builtins.update(self._policy_instance.builtins)
    
    sys.meta_path.append(MetaImporter(self))
    
    # Configure the environment
    self.environment = {
      '_print_': PrintHandler,
      '_getattr_' : __builtins__['getattr'],
      '__builtins__': standard_builtins,
      '_contextual': False,
    }
    self.environment.update(self._policy_instance.environment)
    
    # Publish the API
    self.environment.update(self._policy_instance.api)
    
    # Create an environment accessor & add it to the system modules dict
    accessor = EnvironmentAccessor(self)
    sys.modules[self.environment['__name__']] = accessor
    
    
  def format_kwargs_for_function(self, f, kwargs):
    # Get the defaults from the function & grab the names of the variables
    defaults = f.func_defaults
    if not defaults: return
    varnames = f.func_code.co_varnames
    
    while len(varnames) > 0 and varnames[-1][0] == '_':
      varnames = varnames[:-1]
    varnames = varnames[-len(defaults):]
    
    # Iterate through the variables
    for i in range(len(varnames)):
      
      # Get the name
      n = varnames[i]
      
      # If the name is in the provided kwargs...
      if n in kwargs:
        
        # Get the type of the default
        t = type(defaults[i])
        
        # Convert the provided kwarg to the correct type if necessary
        v = kwargs[n]
        if t == bool:
          kwargs[n] = (v == True or str(v).lower() == 'true' or str(v) == '1')
        elif t == int:
          kwargs[n] = int(v)
        elif t == float:
          kwargs[n] == float(v)
          
  
  def copy_function(self, f):
    d = dict(f.func_globals)
    
    if '__builtins__' in d:
      d.update(d['__builtins__'])
    if 'safe_builtins' in d:
      d.update(d['safe_builtins'])
      
    cf = types.FunctionType(f.func_code, dict(d), f.__name__)
    if f.func_defaults != None:
      cf.func_defaults = tuple(f.func_defaults)
    return cf

  def globalize(self, attr):
    if isinstance(attr, types.FunctionType) or isinstance(attr, property):
      # Copy the function & update its globals
      cf = self.copy_function(attr)
      cf.func_globals.update(self.environment)
      return cf
      
    elif isinstance(attr, types.MethodType):
      # Create a contextual version of the instance method's function
      cf = self.copy_function(attr.im_func)
      cf.func_globals.update(self.environment)
      
      # If no SelfProxy object was provided, create one
      if isinstance(attr.im_self, ContextProxy):
        new_self = attr.im_self._obj()
      else:
        new_self = attr.im_self
      # Create a contextual method using the new function, the current ContextProxy object and the object's class
      cm = types.MethodType(cf, new_self, attr.im_class)
      return cm
      
    return attr

  def contextualize(self, attr, context, selfproxy=None):
    def should_proxy(obj):
      return isinstance(obj, dict) or isinstance(obj, list) or isinstance(obj, Framework.bases.Object)
      
    if isinstance(attr, types.FunctionType) or isinstance(attr, property):
      # Copy the function & update its globals
      cf = self.copy_function(attr)
      cf.func_globals.update(context.environment)
      return cf
      
    elif isinstance(attr, types.MethodType):
      # Create a contextual version of the instance method's function
      cf = self.copy_function(attr.im_func)
      cf.func_globals.update(context.environment)
      
      # If no SelfProxy object was provided, create one
      if selfproxy == None:
        selfproxy = ContextProxy(self, attr.im_self, context)

      # Create a contextual method using the new function, the current ContextProxy object and the object's class
      cm = types.MethodType(cf, selfproxy, attr.im_class)
      return cm
      
    # Check for dictionaries, return a DictContextProxy
    elif isinstance(attr, dict):
      if selfproxy != None:
        return DictContextProxy(self, attr, context)
      for k,v in attr.items():
        if should_proxy(k) or should_proxy(v):
          return DictContextProxy(self, attr, context)
      return dict(attr)
      
    elif isinstance(attr, list):
      if selfproxy != None:
        return ListContextProxy(self, attr, context)
      for i in attr:
        if should_proxy(i):
          return ListContextProxy(self, attr, context)
      return list(attr)
      
    elif isinstance(attr, DictContextProxy):
      return DictContextProxy(self, attr._obj(), context)
      
    elif isinstance(attr, ListContextProxy):
      return ListContextProxy(self, attr._obj(), context)
      
    # Check for ContextProxy objects, extract the proxied object and return a new one
    elif isinstance(attr, ContextProxy):
      return ContextProxy(self, attr._obj(), context)

    # And finally, check for subclasses of Object, indicating a user-defined class. If found, return a new ContextProxy for that object in the current context
    elif isinstance(attr, Framework.bases.Object):
      return ContextProxy(self, attr, context)

    # If none of these conditions are satisfied, return the attribute
    return attr  
    
  def build_context(self, request_headers):
    context = RequestContext(self._core, request_headers)
    
    if Framework.constants.header.transaction_id in request_headers:
      context.txn_id = request_headers[Framework.constants.header.transaction_id]
    
    # Create a copy of the environment dictionary
    ce = dict(self.environment)
    ce['_contextual'] = True
    
    functions = {}
    kits = {}
    objects = {}
    
    # Iterate through the new environment
    for name in ce:
      # Build contextual versions of all public functions
      if name[0] == '_':
        continue
        
      if isinstance(ce[name], types.FunctionType):
        ce[name] = self.copy_function(ce[name])
        functions[name] = ce[name]
        
      # Create contextual versions of the API objects
      elif isinstance(ce[name], Framework.bases.BaseKit):
        if ce[name]._requires_context(context):
          ck = ce[name]._new_context(context)
          ck._begin_context()
          ce[name] = ck
          kits[name] = ck
        
      elif not isinstance(ce[name], types.MethodType):
        ce[name] = self.contextualize(ce[name], context)
  
    # Update the globals of the modified functions so inter-function calls and API access works properly
    for func_name in functions:
      func = functions[func_name]
      func.func_globals.update(functions)
      func.func_globals.update(kits)
      func.func_globals.update(objects)
          
    del functions
    del kits
    
    context.environment = ce
    
    return context
    
    
  def release_context(self, context, response_headers):
    names = []
    for name in context.environment:
      if isinstance(context.environment[name], Framework.bases.BaseKit) and context.environment[name]._context != None:
        context.environment[name]._end_context(response_headers)
        names.append(name)
      elif isinstance(context.environment[name], types.FunctionType):
        f_names = []
        for f_name in context.environment[name].func_globals:
          g = context.environment[name].func_globals[f_name]
          if isinstance(g, Framework.bases.BaseKit) or isinstance(g, types.FunctionType):
            f_names.append(f_name)
        for f_name in f_names:
          del context.environment[name].func_globals[f_name]
        names.append(name)
    for name in names:
      del context.environment[name]
    del context.environment
      
      
  def execute(self, code):
    exec(code) in self.environment
    
    
  def call_named_function(self, function_name, context=None, *args, **kwargs):
    """
      Try to call a function in the hosted environment with the given args & kwargs.
    """
    if context == None:
      ce = self.environment
      txn_id = None
    else:
      ce = context.environment
      txn_id = context.txn_id
    try:  
      if function_name in ce:
        f = ce[function_name]
        self.format_kwargs_for_function(f, kwargs)
        result = f(*args, **kwargs)
        return result
    except Framework.UnauthorizedException:
      raise
    except:
      self._core.log_except(txn_id, "Exception when calling function '%s'", function_name)
      
  def __import__(self, _name, _globals={}, _locals={}, _fromlist=[], _level=-1):
    """
      Calls the standard Python import mechanism. We use the above import hook (MetaImporter)
      to apply restrictions to plug-in code (in Contents/Code)
    """
    m = None
    try:
      m = __import__(_name, _globals, _locals, _fromlist, _level)
    except Exception, e:
      try:
        m = __import__('_'+_name, _globals, _locals, _fromlist, _level)
      except:
        raise e
    return m
    
    
class RestrictedModule(types.ModuleType):
  """
    Compiles a module with the host's restrictions, storing enough information to allow relative
    imports from this module.
  """
  def __init__(self, name, filename, host, rel_path=None):
    types.ModuleType.__init__(self, name)
    code = host._core.loader.load(filename, type(host._policy_instance).elevated_execution)
    self.__dict__.update(host.environment)
    self.__dict__['_current_code_path'] = os.path.dirname(filename)
    module_name = os.path.splitext(os.path.basename(filename))[0]
    if rel_path:
      module_name = os.path.splitext(os.path.basename(rel_path))[0] + '.' + module_name
    self.__dict__['__name__'] = module_name
    self.__path__ = os.path.dirname(filename)
    sys.modules[module_name] = self
    exec(code) in self.__dict__



class PrintHandler:
  """
    A simple class for handling print statements in restricted code.
  """
  def write(self, text):
    if sys.platform != "win32":
      sys.stdout.write(text)
