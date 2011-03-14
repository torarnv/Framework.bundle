#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
import socket, struct, base64
from socket import AF_INET, SOCK_DGRAM

#TODO: Push client list down from PMS when changes detected via bonjour, and only allow valid clients to be used
#TODO: Screenshots, key chars

class PlayerCommand(object):
  def __init__(self, command, **kwargs):
    self._command = command
    self._kwargs = kwargs
    
  def _function_arg_str(self, **kwargs):
    function_args = dict(self._kwargs)
    function_args.update(kwargs)
    formatted_args = self._format_args(**function_args)
    if len(formatted_args) > 0:
      return '(%s)' % formatted_args
    else:
      return ""
    
  def _format_args(self, **kwargs):
    return ""
    
  def _format_response(self, response):
    return response
    
  def __call__(self, **kwargs):
    pass


class UDPCommand(PlayerCommand):  

  def __call__(self, **kwargs):
    cmd = self._command + self._function_arg_str(**kwargs)
    self._player._send_udp_command(cmd)
    
    
class HTTPCommand(PlayerCommand):  

  def __call__(self, **kwargs):
    cmd = self._command + self._function_arg_str(**kwargs)
    return self._format_response(self._player._send_http_command(cmd))

    
class PlayFileCommand(HTTPCommand):  
  def __init__(self, **kwargs):
    HTTPCommand.__init__(self, 'PlayFile', **kwargs)
    
  def _format_args(self, path, userAgent=None, httpCookies=None):
    ret = path
    if userAgent or httpCookies:
      ret += ';'
      if userAgent:
        ret += userAgent
      ret += ';'
      if httpCookies:
        ret += httpCookies
    return ret


class PlayMediaCommand(HTTPCommand):  
  def __init__(self, **kwargs):
    HTTPCommand.__init__(self, 'PlayMedia', **kwargs)

  def _format_args(self, path, key, userAgent='%20', httpCookies='%20', viewOffset='%20'):
    ret = path + ';' + key
    if userAgent or httpCookies or viewOffset:
      ret += ';'
      if userAgent:
        ret += userAgent.replace(' ','+')
      ret += ';'
      if httpCookies:
        ret += httpCookies
      ret += ';'
      if viewOffset:
        ret += viewOffset
    return ret
    
class SetVolumeCommand(HTTPCommand):
  def __init__(self, **kwargs):
    HTTPCommand.__init__(self, 'setvolume', **kwargs)
    
  def _format_args(self, level):
    return str(level)
  
    
class ScreenshotCommand(HTTPCommand):
  def __init__(self, **kwargs):
    HTTPCommand.__init__(self, 'takescreenshot', **kwargs)
  
  def _format_args(self, width=480, height=270, quality=75):
    return ";false;0;%s;%s;%s;true" % (str(width), str(height), str(quality))
  
  def _format_response(self, response):
    return base64.b64decode(response[7:-8])
  

class SendKeyCommand(PlayerCommand):
  def __init__(self, virtual=False):
    PlayerCommand.__init__(self, 'SendKey')
    if virtual:
      self._base_code = 0xF100
    else:
      self._base_code = 0xF000
      
  def __call__(self, code):
    cmd = 'SendKey(%s)' % str(hex(self._base_code + int(code)))
    self._player._send_http_command(cmd)

  
class SendStringCommand(SendKeyCommand):
  def __init__(self):
    SendKeyCommand.__init__(self, virtual=True)
    
  def __call__(self, text):
    for char in text:
      SendKeyCommand.__call__(self, ord(char))
      
      
class PlayerController(object):
  def __init__(self, player, **commands):
    self._player = player
    for name in commands:
      commands[name]._player = player
    self.command_dict = commands

  def __getattr__(self, name):
    if name in self.command_dict:
      return self.command_dict[name]


class PlayerInstance(object):
  def __init__(self, core, host, udp_port=9777, http_port=3000):
    self._cmd_fmt = "\x58\x42\x4D\x43\x02\x00\x00\x0A\x00\x00\x00\x01\x00\x00\x00\x01%s\x49\x9D\xFA\x3A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02%s\x00"
    self._socket = socket.socket(AF_INET, SOCK_DGRAM)
    self._core = core
    self._host = self._core.networking.resolve_hostname_if_required(host)
    self._udp_port = udp_port
    self._http_port = http_port
    
    self.Navigation   = PlayerController(self,
      MoveUp          = UDPCommand("Up"),
      MoveDown        = UDPCommand("Down"),
      MoveLeft        = UDPCommand("Left"),
      MoveRight       = UDPCommand("Right"),
      PageUp          = UDPCommand("PageUp"),
      PageDown        = UDPCommand("PageDown"),
      NextLetter      = UDPCommand("NextLetter"),
      PreviousLetter  = UDPCommand("PrevLetter"),
      Select          = UDPCommand("Select"),
      Back            = UDPCommand("ParentDir"),
      ContextMenu     = UDPCommand("ContextMenu"),
      ToggleOSD       = UDPCommand("OSD")
    )
    
    self.Playback     = PlayerController(self,
      Play            = UDPCommand("Play"),
      Pause           = UDPCommand("Pause"),
      Stop            = UDPCommand("Stop"),
      Rewind          = UDPCommand("Rewind"),
      FastForward     = UDPCommand("FastForward"),
      StepForward     = UDPCommand("StepForward"),
      BigStepForward  = UDPCommand("BigStepForward"),
      StepBack        = UDPCommand("StepBack"),
      BigStepBack     = UDPCommand("BigStepBack"),
      SkipNext        = UDPCommand("SkipNext"),
      SkipPrevious    = UDPCommand("SkipPrevious")
    )
    
    self.Application  = PlayerController(self,
      PlayFile        = PlayFileCommand(),
      PlayMedia       = PlayMediaCommand(),
      SetVolume       = SetVolumeCommand(),
      Screenshot      = ScreenshotCommand(),
      SendString      = SendStringCommand(),
      SendKey         = SendKeyCommand(virtual=False),
      SendVirtualKey  = SendKeyCommand(virtual=True),
    )
  
  def _send_udp_command(self, cmd):
    self._socket.sendto(self._cmd_fmt % (struct.pack(">H", len(cmd)+2), cmd), (self._host, self._udp_port))
    
  def _send_http_command(self, cmd):
    response = self._core.networking.http_request(("http://%s:%s/xbmcCmds/xbmcHttp?command=" % (self._host, self._http_port)) + cmd, cacheTime=0, immediate=True)
    return response.content

class PlayerKit(Framework.bases.BaseKit):
  def _init(self):
    self._instances = dict()
  
  def __getitem__(self, name):
    if name not in self._instances:
      self._instances[name] = PlayerInstance(self._core, name)
    return self._instances[name]
    