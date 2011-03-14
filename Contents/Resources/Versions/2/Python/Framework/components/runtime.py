#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import urlparse, urllib, cgi, routes, threading, sys, os, Queue, base64, types, socket
from lxml import etree

if sys.platform == 'win32':
  import urllib2
else:
  import urllib2_new as urllib2


class PrefixHandlerRecord(object):

  def __init__(self, handler, name, thumb, art, titleBar, share):
    self.handler = handler
    self.name = name
    self.thumb = thumb
    self.art = art
    self.titleBar = titleBar
    self.share = share


view_modes = {
  "List": 65586, "InfoList": 65592, "MediaPreview": 458803, "Showcase": 458810, "Coverflow": 65591, 
  "PanelStream": 131124, "WallStream": 131125, "Songs": 65593, "Seasons": 65593, "Albums": 131123, 
  "Episodes": 65590,"ImageStream":458809,"Pictures":131123
}


class ViewGroupRecord(object):

  def __init__(self, viewMode=None, mediaType=None, type=None, menu=None, cols=None, rows=None, thumb=None, summary=None):
    if viewMode:
      if viewMode not in view_modes:
        raise Framework.FrameworkException("%s is not a valid view mode." % viewMode)
      self.viewMode = view_modes[viewMode]
    else:
      self.viewMode = None
    self.mediaType = mediaType
    self.viewType = type
    self.viewMenu = menu
    self.viewCols = cols
    self.viewRows = rows
    self.viewThumb = thumb
    self.viewSummary = summary


class BaseTaskQueue(object):
  """
    BaseTaskQueue implements a simple queue that adds tasks to a task pool. This class is
    pointless when instantiated directly as it simply drops tasks into the pool as soon as
    they're received. One of the subclasses should be used instead. 
  """
  
  def __init__(self, pool):
    self._pool = pool
    self._queue = Queue.Queue()
    self._pool._runtime.create_thread(self._thread)
  
  def _thread(self):
    dead = False
    while not dead:
      dead = not self._process()
    self._pool._runtime._core.log.debug("Finished dispatching queued tasks to the pool - ending the thread.")
      
  def _process(self):
    obj = self._queue.get()
    self._pool._add(obj)
    self._queue.task_done()
    return obj != None
    
  def _add(self, task):
    self._queue.put(task)
    
  def add_task(self, f, args=[], kwargs={}, important=False):
    obj = TaskObject(f, args, kwargs, important)
    self._add(obj)
    return obj
    
  def end(self):
    self._add(None)
    
  @property
  def size(self):
    return self._queue.qsize()
    
    
class BlockingTaskQueue(BaseTaskQueue):
  """
    A task queue with an event assigned to it. The queue blocks new tasks from being added to the
    pool until the event is set.
  """
  
  def __init__(self, pool, event):
    self._event = event
    BaseTaskQueue.__init__(self, pool)
    
  def _process(self): 
    self._event.wait()
    return BaseTaskQueue._process(self)
    
    
class LimitingTaskQueue(BaseTaskQueue):
  """
    A task queue that only allows a maximum number of tasks to enter the pool at any one time. The
    queue will block when the number of tasks in the pool is equal to the defined limit and allow
    subsequent tasks to be processed only when existing ones have finished.
  """
  
  def __init__(self, pool, limit):
    self._semaphore = pool._runtime.semaphore(limit=limit)
    BaseTaskQueue.__init__(self, pool)

  def _process(self):
    obj = self._queue.get()
    self._semaphore.acquire()
    self._pool.add_task(self._run, kwargs=dict(obj=obj))
    self._queue.task_done()
    return obj != None
    
  def _run(self, obj):
    ret = None
    if isinstance(obj, TaskObject):
      try:
        obj._exec()
        ret = obj.result
      except:
        self._pool._runtime._core.log_except(None, 'Exception in task thread')
    self._semaphore.release()
    return ret


