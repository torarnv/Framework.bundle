#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#


"""
  Defaults 
"""

default_locale                  = 'en-us'
default_network_timeout         = 20.0
module_whitelist                = ['re', 'string', 'datetime']



"""
  Framework config
"""

default_interface               = 'socket'
log_level                       = 'Debug'
console_logging                 = False

root_path                       = None
plugin_support_dir_name         = None
bundles_dir_name                = None

# These variables are only used when app_support_path is defined
pid_files_dir                   = 'pid'
log_files_dir                   = 'log'
plugin_support_files_dir        = 'support'
bundle_files_dir                = 'bundle'

# These variables override the app support path + individual dir variables if set
pid_file                        = None
log_file                        = None

log_internal_component_usage    = False
show_internal_traceback_frames  = True
enable_external_debugging       = True

messaging_keepalive_interval    = 20
messaging_timeout               = 60

taskpool_maximum_threads        = 8
taskpool_priority_threads       = 2

threadkit_parallel_limit        = 4
agentservice_update_limit       = 3

socket_interface_port           = 0

http_cache_max_items            = 1024
http_cache_max_items_grace      = 100
http_cache_max_size             = 52428800


"""
  Platform config
"""

system_bundle_name              = 'System'
system_bundle_identifier        = 'com.plexapp.system'
services_bundle_name            = 'Services'
services_bundle_identifier      = 'com.plexapp.system.services'
framework_bundle_name           = 'Framework'
framework_bundle_identifier     = 'com.plexapp.framework'

server_version                  = None

os_map = {
  "Darwin"                      : "MacOSX",
  "Linux"                       : "Linux",
  "Windows"                     : "Windows"
}

cpu_map = {
  "i386"                        : "i386",
  "i686"                        : "i386",
  "x86_64"                      : "i386",
  "3548b0-smp"                  : "MIPS",
  "mips"                        : "MIPS",
  "mips64"                      : "mips64",
  "Win32"                       : "Win32",
  "armv5tel"                    : "armv5tel"
}
