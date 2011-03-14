#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework


class LogKit(Framework.bases.BaseKit):
  
  def Debug(self, fmt, *args, **kwargs):
    self._core.log_debug(self._txn_id, fmt, *args, **kwargs)
  
  def Info(self, fmt, *args, **kwargs):
    self._core.log_info(self._txn_id, fmt, *args, **kwargs)
  
  def Warn(self, fmt, *args, **kwargs):
    self._core.log_warn(self._txn_id, fmt, *args, **kwargs)
      
  def Error(self, fmt, *args, **kwargs):
    self._core.log_error(self._txn_id, fmt, *args, **kwargs)
  
  def Critical(self, fmt, *args, **kwargs):
    self._core.log_critical(self._txn_id, fmt, *args, **kwargs)
    
  def Exception(self, fmt, *args, **kwargs):
    self._core.log_except(self._txn_id, fmt, *args, **kwargs)

  def __call__(self, fmt, *args, **kwargs):
    self._core.log_info(self._txn_id, fmt, *args, **kwargs)
    
  def _requires_context(self, context):
    return True