class TaskObject(object):
  """
    Task objects define a function to execute, args/kwargs to pass to the function, the function
    result, the function's completion status and a priority flag.
  """

  def __init__(self, f, args, kwargs, important=False):
    self._complete = threading.Event()
    self._f = f
    self._args = args
    self._kwargs = kwargs
    self._result = None
    self._important = important
    
  def wait(self):
    """
      Blocks the calling thread until the task is completed.
    """
    return self._complete.wait()
    
  @property
  def result(self):
    """
      Blocks the calling thread until the task is completed, then returns the result
    """
    self._complete.wait()
    return self._result
    
  def _exec(self):
    """
      Executes the function, setting the result and handling any exceptions, then sets the
      completed event to unblock any waiting threads.
    """
    try:
      self._result = self._f(*self._args, **self._kwargs)
    finally:
      self._complete.set()


class TaskThread(object):
  """
    Task threads handle the execution of tasks belonging to a task pool.
  """
  
  def __init__(self, pool, priority=False):
    """
      Store a reference to the task pool and whether this is a priority thread or not.
      Priority threads only execute tasks in the task pool's priority queue. Standard
      queues give priority to tasks in the priority queue, then fall back to the standard
      queue if no important tasks have been added
    """
    self._priority = priority
    self._pool = pool
    self._pool._runtime.create_thread(self._start)
    
  def _start(self):
    """
      Keep fetching tasks from the pool and processing them
    """
    while True:
      obj = None
      important = False
      
      # If this is a priority thread, only execute tasks in the priority queue. Otherwise, check
      # for important tasks first, then wait for standard ones.
      if self._priority:
        obj = self._pool._priority_queue.get()
        important = True
      else:
        if not self._pool._priority_queue.empty():
          obj = self._pool._priority_queue.get()
          important = True
        else:
          obj = self._pool._queue.get()
      
      # If executing an important task, put None in the standard queue to wake up non-priority threads
      # for processing of additional important tasks (if any)     
      if important:
        self._pool._queue.put(None)

      # If the fetched object is a TaskObject, execute it
      if obj != None and isinstance(obj, TaskObject):
        try:
          obj._exec()
        except:
          self._pool._runtime._core.log_except(None, 'Exception in task thread')
        
      # Notify the relevant queue that processing has completed
      if important:
        self._pool._priority_queue.task_done()
      else:
        self._pool._queue.task_done()
        

class TaskPool(object):
  """
    Task pools manage a number of worker threads and the distribution of task objects
    between them.
  """
  
  def __init__(self, runtime, threadcount=8, prioritycount=0):
    # Store a reference to the runtime, and store the thread count and priority count.
    self._runtime = runtime
    self._threadcount = threadcount
    self._prioritycount = prioritycount
    
    # Create the queues
    self._queue = Queue.Queue()
    self._priority_queue = Queue.Queue()
    
    # Create the required number of threads (setting the priority flag accordingly)
    self._threads = []
    for x in range(prioritycount):
      self._threads.append(TaskThread(self, True))
    for x in range(threadcount - prioritycount):
      self._threads.append(TaskThread(self, False))
      
  def _add(self, obj):
    """
      Adds a given task object to the relevant queue.
    """
    if obj._important:
      self._priority_queue.put(obj)
    else:
      self._queue.put(obj)
      
  def add_task(self, f, args=[], kwargs={}, important=False, globalize=True):
    """
      Creates a task object with the given attributes and adds it to the pool.
    """
    if globalize:
      f = self._runtime._globalize(f)
    obj = TaskObject(f, args, kwargs, important)
    self._add(obj)
    return obj
    
  def wait_for_tasks(self, tasks=[]):
    """
      Blocks the calling thread until all listed tasks have completed.
    """
    for obj in tasks:
      if isinstance(obj, TaskObject):
        obj.wait()
  
  def create_blocking_queue(self, event):
    """
      Creates a BlockingTaskQueue for this pool.
    """
    return BlockingTaskQueue(self, event)
    
  def create_limiting_queue(self, limit):
    """
      Creates a LimitingTaskQueue for this pool.
    """
    return LimitingTaskQueue(self, limit)
    
