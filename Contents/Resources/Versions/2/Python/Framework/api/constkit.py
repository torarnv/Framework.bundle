#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework

class ClientPlatforms(object):
  MacOSX                  = 'MacOSX'
  Linux                   = 'Linux'
  Windows                 = 'Windows'
  iOS                     = 'iOS'
  Android                 = 'Android'
  
class Protocols(object):
  Shoutcast               = 'shoutcast'
  WebKit                  = 'webkit'
  HTTPStreamingVideo      = 'http-streaming-video'
  HTTPStreamingVideo720p  = 'http-streaming-video-720p'
  HTTPMP4Video            = 'http-mp4-video'
  HTTPMP4Video720p        = 'http-mp4-video-720p'
  HTTPVideo               = 'http-video'
  RTMP                    = 'rtmp'
  HTTPLiveStreaming       = 'http-live-streaming'
  HTTPMP4Streaming        = 'http-mp4-streaming'
  
class ServerPlatforms(object):
  MacOSX_i386             = 'MacOSX-i386'
  Linux_i386              = 'Linux-i386'
  Linux_x86_64            = 'Linux-x86_64'
  Linux_MIPS              = 'Linux-MIPS'
  Linux_ARM               = 'Linux-ARM'
  
class ViewTypes(object):
  Grid                    = 'grid'
  List                    = 'list'
  
class SummaryTextTypes(object):
  NoSummary               = 0
  Short                   = 1
  Long                    = 2
  
class AudioCodecs(object):
  AAC                     = 'aac'
  MP3                     = 'mp3'
  
class VideoCodecs(object):
  H264                    = 'h264'
  
class Containers(object):
  MKV                     = 'mkv'
  MP4                     = 'mp4'
  MOV                     = 'mov'
  AVI                     = 'avi'

class ConstKit(Framework.bases.BaseKit):
  
  root_object = False
  
  def _init(self):
    self._globals = dict(
      CACHE_1MINUTE       = 60,
      CACHE_1HOUR         = 3600,
      CACHE_1DAY          = 86400,
      CACHE_1WEEK         = 604800,
      CACHE_1MONTH        = 2592000,
      ClientPlatform      = ClientPlatforms,
      ServerPlatform      = ServerPlatforms,
      Protocol            = Protocols,
      ViewType            = ViewTypes,
      SummaryType         = SummaryTextTypes,
      AudioCodec          = AudioCodecs,
      VideoCodec          = VideoCodecs,
      Container           = Containers,
    )
    