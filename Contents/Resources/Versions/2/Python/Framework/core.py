#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import os, plistlib, logging, logging.handlers, traceback, sys, signal
import code, policies, components

VERSION               = "2.1.0"
COMPATIBLE_VERSION    = "2.0a1"

POLICY_KEY            = 'PlexPluginCodePolicy'
WHITELIST_KEY         = 'PlexPluginModuleWhitelist'
API_EXCLUSION_KEY     = 'PlexPluginAPIExclusions'
CONSOLE_LOGGING_KEY   = 'PlexPluginConsoleLogging'
LOG_LEVEL_KEY         = 'PlexPluginLogLevel'
AUDIO_CODEC_KEY       = 'PlexAudioCodec'
VIDEO_CODEC_KEY       = 'PlexVideoCodec'
MEDIA_CONTAINER_KEY   = 'PlexMediaContainer'


class LogFilter(logging.Filter):
  def filter(self, record):
    return 0
    
class LogFormatter(logging.Formatter):
  def format(self, record):
    for key in record.__dict__:
      if key[0] != '_' and isinstance(record.__dict__[key], str):
        record.__dict__[key] = uni(record.__dict__[key])
    return logging.Formatter.format(self, record)

class FrameworkCore(object):
  def __init__(self, bundle_path, framework_path, config_module):
    self.bundle_path = bundle_path
    self.framework_path = framework_path
    self.config = config_module
    
    self.version = VERSION
    self.compatible_version = COMPATIBLE_VERSION
    
    self.attributes = dict()
    
    #TODO: Read from environment variable
    if self.config.root_path:
      self.app_support_path = self.config.root_path
      
      # Set defaults if not provided
      if not self.config.bundles_dir_name:
        self.config.bundles_dir_name = self.config.bundle_files_dir
      if not self.config.plugin_support_dir_name:
        self.config.plugin_support_dir_name = self.config.plugin_support_files_dir
    
    else:
      if sys.platform == "win32":
        self.app_support_path = os.environ["PLEXLOCALAPPDATA"]    
      else:
        self.app_support_path = os.path.join(os.environ["HOME"], 'Library', 'Application Support', 'Plex Media Server')
        
      # Set defaults if not provided
      if not self.config.bundles_dir_name:
        self.config.bundles_dir_name = 'Plug-ins'
      if not self.config.plugin_support_dir_name:
        self.config.plugin_support_dir_name = 'Plug-in Support'
        
    self.plugin_support_path = os.path.join(self.app_support_path, self.config.plugin_support_dir_name)
    
    # Read the plist file
    self.plist_path = os.path.join(bundle_path, 'Contents', 'Info.plist')
    bundle_plist = plistlib.readPlist(self.plist_path)
    
    self.identifier = bundle_plist["CFBundleIdentifier"]
    if API_EXCLUSION_KEY in bundle_plist:
      self._api_exclusions = list(bundle_plist[API_EXCLUSION_KEY])
    else:
      self._api_exclusions = list()
      
    if CONSOLE_LOGGING_KEY in bundle_plist:
      self.config.console_logging = (str(bundle_plist[CONSOLE_LOGGING_KEY]) == '1')
    
    if LOG_LEVEL_KEY in bundle_plist:
      self.config.log_level = bundle_plist[LOG_LEVEL_KEY]  
    
    self.storage = components.Storage(self)
    self._configure_logging()
    
    try:
      version_path = os.path.abspath(os.path.join(self.framework_path, '..', '..', '..', 'VERSION'))
      f = open(version_path, 'r')
      self.build_info = f.read()
      f.close()
    except:
      self.build_info = 'No build information available'
      
    self.log.debug('Starting framework core - Version: %s, Build: %s', self.version, self.build_info)
    
    _whitelist = list()
    _syspaths = list()
    
    # Decide which security policy to use
    policy = policies.StandardPolicy
    
    if POLICY_KEY in bundle_plist:
      policy_name = bundle_plist[POLICY_KEY]
      policy_key = policy_name + 'Policy'
      if hasattr(policies, policy_key):
        policy = getattr(policies, policy_key)
        #TODO: Check the code signature
        self.log.debug("Using the %s security policy", policy_name.lower())
        
        # Check for a whitelist in the plist file
        if policy.allow_whitelist_extension and WHITELIST_KEY in bundle_plist:
          _whitelist.extend(bundle_plist[WHITELIST_KEY])
          
    if policy == policies.StandardPolicy:
      self.log.debug("Using the standard security policy")
    
    self._policy = policy
    
    [self.copy_attribute(bundle_plist, attr_name) for attr_name in (AUDIO_CODEC_KEY, VIDEO_CODEC_KEY, MEDIA_CONTAINER_KEY)]
    del bundle_plist
    
    self.code_path = os.path.join(bundle_path, 'Contents', 'Code')
    self.init_path = os.path.join(self.code_path, '__init__.py')
    
    self.loader = code.CodeLoader()

    # Initialize each of the core components
    self.runtime        = components.Runtime(self)
    self.caching        = components.Caching(self)
    self.data           = components.Data(self)
    self.networking     = components.Networking(self)
    self.localization   = components.Localization(self)
    self.messaging      = components.Messaging(self)
    
    # Create a metadata model accessor for this plug-in
    self._metadata_model_accessor = Framework.modelling.ModelAccessor(
      self,
      'metadata',
      self.storage.join_path(self.framework_path, 'Models', 'Metadata', '__init__.pym'),
      self.storage.join_path(self.app_support_path, 'Metadata')
    )
    
    if policy.allow_bundled_libraries:
      sys.path.insert(0, os.path.join(self.bundle_path, 'Contents', 'Libraries', self.runtime.os, self.runtime.cpu).encode('utf-8'))
      sys.path.insert(0, os.path.join(self.bundle_path, 'Contents', 'Libraries', 'Shared').encode('utf-8'))
    
    # Load services
    self.services_bundle_path = self.path_for_bundle(self.config.services_bundle_name, self.config.services_bundle_identifier)
    self.services = ServiceStore(self)
        
    self.host = code.CodeHost(self, self.code_path, policy)
    
    for name in self.config.module_whitelist:
      if name not in self.host._policy_instance._whitelist:
        self.host._policy_instance._whitelist.append(name)
        
    if len(_whitelist) > 0:
      for name in _whitelist:
        if name in self.host._policy_instance._whitelist:
          _whitelist.remove(name)
      self.log.debug("Extending whitelist: %s", str(_whitelist))
      self.host._policy_instance._whitelist.extend(_whitelist)
      
    self.log.debug("Finished starting framework core")
    
  def copy_attribute(self, bundle_plist, attr_name):
    if attr_name in bundle_plist:
      self.attributes[attr_name] = [x.replace('.', '').lower() for x in bundle_plist[attr_name]]
    
  def load_code(self, elevated=False):
    self.log.debug("Loading plug-in code")
    try:
      self.init_code = self.loader.load(self.init_path, elevated)
      return True
    except:
      self.log_except(None, 'Exception while loading code')
      return False
      
  def log_msg(self, txn_id, func, fmt, *args, **kwargs):
    if txn_id:
      fmt = ('[T:%s] ' % str(txn_id)) + fmt
    func(fmt, *args, **kwargs)
    
  def log_debug(self, txn_id, fmt, *args, **kwargs):
    self.log_msg(txn_id, self.log.debug, fmt, *args, **kwargs)
    
  def log_info(self, txn_id, fmt, *args, **kwargs):
    self.log_msg(txn_id, self.log.info, fmt, *args, **kwargs)
    
  def log_warn(self, txn_id, fmt, *args, **kwargs):
    self.log_msg(txn_id, self.log.warn, fmt, *args, **kwargs)
    
  def log_error(self, txn_id, fmt, *args, **kwargs):
    self.log_msg(txn_id, self.log.error, fmt, *args, **kwargs)
    
  def log_critical(self, txn_id, fmt, *args, **kwargs):
    self.log_msg(txn_id, self.log.critical, fmt, *args, **kwargs)
    
  def log_except(self, txn_id, fmt, *args):
    self.log_critical(txn_id, self.traceback(fmt % tuple(args)))
    
  def log_exception(self, fmt, *args):
    self.log_except(None, fmt, *args)

  def _configure_logging(self):
    logging.basicConfig()
    logger = logging.getLogger()
    logger.handlers[0].addFilter(LogFilter())
    
    self.log = logging.getLogger(self.identifier)
    
    if self.config.log_level == 'Critical':
      self.log.setLevel(logging.CRITICAL)
    elif self.config.log_level == 'Error':
        self.log.setLevel(logging.ERROR)
    elif self.config.log_level == 'Warning':
      self.log.setLevel(logging.WARNING)
    elif self.config.log_level == 'Info':
      self.log.setLevel(logging.INFO)
    else:
      self.log.setLevel(logging.DEBUG)
    
    if self.config.log_file:
      log_dir = os.path.dirname(self.config.log_file)
    elif self.config.root_path:
      log_dir = os.path.join(self.config.root_path, self.config.log_files_dir)
    elif sys.platform == 'win32':
      log_dir = os.path.join(os.environ['PLEXLOCALAPPDATA'], 'Logs', 'PMS Plugin Logs')
    else:
      log_dir = os.path.join(os.environ['HOME'], 'Library', 'Logs', 'PMS Plugin Logs')

    log_config = dict(identifier = self.identifier, port = self.config.socket_interface_port)
    if self.config.root_path:
      log_file = os.path.join(log_dir, '%(identifier)s.%(port)d.log' % log_config)
    elif not self.config.log_file:
      log_file = os.path.join(log_dir, self.identifier+'.log')
    else:
      log_file = self.config.log_file % log_config
    
    self.storage.ensure_dirs(log_dir)
    rollover = os.path.exists(log_file)
    
    if self.config.console_logging == True:
      console_handler = logging.StreamHandler()
      console_formatter = LogFormatter('%(asctime)-15s - %(name)-32s (%(thread)x) :  %(levelname)s (%(module)s) - %(message)s')
      console_handler.setFormatter(console_formatter)
      self.log.addHandler(console_handler)
    
    file_handler = logging.handlers.RotatingFileHandler(log_file, mode='w', maxBytes=1048576, backupCount=5)
    file_formatter = LogFormatter('%(asctime)-15s (%(thread)x) :  %(levelname)s (%(module)s) - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    if rollover:
      try:
        file_handler.doRollover()
      except:
        self.log_except(None, 'Exception performing logfile rollover')
        
    self.log.addHandler(file_handler)
    
  """ Dump the stack of all threads to the specified file """
  def dump_thread_stacks(self, file):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name[threadId], threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))

    f = open(file, "w")
    f.write("\n".join(code))
    f.close()
    
  def traceback(self, msg='Traceback'):
    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
    full_entry_list = traceback.extract_tb(exceptionTraceback)
    if not self.config.show_internal_traceback_frames:
      entry_list = []
      for entry in full_entry_list:
        if not ('/%s.bundle/' % self.config.framework_bundle_name in entry[0] or '/%s/' % self.config.framework_bundle_identifier in entry[0]):
          entry_list.append(entry)
    else:
      entry_list = full_entry_list
    traceback_str = ''.join(traceback.format_list(entry_list)) + ''.join(traceback.format_exception_only(exceptionType, exceptionValue))
    return "%s (most recent call last):\n%s" % (msg, traceback_str)
    
  def start(self):
    try:
      self.host.execute(self.init_code)
      
      self.log.debug("Running pre-flight checks")
      for name in self.host._policy_instance.api:
        kit = self.host._policy_instance.api[name]
        if isinstance(kit, Framework.bases.BaseKit):
          kit._preflight()
        
      self.host.call_named_function('Start')
      self.log.info("Started plug-in")
      return True
    except:
      self.log_except(None, "Exception starting plug-in")
      return False
      
  def path_for_bundle(self, name, identifier):
    # Check if a cloud path exists - if not, use the local naming format
    bundles_path = self.storage.join_path(self.app_support_path, self.config.bundles_dir_name)
    cloud_path = self.storage.join_path(bundles_path, identifier)
    if self.storage.dir_exists(cloud_path):
      return cloud_path
    return self.storage.join_path(bundles_path, name + '.bundle')
      