class RouteManager(Framework.bases.Base):
  def __init__(self, core, runtime, method):
    Framework.bases.Base.__init__(self, core)
    self._method = method
    self._route_lock = runtime.lock()
    self._route_controllers = {}
    self._route_mapper = routes.Mapper()
    self._route_generator = routes.URLGenerator(self._route_mapper, {})
    
  def connect_route(self, path, f, **kwargs):
    self._route_lock.acquire()
    try:
      if f.__name__ not in self._route_controllers:
        self._route_controllers[f.__name__] = f
      if 'action' not in kwargs:
        kwargs['action'] = '__NONE__'
      self._route_mapper.connect(None, path, controller=f.__name__, **kwargs)
      self._core.log.debug("Connecting route %s to %s", path, f.__name__)
    finally:
      self._route_lock.release()

  def generate_route(self, f, **kwargs):
    if 'action' not in kwargs:
      kwargs['action'] = '__NONE__'
    return self._route_generator(controller=f.__name__, **kwargs)

  def match_route(self, path, txn_id=None):
    self._route_lock.acquire()
    try:
      d = self._route_mapper.match(path)
      if not d:
        raise Framework.FrameworkException("No route found matching '%s'" % path)
      f = self._route_controllers[d['controller']]
      del d['controller']
      if d['action'] == '__NONE__': del d['action']
      self._core.host.format_kwargs_for_function(f, d)
      return f, d  
    except:
      self._core.log_except(txn_id, 'Exception in match_route')
      return None, None
    finally:
      self._route_lock.release()

