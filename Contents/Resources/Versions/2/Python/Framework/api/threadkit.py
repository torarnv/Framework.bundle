#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import time, Queue, types


class ThreadKit(Framework.bases.BaseKit):
  
  def _init(self):
    self._parallelizer_tasks = None
    
    self._globals = dict(
      thread        = self._thread_decorator,
      spawn         = self._spawn_decorator,
      lock          = self._lock_decorator,
      locks         = self._locks_decorator,
      parallelize   = self._parallelize_decorator,
      parallel      = self._parallel_decorator,
      task          = self._task_decorator,
    )
    
    self.Queue = Queue.Queue
  
  def _key(self, key):
    #print "TKKey:%s" % key
    if key is not None:
      return 'ThreadKit:'+str(self._core.runtime._key(key))
  
  def Create(self, f, globalize=True, *args, **kwargs):
    return self._core.runtime.create_thread(f, True, self._txn_id, globalize, *args, **kwargs)
    
  def CreateTimer(self, interval, f, globalize=True, *args, **kwargs):
    return self._core.runtime.create_timer(interval, f, True, self._txn_id, globalize, *args, **kwargs)
    
  def Sleep(self, interval):
    time.sleep(interval)
    
  def Lock(self, key=None):
    return self._core.runtime.lock(self._key(key))
    
  def AcquireLock(self, key):
    return self._core.runtime.acquire_lock(self._key(key), self._txn_id)
    
  def ReleaseLock(self, key):
    return self._core.runtime.release_lock(self._key(key), self._txn_id)
    
  def Block(self, key):
    return self._core.runtime.block_event(self._key(key))
    
  def Unblock(self, key):
    return self._core.runtime.unblock_event(self._key(key))
    
  def Wait(self, key, timeout=None):
    return self._core.runtime.wait_for_event(self._key(key), timeout)
    
  def Event(self, key=None):
    return self._core.runtime.event(self._key(key))
    
  def Semaphore(self, key=None, limit=1):
    return self._core.runtime.semaphore(self._key(key), limit)
    
  def _requires_context(self, context):
    return Framework.constants.header.transaction_id in context.headers
    
  def _thread_decorator(self, f):
    def _thread_function(*args, **kwargs):
      self.Create(f, *args, **kwargs)
    return _thread_function
    
  def _spawn_decorator(self, f):
    self.Create(f)
    
  def _lock_decorator(self, key, *keys):
    def _lock_decorator_inner(f, *args, **kwargs):
      #print "About to acquire: %s" % key
      _key = self._key(key)
      self._core.runtime.acquire_lock(_key)
      l = list(self._key(k) for k in keys)
      #print "About to lock %s" % str(l)
      for k in l:
        self._core.runtime.acquire_lock(k)
      try:
        return f(*args, **kwargs)
      finally:
        l.reverse()
        for k in l:
          self._core.runtime.release_lock(k)
        self._core.runtime.release_lock(_key)
    return _lock_decorator_inner
  
  def _locks_decorator(self, key, *keys):
    def _locks_decorator_inner(f, key=key):
      def _locks_function(key=key, f=f, *args, **kwargs):
        return self._lock_decorator(key, *keys)(f, *args, **kwargs)
      return _locks_function
    if isinstance(key, types.FunctionType):
      return _locks_decorator_inner(key)
    return _locks_decorator_inner
    
  def _block_decorator(self, f, *args, **kwargs):
    blockname = "ThreadKit:" + f.__name__
    self.Block(blockname)
    ret = f(*args, **kwargs)
    self.Unblock(blockname)
    return ret
    
  def _blocks_decorator(self, f):
    def _blocks_function(*args, **kwargs):
      return self._block_decorator(f, *args, **kwargs)
    return _blocks_function
    
    
  """
    The @parallelize and @task decorators are designed to be used in conjunction with each other - 
    @parallelize decorates a function that defines one or more @task functions. A ThreadKit-specific
    lock is maintained so only one parallelizer can be created at any time. When the parallelizer
    has run, the tasks are queued for dispatch to the runtime's task pool, and the calling thread is
    blocked until all tasks have completed.
  """
  def _parallelize_decorator(self, f, *args, **kwargs):
    self.AcquireLock("_ThreadKit:Parallelizer")
    self._parallelizer_tasks = []
    pool = self._core.runtime.create_taskpool(self._core.config.threadkit_parallel_limit)
    name = f.__name__
    tasks = []
    try:
      f(*args, **kwargs)
      self._core.log_debug(self._txn_id, "Starting a parallel task set named %s with %d tasks", name, len(self._parallelizer_tasks))
      for f in self._parallelizer_tasks:
        obj = pool.add_task(f, globalize=False)
        tasks.append(obj)
    finally:
      self._parallelizer_tasks = None
      self.ReleaseLock("_ThreadKit:Parallelizer")
      pool.wait_for_tasks(tasks)
      del pool
      self._core.log.debug("Parallel task set %s ended", name)
    
  def _task_decorator(self, f):
    self.AcquireLock("_ThreadKit:ParallelizerTask")
    if hasattr(self, '_parallelizer_tasks') and isinstance(self._parallelizer_tasks, list):
      self._parallelizer_tasks.append(f)
    else:
      self._core.log_debug(self._txn_id, "Unable to create a task for %s - not inside a parallelizer!", f.__name__)
    self.ReleaseLock("_ThreadKit:ParallelizerTask")
    
  def _parallel_decorator(self, f):
    def _parallel_function(*args, **kwargs):
      return self._parallelize_decorator(f, *args, **kwargs)
    return _parallel_function