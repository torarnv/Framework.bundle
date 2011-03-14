#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os, copy


class DictKit(Framework.bases.BaseKit):
  def _init(self):
    self._dict = {}
    self._dict_path = os.path.join(self._core.storage.data_path, 'Dict')
    self._default_dict_path = os.path.join(self._core.bundle_path, 'Contents', 'DefaultDict.json')
    
    self._should_save = False
    self._save_scheduled = False
    self._loaded = False
    
    self._lock = self._core.runtime.lock()
    
  def Reset(self):
    self._core.log.info("Resetting the dictionary")
    self._lock.acquire()
    try:
      self._check_loaded()
      self._should_save = False
      if os.path.exists(self._dict_path):
        os.unlink(self._dict_path)
      self._load_defaults()
    finally:
      self._lock.release()
      
  def Save(self):
    self._really_save()
      
  def __getitem__(self, key):
    self._lock.acquire()
    try:
      self._check_loaded()
      if key in self._dict:
        return self._dict[key]
    finally:
      self._lock.release()
  
  def __setitem__(self, key, value):
    self._lock.acquire()
    try:
      self._check_loaded()
      if isinstance(value, Framework.code.ContextProxy):
        self._dict[key] = value._obj()
      else:
        self._dict[key] = value
      self._save()
    finally:
      self._lock.release()
    
  def __iter__(self):
    self._lock.acquire()
    try:
      self._check_loaded()
      return self._dict.__iter__()
    finally:
      self._lock.release()
      
  def __len__(self):
    self._lock.acquire()
    try:
      self._check_loaded()
      return self._dict.__len__()
    finally:
      self._lock.release()
      
  def __delitem__(self, key):
    self._lock.acquire()
    try:
      self._check_loaded()
      del self._dict[key]
      self._save()
    finally:
      self._lock.release()
    
  def _check_loaded(self):
    if not self._loaded:
      self._load()
      
  def _load(self):
    if os.path.exists(self._dict_path):
      try:
        pickled_dict = self._core.storage.load(self._dict_path)
        unpickled_dict = self._core.data.pickle.load(pickled_dict)
        del pickled_dict
        self._dict = unpickled_dict
        self._core.log.info("Loaded the dictionary file")
      except:
        self._core.log.error("The dictionary file is corrupt and couldn't be loaded")
        self._load_defaults()
    else:
      self._load_defaults()
    self._loaded = True
    
  def _save(self):
    if not self._save_scheduled:
      self._core.runtime.create_timer(5, self._really_save)
      self._save_scheduled = True
    self._should_save = True
      
  def _load_defaults(self):
    if os.path.exists(self._default_dict_path):
      try:
        default_dict_json = self._core.storage.load(self._default_dict_path)
        self._dict = self._core.data.json.from_string(default_dict_json)
        del default_dict_json
        self._core.log.info("Loaded the default dictionary")
      except:
        self._core.log.critical("Unable to load the default dictionary - excpetion thrown")
        self._dict = dict()
    else:
      self._core.log.info("No default dictionary file")
    
  def _really_save(self):
    self._lock.acquire()
    try:
      if self._should_save:
        # Create a copy of the dictionary & pickle it
        pickled_dict = self._core.data.pickle.dump(self._dict)
      
        # Save the pickled dictionary
        self._core.storage.save(self._dict_path, pickled_dict)
        del pickled_dict
        
        self._core.log.info("Saved the dictionary file")
        
      self._save_scheduled = False
      self._should_save = False

    finally:
      self._lock.release()
    


class CacheKit(Framework.bases.BaseKit):

  def __getitem__(self, key):
    return self._core.caching.get_cache_manager(key)



class DataKit(Framework.bases.BaseKit):
  
  def _init(self):
    self._dict = DictKit(self._core, self._policy_instance)
    self._cache = CacheKit(self._core, self._policy_instance)
    self._globals = dict(
      Dict = self._dict,
      Cache = self._cache,
    )
  
  def Load(self, item):
    return self._core.storage.load_data_item(item)
    
  def LoadObject(self, item):
    return self._core.storage.load_data_item(item, is_object=True)
    
  def Save(self, item, data):
    return self._core.storage.save_data_item(item, data)
    
  def SaveObject(self, item, obj):
    return self._core.storage.save_data_item(item, obj, is_object=True)
    
  def Exists(self, item):
    return self._core.storage.data_item_exists(item)
    
  def Remove(self, item):
    return self._core.storage.remove_data_item(item)