class Runtime(Framework.bases.BaseComponent):
  """
    The Runtime component manages the state of the current plug-in, including request handling
    and thread management. Most of the functionality provided here is exposed via the RuntimeKit,
    and ThreadKit APIs.
  """

  def _init(self):
    self.prefix_handlers = {}
    self.view_groups = {}
    
    self._private_handlers = []
    
    self._thread_locks = {}
    self._thread_events = {}
    self._thread_semaphores = {}
    self._interface_args = {}
    
    self._current_user_id = None
    self._delegates = []
    self._delegate_lock = self.lock()
    
    self._route_managers = {}
    self._create_route_manager('GET')
    self._create_route_manager('PUT')
    
    self._taskpool = TaskPool(
      self,
      threadcount = self._core.config.taskpool_maximum_threads,
      prioritycount = self._core.config.taskpool_priority_threads
    )
    
  def _create_route_manager(self, method):
    self._route_managers[method] = RouteManager(self._core, self, method)

  @property
  def os(self):
    """
      Returns the current OS name (e.g. MacOSX or Linux)
    """
    if sys.platform == "win32":
      os_name = "Windows"
    else:
      os_name = os.uname()[0]
    if os_name in self._core.config.os_map:
      return self._core.config.os_map[os_name]
  
  @property
  def cpu(self):
    """
      Returns the current CPU name (e.g. x86 or MIPS)
    """
    if sys.platform == "win32":
      #TODO: Support x64 CPUs on Windows
      cpu_name = "i386"
    else:
      cpu_name = os.uname()[4]
    if cpu_name in self._core.config.cpu_map:
      return self._core.config.cpu_map[cpu_name]
      
  @property
  def platform(self):
    return '%s-%s' % (self.os, self.cpu)
    
  def add_prefix_handler(self, prefix, handler, name, thumb, art, titleBar, share=False):
    self._core.log.debug("Adding a prefix handler for '%s' ('%s')", name, prefix)
    self.prefix_handlers[prefix] = PrefixHandlerRecord(handler, name, thumb, art, titleBar, share)
    
  def add_view_group(self, name, viewMode=None, mediaType=None, type=None, menu=None, cols=None, rows=None, thumb=None, summary=None):
    self.view_groups[name] = ViewGroupRecord(viewMode, mediaType, type, menu, cols, rows, thumb, summary)
  
  def create_query_string(self, kwargs):
    return 'function_args=' + Framework.utils.pack(kwargs)
    
  def parse_query_string(self, querystring, txn_id=None):
    kwargs = {}
    
    # Check for an empty querystring
    if len(querystring) == 0:
      return kwargs
      
    # Check for empty args
    for arg in querystring.split('&'):
      if len(arg) > 1 and arg[-1] == '=':
        kwargs[arg[:-1]] = None
    
    # Parse populated args
    qs_args = cgi.parse_qs(querystring)
    if 'function_args' in qs_args:
      try:
        packed_args = qs_args['function_args'][0]
        kwargs = Framework.utils.unpack(packed_args)
      except:
        self._core.log_except(txn_id, "Exception decoding function arguments")
    for arg in qs_args:
      if arg != 'function_args':
        kwargs[arg] = qs_args[arg][0]
    return kwargs
  
  def add_private_request_handler(self, f):
    self._private_handlers.append(f)
    
  def _handle_private_request(self, pathNouns, kwargs, context):
    for handler in self._private_handlers:
      result = handler(pathNouns, kwargs, context)
      if result != None:
        return result
    return None
    
  def handle_request(self, path, headers, method='GET'):
    """
      Handles a given path & set of headers, directing a request to the relevant plug-in or
      framework function and returning the result.
    """
    context = None
    
    try:
      # Build a context for this request
      context = self._core.host.build_context(headers)
      
      self._core.log_debug(context.txn_id, "Handling request %s %s", method, path)
      
      result = None
      req = urlparse.urlparse(path)
      path = req.path
      kwargs = self.parse_query_string(req.query, context.txn_id)
      
      if path[-1] == '/': path = path[:-1]
      pathNouns = [urllib.unquote(p) for p in path.split('/')]
      pathNouns.pop(0)
      
      # Return simple OK for requests for root
      if len(pathNouns) == 0:
        result = "OK\n"
        
      # Check for management requests (internal requests from the media server)
      elif len(pathNouns) > 1 and pathNouns[0] == ':':
        result = self.handle_management_request(pathNouns[1:], kwargs, context)
        if result == None:
          result = self._handle_private_request(pathNouns[1:], kwargs, context)
          
      # Check if we're at the root of a prefix
      elif path in self.prefix_handlers:
        context.prefix = path
        handler = self._core.host.contextualize(self.prefix_handlers[path].handler, context)
        self._core.host.format_kwargs_for_function(handler, kwargs)
        self._core.log_debug(context.txn_id, "Found prefix handler matching "+path)
        result = handler(**kwargs)
        del handler
        
      else:
        # Store the full route path
        route_path = '/'+'/'.join(pathNouns)
        
        # Pop path nouns from the prefix and check whether the request should be handled internally
        for prefix in self.prefix_handlers:
          if path.count(prefix, 0, len(prefix)) == 1:
            context.prefix = prefix
            for i in range(len(prefix.split('/'))-1):
              pathNouns.pop(0)
            break

        if len(pathNouns) > 1 and pathNouns[0] == ':':
          result = self.handle_internal_request(pathNouns[1:], kwargs, context)   
          if result == None:
            result = self._handle_private_request(pathNouns[1:], kwargs, context)
          
        else:
          # Check for a matching route
          f,d = self.match_route(route_path, method, context.txn_id)
          if f:
            if d:
              d.update(kwargs)
            else:
              d = kwargs
            self._core.log_debug(context.txn_id, "Found route matching "+route_path)
            cf = self._core.host.contextualize(f, context)
            result = cf(**d)
          else:
            self._core.log_error(context.txn_id, "Could not find route matching "+route_path)
            
      if 'X-Plex-Container-Start' in headers and 'X-Plex-Container-Size' in headers and isinstance(result, Framework.objects.MediaContainer):
        try:
          start = int(headers['X-Plex-Container-Start'])
          end = start + int(headers['X-Plex-Container-Size'])
          total_size = len(result)
          result = result[start:end]
          result.SetHeader('X-Plex-Container-Start', str(start))
          result.SetHeader('X-Plex-Container-Total-Size', str(total_size))
          result.totalSize = total_size

        except:
          self._core.log_except(context.txn_id, 'Exception when calculating paged results')

      status, headers, body = self.construct_response(result, context)
    
    except KeyboardInterrupt:
      raise # re-raise KeyboardInterrupts - let the interface catch those
    
    except Framework.UnauthorizedException:
      self._core.log.debug("Unauthorized")
      status = 401
      headers = {}
      body = ''
      
    except Exception, e:
      if context:
        self._core.log_except(context.txn_id, "Exception")
      else:
        self._core.log_except(None, "Exception")
      
      headers = {}
        
      # If the exception was a timeout error, return 504, otherwise return 500 with more info
      if isinstance(e, urllib2.URLError) and len(e.args) > 0 and isinstance(e.args[0], socket.timeout):
        status = 504
        body = ''
      else:
        status = 500

        el = self._core.data.xml.element('Exception')
        el.set('type', str(type(e).__name__))
        el.set('message', e.message)
        el.append(self._core.data.xml.element('Traceback', self._core.traceback()))
      
        body = self._core.data.xml.to_string(el)
    
    finally:
      # If returning from a request context, add headers from kit objects
      if context:
        final_headers = dict()
        
        # If the status code was set manually, override the code that was set automatically
        if context.response_status != None:
          status = context.response_status
          
        self._core.host.release_context(context, final_headers)
        
        # Don't return context headers when the status is 401 (Unauthorized)
        if status != 401:
          final_headers.update(headers)
          headers = final_headers

        txn_id = context.txn_id

      else:
        txn_id = None
      
      # Log the response code
      self._core.log_debug(txn_id, "Response: %s" % str(status))
    
      
    return (status, headers, body)
    
  def handle_management_request(self, pathNouns, kwargs, context):
    """
      Handles a management request (received directly from the media server - cannot
      be generated by an external request)
    """
    count = len(pathNouns)
    if count > 0:
      # If PMS is requesting a list of prefixes, construct a MediaContainer and return it
      if pathNouns[0] == 'prefixes' and count == 1:
        d = Framework.objects.MediaContainer(self._core)
        
        hasPrefs = self._core.storage.file_exists(self._core.storage.join_path(self._core.plugin_support_path, 'Preferences', self._core.identifier + '.xml')) \
          or self._core.storage.file_exists(self._core.storage.join_path(self._core.bundle_path, 'Contents', 'DefaultPrefs.json'))
        
        for prefix in self.prefix_handlers:
          handler = self.prefix_handlers[prefix]
          d.Append(Framework.objects.XMLObject(self._core, tagName="Prefix", key=prefix, name=handler.name, thumb=self.external_resource_path(handler.thumb), art=self.external_resource_path(handler.art), titleBar=self.external_resource_path(handler.titleBar), hasPrefs=hasPrefs, identifier=self._core.identifier))
        
        for arg in self._interface_args:
          setattr(d, arg, self._interface_args[arg])
        
        return d
        
      elif count == 4 and pathNouns[0] == 'plugins' and pathNouns[2] == ':' and pathNouns[3] == 'memory':
        s = ''
        for n, c in self.get_refcounts()[:50]:
          s +=  '%10d %s\n' % (n, c.__name__)
        return s
        
      elif pathNouns[0] == 'events' and count > 1:
        if pathNouns[1] == 'systemBundleRestarted':
          return ''
       
      elif pathNouns[0] == "rate" and count == 1:
        key = base64.urlsafe_b64decode(str(kwargs["key"]))
        rating = int(kwargs["rating"])
        self._core.log.debug("Setting rating of '%s' to %d", key, rating)
        if rating >= 0 and rating <= 10:
          self._core.host.call_named_function("SetRating", context=context, key=key, rating=rating)
          return ''
      
      elif pathNouns[0] == 'cookies' and count == 1:
        return self._core.networking.cookie_container(**kwargs)

  def get_refcounts(self):
    d = {}
    sys.modules

    # collect all classes
    for m in sys.modules.values():
      for sym in dir(m):
        o = getattr (m, sym)
        if type(o) is types.ClassType:
          d[o] = sys.getrefcount(o)

    # sort by refcount
    pairs = map (lambda x: (x[1],x[0]), d.items())
    pairs.sort()
    pairs.reverse()
    return pairs
      
  def handle_internal_request(self, pathNouns, kwargs, context):
    """
      Handles an internal request (meant to be handled by the framework, but can be requested
      via an external interface)
    """
    count = len(pathNouns)
    if count == 0: return
    
    if pathNouns[0] == 'function' and (count == 2 or count == 3):
      function_name = pathNouns[1]
      
      self._core.log_debug(context.txn_id, "Calling function '%s'", function_name)
      
      # Strip the extension (if included)
      pos = function_name.rfind('.')
      if pos > -1:
        function_name = function_name[:pos]
      
      if count == 3:
        kwargs['query'] = pathNouns[2]
        
      # Check for an IndirectFunction call
      if 'indirect' in kwargs and kwargs['indirect'] == '1':
        indirect = True
        del kwargs['indirect']
      else:
        indirect = False
        
      result = self._core.host.call_named_function(function_name, context=context, **kwargs)
      
      # If this isn't an indirect function, return the result as provided
      if not indirect:
        return result
        
      # Otherwise, check for a Redirect object, and return an XML representation of it
      elif isinstance(result, Framework.objects.Redirect):
        location = result.Headers()['Location']
        return self._core.data.xml.element('IndirectResponse', location=location)
    
    elif pathNouns[0] == 'resources' and count == 2:
      itemname = pathNouns[1]
      if self._core.storage.resource_exists(itemname):
        resource = self._core.storage.load_resource(itemname)
        return Framework.objects.DataObject(self._core, resource, Framework.utils.guess_mime_type(itemname))
  
    elif pathNouns[0] == 'sharedresources' and count == 2:
      itemname = pathNouns[1]
      if self._core.storage.shared_resource_exists(itemname):
        resource = self._core.storage.load_shared_resource(itemname)
        return Framework.objects.DataObject(self._core, resource, Framework.utils.guess_mime_type(itemname))
      
  def construct_response(self, result, context=None):
    """
      Converts a function call result into a server response. Handles conversion of
      Framework Objects, XML elements, strings or 'None'.
    """
    resultStr = None
    
    if context:
      txn_id = context.txn_id
    else:
      txn_id = None
    
    if result == None:
      resultStr = ''
      resultHeaders = {}
      resultStatus = 404
      
    elif isinstance(result, Framework.modelling.objects.Object):
      try:
        resultStr = self._core.data.xml.to_string(result._to_xml(context=context))
        resultStatus = result._get_response_status()
        resultHeaders = result._get_response_headers()
        if resultStr is not None:
          resultStr = str(resultStr)
        else:
          resultStr = ""
      except:
        self._core.log_except(txn_id, "Exception when constructing response")
        resultStr = None
    
    # If the result is an old-school Framework Object, return its content, status and headers
    elif isinstance(result, Framework.objects.Object):
      try:
        resultStr = result.Content(context=context)
        resultStatus = result.Status()
        resultHeaders = result.Headers()
        if resultStr is not None:
          resultStr = str(resultStr)
        else:
          resultStr = ""
      except:
        self._core.log_except(txn_id, "Exception when constructing response")
        resultStr = None

    # If the result is a string, convert it to unicode and populate the headers/status with
    # valid values
    elif isinstance(result, basestring):
      resultStr = str(result)
      resultStatus = 200
      resultHeaders = {'Content-type': 'text/plain'}
      
    # If the result is an lxml.etree element, convert it to a unicode string and populate the
    # headers/status with valid values
    elif isinstance(result, etree._Element):
      resultStr = str(self._core.data.xml.to_string(result))
      resultStatus = 200
      resultHeaders = {'Content-type': 'application/xml'}
      
    # If the result is a boolean value, return a 200 for True or a 404 for False
    elif isinstance(result, bool):
      if result == True:
        resultStatus = 200
      else:
        resultStatus = 404
      resultStr = ''
      resultHeaders = {}
      
    # Otherwise, return a 500 error
    if resultStr == None:
      resultStr = ""
      resultStatus = 500
      resultHeaders = {}
      self._core.log_debug(txn_id, "Unable to handle response type: %s", str(type(result)))
      
    # Add response headers from the current context, if available
    if context:
      resultHeaders.update(context.response_headers)

    return resultStatus, resultHeaders, resultStr
    
    #TODO: Check if plugin is broken


  def connect_route(self, path, f, method='GET', **kwargs):
    self._route_managers[method].connect_route(path, f, **kwargs)
    
  def generate_route(self, f, method='GET', **kwargs):
    return self._route_managers[method].generate_route(f, **kwargs)
    
  def match_route(self, path, method='GET', txn_id=None):
    return self._route_managers[method].match_route(path, txn_id)
    
  def generate_callback_path(self, func, indirect=False, ext=None, **kwargs):
    try:
      s = self.generate_route(func, **kwargs)
    except:
      if ext and ext[0] != '.':
        ext = '.'+ext
      else:
        ext = ''
      query_string = self._core.runtime.create_query_string(kwargs)
      if query_string and len(query_string) > 0: query_string = '?' + query_string
      else: query_string = ''
      s = "%s/:/function/%s%s%s" % (self._core.runtime.prefix_handlers.keys()[0], func.__name__, ext, query_string)
    if indirect:
      return indirect_callback_string(s + "&indirect=1")
    return s
        
  def external_resource_path(self, itemname, context=None):
    """
      Generates an external path for accessing a bundled resource file.
    """
    if not itemname: return
    if context:
      prefix = context.prefix
    else:
      prefix = self.prefix_handlers.keys()[0]
    if self._core.storage.resource_exists(itemname):
      return "%s/:/resources/%s" % (prefix, itemname)
    
  def external_shared_resource_path(self, itemname, context=None):
    """
      Generates an external path for accessing a shared resource file.
    """
    if not itemname: return
    if context:
      prefix = context.prefix
    else:
      prefix = self.prefix_handlers.keys()[0]
    if self._core.storage.shared_resource_exists(itemname):
      return "%s/:/sharedresources/%s" % (prefix, itemname)


  # Threading functions
  def _globalize(self, attr):
    if not hasattr(self._core, 'host'):
      return attr
    return self._core.host.globalize(attr)
        
  def create_thread(self, f, log=True, txn_id=None, globalize=True, *args, **kwargs):
    """
      Spawns a new thread with the given function, args & kwargs
    """
    if globalize:
      f = self._globalize(f)
    th = threading.Thread(
      None,
      self._start_thread,
      name=f.__name__,
      args=(),
      kwargs=dict(
        f=f,
        args=args,
        kwargs=kwargs,
        txn_id=txn_id
      )
    )
    th.start()
    if log and (self._core.config.log_internal_component_usage or f.__name__[0] != '_'):
      self._core.log_debug(txn_id, "Created a thread named '%s'" % f.__name__)
    return th
    
  def _start_thread(self, f, args, kwargs, txn_id=None):
    # Internal code for running the given function and handling exceptions
    try:
      f(*args, **kwargs)
    except:
      self._core.log_except(txn_id, "Exception in thread named '%s'", f.__name__)
      
  def create_timer(self, interval, f, log=True, txn_id=None, globalize=True, *args, **kwargs):
    """
      Schedules a thread with the given function, args & kwargs to fire after the given
      interval.
    """
    if globalize:
      f = self._globalize(f)
    timer = threading.Timer(
      interval,
      self._start_timed_thread,
      args=(),
      kwargs=dict(
        f=f,
        log=log,
        args=args,
        kwargs=kwargs,
        txn_id=txn_id
      )
    )
    timer.start()
    if f.__name__[0] != '_':
      if log and (self._core.config.log_internal_component_usage or f.__name__[0] != '_'):
        self._core.log_debug(txn_id, "Scheduled a timed thread named '%s'", f.__name__)
    return timer
    
  def _start_timed_thread(self, f, log, args, kwargs, txn_id=None):
    # Internal code for running the given function and handling exceptions
    if log and (self._core.config.log_internal_component_usage or f.__name__[0] != '_'):
      self._core.log.debug("Starting timed thread named '%s'", f.__name__)
    try:
      f(*args, **kwargs)
    except:
      self._core.log_except(txn_id, "Exception in timed thread named '%s'", f.__name__)
      
  def _key(self, key):
    if key == None:
      raise Framework.FrameworkException('Cannot lock the None object')
    elif isinstance(key, basestring):
      return key
    elif isinstance(key, Framework.code.ContextProxy):
      return id(key._obj())
    else:
      return id(key)
    
  def acquire_lock(self, key, addToLog=True, txn_id=None):
    """
      Acquires a named lock.
    """
    try:
      key = self._key(key)
      if key not in self._thread_locks:
        self._thread_locks[key] = threading.Lock()
      if addToLog:
        if self._core.config.log_internal_component_usage and '_Storage:' not in str(key):
          self._core.log.debug("Acquiring the thread lock '%s'" % str(key))
      self._thread_locks[key].acquire()
      return True
    except:
      self._core.log_except(txn_id, "Unable to acquire the thread lock '%s'" % str(key))
      raise
      
  def release_lock(self, key, addToLog=True, txn_id=None):
    """
      Releases a named lock.
    """
    key = self._key(key)
    if key in self._thread_locks:
      if addToLog:
        if self._core.config.log_internal_component_usage and '_Storage:' not in str(key):
          self._core.log.debug("Releasing the thread lock '%s'" % str(key))
      self._thread_locks[key].release()
      return True
    else:
      self._core.log_except(txn_id, "Unable to find a thread lock named '%s'" % str(key))
      return False
      
  def lock(self, key = None):
    """
      Returns a lock object. If a key is provided, the named lock is returned, otherwise a new
      lock object is generated.
    """
    if key:
      key = self._key(key)
    if key in self._thread_locks:
      lock = self._thread_locks[key]
    else:
      lock = threading.Lock()
      if key != None:
        self._thread_locks[key] = lock
    return lock
      
  def event(self, key = None):
    """
      Returns an event object. If a key is provided, the named event is returned, otherwise a new
      event object is generated.
    """
    if key:
      key = self._key(key)
    if key in self._thread_events:
      event = self._thread_events[key]
    else:
      event = threading.Event()
      if key != None:
        self._thread_events[key] = event
    return event
      
  def block_event(self, key):
    """
      Clears the named event, causing any threads waiting for it to block.
    """
    self.event(key).clear()
    
  def unblock_event(self, key):
    """
      Sets the named event, causing any threads currently waiting for it to be unblocked.
    """
    self.event(key).set()
    
  def wait_for_event(self, key, timeout=None):
    """
      Blocks the calling thread until the named event is set.
    """
    self.event(key).wait(timeout)
    return self.event(key).isSet()
    
  def semaphore(self, key = None, limit=1):
    """
      Returns an semaphore object. If a key is provided, the named semaphore is returned, otherwise
      a new semaphore object is generated.
    """
    if key:
      key = self._key(key)
    if key in self._thread_semaphores:
      sem = self._thread_semaphores[key]
    else:
      sem = threading.Semaphore(limit)
      if key != None:
        self._thread_semaphores[key] = sem
    return sem
    
  @property
  def taskpool(self):
    """
      Returns the runtime's task pool
    """
    return self._taskpool
    
  def create_taskpool(self, threadcount, prioritycount=0):
    """
      Creates a new task pool (not used by the framework - meant for access via CoreKit)
    """
    return TaskPool(self, threadcount)
    
  def _expand_identifier(self, identifier):
    if identifier[0:2] == '..':
      return 'com.plexapp.'+identifier[2:]
    elif identifier[0] == '.':
      return self._core.identifier[:self._core.identifier.rfind('.')]+identifier
    else:
      return identifier

