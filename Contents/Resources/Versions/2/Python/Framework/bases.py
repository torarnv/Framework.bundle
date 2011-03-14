#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import types, weakref


class Object(object): pass

class FrameworkException(Exception): pass
class ContextException(Exception): pass
class UnauthorizedException(Exception): pass

def _apply(f, *args, **kwargs):
  return apply(f, args, kwargs)

def _inplacevar(op, arg1, arg2):
  if op == '+=':
    return arg1 + arg2
  raise FrameworkException("Operator '%s' is not supported" % op)

class Base(object):
  def __init__(self, core):
    self._core = core
    self._init()
  
  def _init(self):
    pass

class BaseComponent(Base):
  def __init__(self, core):
    Base.__init__(self, core)
    component_class = type(self)
    if hasattr(component_class, 'subcomponents'):
      for subcomponent in component_class.subcomponents:
        setattr(self, subcomponent, component_class.subcomponents[subcomponent](self))
        
class SubComponent(object):
  def __init__(self, base):
    self._base = base
    self._init()
    
  def _init(self):
    pass
    
  @property
  def _core(self):
    return self._base._core
  
class BaseKit(object):
  root_object = True
  
  def __init__(self, core, policy_instance, global_kit=None):
    if global_kit != None:
      self._global_kit = global_kit
    self._context = None
    self._core = core
    self._policy_instance = policy_instance
    self._init()
    
  @property
  def _txn_id(self):
    if self._context == None:
      return None
    else:
      return self._context.txn_id
    
  def _new_context(self, context):
    new_kit = type(self)(self._core, self._policy_instance, self)
    new_kit._context = context
    return new_kit
    
  def _init(self):
    pass
    
  def _preflight(self):
    for name in self.__dict__:
      obj = self.__dict__[name]
      if isinstance(obj, BaseKit):
        obj._preflight()
    
  def __getattribute__(self, name):
    attr = object.__getattribute__(self, name)
    if isinstance(attr, Framework.utils.AttrProxy):
      return getattr(attr._obj, attr._attr)
    else:
      return attr
      
  def __setattr__(self, name, value):
    if hasattr(self, name):
      attr = object.__getattribute__(self, name)
      if isinstance(attr, Framework.utils.AttrProxy):
        return setattr(attr._obj, attr._attr, value)
    return object.__setattr__(self, name, value)
    
  def _requires_context(self, context): return False
  def _begin_context(self): pass
  def _end_context(self, response_headers): pass
    
    
    
class BaseHTTPKit(BaseKit):
  
  @property
  def _opener(self):
    if self._context:
      return self._context.opener
    return None
    
  @property
  def _user_headers(self):
    # TODO: Fix this hack once we have per-user PMS data
    if self._context and self._context.proxy_user_data:
      return self._context.http_headers
    else:
      return self._core.networking.user_headers
      
  def _add_headers(self, headers={}):
    user_headers = self._user_headers
    user_headers.update(headers)
    return user_headers
  
  def _requires_context(self, context):
    return True
    
  def _begin_context(self):
    self._context.require_opener()


    
class BasePolicy(Base):
  ext = 'py'
  
  #TODO: Look in to ZopeGuards for safe alternatives to some of these
  
  base_environment = dict(
    __name__  = '__code__',
    _write_   = lambda x: x,
    _getiter_ = lambda x: x.__iter__(),
    _getitem_ = lambda x, y: x.__getitem__(y),
    _apply_   = _apply,
    _inplacevar_ = _inplacevar,
    object    = object,
    set       = set,
    str       = str,
    unicode   = unicode,
    min       = min,
    max       = max,
    xrange    = xrange,
    list      = list,
    dict      = dict,
    staticmethod = staticmethod,
    classmethod = classmethod,
    property  = property,
    sorted    = sorted,
    reversed  = reversed,
    reduce    = reduce,
    filter    = filter,
    FrameworkException = FrameworkException,
    Object    = Object,
  )
  
  allow_whitelist_extension = False
  elevated_execution = False
  allow_bundled_libraries = False
  
  def __init__(self, core):
    Base.__init__(self, core)
    policy_class = type(self)

    # Copy the whitelist from the class to the instance
    self._whitelist = []
    if hasattr(policy_class, 'whitelist'):
      self._whitelist.extend(policy_class.whitelist)

    # Construct the API objects from the classes provided by the policy
    self.api = {}
    if hasattr(policy_class, 'api'):
      for kit in self.__class__.api:
        if kit in self._core._api_exclusions:
          self._core.log.debug("Excluding '%s' from the published API", kit)
        else:
          cls = policy_class.api[kit]
          
          # If the current class is a kit object, create an instance of it
          if BaseKit in cls.__mro__:
            kit_instance = cls(core, self)
          
            # Expose the root object at the global level, if available
            if not (hasattr(cls, 'root_object') and cls.root_object == False):
              self.api[kit] = kit_instance
          
            # Add globals defined by the kit instance
            if hasattr(kit_instance, '_globals'):
              for name in kit_instance._globals:
                self.api[name] = kit_instance._globals[name]
    
    # Create a copy of the class's default environment
    self.environment = dict(BasePolicy.base_environment)
    if hasattr(policy_class, 'environment'):
      self.environment.update(policy_class.environment)

    self.builtins = {}
    if hasattr(policy_class, 'builtins'):
      self.builtins.update(policy_class.builtins)

    self.ext = policy_class.ext


class BaseInterface(Base):

  @classmethod
  def setup_environment(cls):
    pass
    
  def listen(self, daemonized):
    pass
    