class URLServiceRecord(Framework.bases.Base):
  def __init__(self, core, name, pattern, linked_plugin):
    Framework.bases.Base.__init__(self, core)
    self.name = name
    self.pattern = pattern
    self.linked_plugin = linked_plugin
    self.path = self._core.storage.join_path(self._core.services_bundle_path, 'Contents', 'URL Services', name)
  
class SearchServiceRecord(Framework.bases.Base):
  def __init__(self, core, name, identifier):
    Framework.bases.Base.__init__(self, core)
    self.name = name
    self.identifier = identifier
    self.path = self._core.storage.join_path(self._core.services_bundle_path, 'Contents', 'Search Services', name)

class ServiceStore(Framework.bases.Base):
  def _init(self):
    self.url_services = {}
    self.search_services = {}
    
    self._load_services(self._core.services_bundle_path, allow_linking=True)
    self._load_services(self._core.bundle_path, allow_linking=False)
    self._core.log.debug('Loaded services')
    
  def _load_services(self, path, allow_linking):
    try:
      plist_path = self._core.storage.join_path(path, 'Contents', 'Info.plist')
      if not self._core.storage.file_exists(plist_path):
        return

      # Load the services plist if it exists
      plist = plistlib.readPlist(plist_path)
    
      # Check for URL services and create a record for each one
      if 'PlexURLServices' in plist:
        for service_name in plist['PlexURLServices']:
          service = plist['PlexURLServices'][service_name]
          pattern = service.get('URLPattern')
          linked_plugin = service.get('LinkedPlugin') if allow_linking else self._core.identifier
          self.url_services[service_name] = URLServiceRecord(self._core, service_name, pattern, linked_plugin)
      
      # And the same for search services
      if 'PlexSearchServices' in plist:
        search_plist = plist['PlexSearchServices']
        for service_name in search_plist:
          service_identifier = search_plist[service_name]
          self.search_services[service_identifier] = SearchServiceRecord(self._core, service_name, service_identifier)
    except:
      self._core.log_exception("Unable to load services")
