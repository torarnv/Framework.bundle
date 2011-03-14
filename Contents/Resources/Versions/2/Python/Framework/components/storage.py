#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os, os.path, shutil


class Storage(Framework.bases.BaseComponent):
  
  def _init(self):
    self.data_path = os.path.join(self._core.plugin_support_path, 'Data', self._core.identifier)
    self.resource_path = os.path.join(self._core.bundle_path, 'Contents', 'Resources')
    self.shared_resource_path = os.path.join(self._core.framework_path, 'Resources')
    self.walk = os.walk
    self.copy = shutil.copy
    self.rename = os.rename
    self.remove = os.remove
    self.utime = os.utime
    self.dir_name = os.path.dirname
    self.last_accessed = os.path.getatime
    self.last_modified = os.path.getmtime
    Framework.utils.makedirs(os.path.join(self.data_path, 'DataItems'))
    
    os.chdir(self.data_path)
    
  def load(self, filename, binary=True, txn_id=None):
    self._core.runtime.acquire_lock('_Storage:'+filename)
    data = None
    try:
      if binary: mode = 'rb'
      else: mode = 'r'
      f = open(filename, mode)
      data = f.read()
      f.close()
    except:
      self._core.log_except(txn_id, "Exception reading file %s", filename)
      data = None
      raise
    finally:
      self._core.runtime.release_lock('_Storage:'+filename)
      return data
    
  def save(self, filename, data, binary=True, txn_id=None):
    self._core.runtime.acquire_lock('_Storage:'+filename)
    tempfile = '%s/._%s' % (os.path.dirname(filename), os.path.basename(filename))
    try:
      if os.path.exists(tempfile):
        os.remove(tempfile)
      if binary: mode = 'wb'
      else: mode = 'w'
      f = open(tempfile, mode)
      f.write(str(data))
      f.close()
      if os.path.exists(filename):
        os.remove(filename)
      os.rename(tempfile, filename)
    except:
      self._core.log_except(txn_id, "Exception writing to %s", filename)
      if os.path.exists(tempfile):
        os.remove(tempfile)
      raise
    finally:
      self._core.runtime.release_lock('_Storage:'+filename)
      
  def list_dir(self, path):
    return os.listdir(path)
    
  def join_path(self, *args):
    return os.path.join(*args)
    
  def file_exists(self, path):
    return os.path.exists(path)
    
  def dir_exists(self, path):
    return os.path.exists(path) and os.path.isdir(path)
    
  def link_exists(self, path):
    return os.path.exists(path) and os.path.islink(path)
    
  def make_dirs(self, path):
    if not os.path.exists(path):
      os.makedirs(path)
  
  def ensure_dirs(self, path):
    try:
      self.make_dirs(path)
    except:
      if not os.path.exists(path):
        raise

  def remove_tree(self, path):
    if self.dir_exists(path):
      shutil.rmtree(path) 
  
  def load_resource(self, itemname, binary=True):
    return self.load(os.path.join(self.resource_path, itemname), binary)
    
  def load_shared_resource(self, itemname, binary=True):
    return self.load(os.path.join(self.shared_resource_path, itemname), binary)
    
  def resource_exists(self, itemname):
    return os.path.exists(os.path.join(self.resource_path, itemname))
    
  def shared_resource_exists(self, itemname):
    return os.path.exists(os.path.join(self.shared_resource_path, itemname))
  
  def data_item_path(self, itemname):
    return os.path.join(self.data_path, 'DataItems', itemname)  
  
  def data_item_exists(self, itemname):
    return os.path.exists(self.data_item_path(itemname))
    
  def remove_data_item(self, itemname):
    if self.data_item_exists(itemname):
      return os.unlink(self.data_item_path(itemname))
    else:
      return False
      
  def load_data_item(self, itemname, is_object=False):
    if self.data_item_exists(itemname):
      data = self.load(self.data_item_path(itemname))
      if is_object:
        return self._core.data.pickle.load(data)
      else:
        return data
    else:
      return None
    
  def save_data_item(self, itemname, data, is_object=False):
    if is_object:
      data = self._core.data.pickle.dump(data)
    self.save(self.data_item_path(itemname), data)
    
  def file_size(self, path):
    stat = os.stat(path)
    return stat.st_size

