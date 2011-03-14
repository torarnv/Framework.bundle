#
#  Plex Extension Framework
#  Copyright (C) 2008-2010 Plex Development Team (James Clarke, Elan Feingold). All Rights Reserved.
#

import Framework
from pipeinterface import PipeInterface
import sys, string, socket, weakref

import tornado.httpserver
import tornado.web
import tornado.ioloop


class PluginRequestHandler(tornado.web.RequestHandler):
  _core = None
  
  @property
  def _core(self):
    return type(self)._core
  
  @tornado.web.asynchronous
  def get(self):
    self._core.runtime.create_thread(self._handle_request)
    
  @tornado.web.asynchronous
  def put(self):
    self._core.runtime.create_thread(self._handle_request)
    
  def _handle_request(self):
    status, headers, body = type(self)._core.runtime.handle_request(self.request.uri, self.request.headers, self.request.method)
    
    self.set_status(status)
    self._headers = headers
    
    self.write(body)
    self.finish()


class SocketInterface(PipeInterface):
    
  def listen(self, daemonized):
    self._core.log.debug('Starting socket server')
    port = self._core.config.socket_interface_port
    
    if port == 0:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.bind(('',0))
      t = s.getsockname()
      s.close()
      port = t[1]
    
    self._core.runtime._interface_args['port'] = port
    
    PluginRequestHandler._core = self._core
    application = tornado.web.Application([
      (r".*", PluginRequestHandler)
    ], transforms=[])
    server = tornado.httpserver.HTTPServer(application)
    server.listen(port)
    self._core.runtime.create_thread(tornado.ioloop.IOLoop.instance().start)
    self._core.log.info("Socket server started on port %s", port)

    if not daemonized:
      PipeInterface.listen(self, False)
    