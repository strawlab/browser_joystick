#!/usr/bin/env python

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
import tornado.web
from sockjs.tornado import SockJSRouter, SockJSConnection
import tornado.template

assert tornado.version_info >= (2,4,1)

import os, sys, subprocess
import tempfile
import json
import argparse

# ROS imports
import roslib; roslib.load_manifest('browser_joystick')
import rospy
from  sensor_msgs.msg import Joy

global joy_pub

class JoySockHandler(SockJSConnection):
    def on_message(self, message_raw):
        message = json.loads(message_raw)
        if message['msg']=='lag':
            self.send( json.dumps({
                'start':message['start'],
                }))

        if message['msg']=='joy':
            msg = Joy()
            msg.header.stamp = rospy.Time.now()
            msg.axes = message['axes']
            msg.buttons = message['buttons']
            joy_pub.publish(msg)

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, cfg):
        self.cfg = cfg
    def get(self):
        self.render("web_control.html",**self.cfg)

class JoyHandler(tornado.web.RequestHandler):
    def initialize(self, cfg):
        self.cfg = cfg
    def get(self):
        self.render("joy_web_control.html",**self.cfg)

class MouseHandler(tornado.web.RequestHandler):
    def initialize(self, cfg):
        self.cfg = cfg
    def get(self):
        self.render("mouse_web_control.html",**self.cfg)

class JoyJSHandler(tornado.web.RequestHandler):
    def initialize(self, cfg):
        self.cfg = cfg
    def get(self):
        self.set_header("Content-Type", "application/javascript")
        buf = self.render_string("joy_web_control.js",**self.cfg)
        self.write(buf)

class MouseJSHandler(tornado.web.RequestHandler):
    def initialize(self, cfg):
        self.cfg = cfg
    def get(self):
        self.set_header("Content-Type", "application/javascript")
        buf = self.render_string("mouse_web_control.js",**self.cfg)
        self.write(buf)

def main():
    global joy_pub

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--host', type=str, default='localhost',
        help='host name or IP address',)
    parser.add_argument(
        '--port', type=int, default='9381',
        help='port number',)
    parser.add_argument(
        '--qr', action='store_true', default=False,
        help='show QR code',)
    # use argparse, but only after ROS did its thing
    argv = rospy.myargv()
    args = parser.parse_args(argv[1:])

    settings = dict(
        static_path= os.path.join(os.path.dirname(__file__), "static"),
        cookie_secret=os.urandom(1024),
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        xsrf_cookies= True,
        )

    joy_sock_path = 'joy_sock'
    base_url = args.host
    if args.port != 80:
        base_url = base_url+':'+str(args.port)

    joy_js_path='joy_web_control.js'
    mouse_js_path='mouse_web_control.js'
    dd = {'base_url':base_url,
          'joy_sock_path':joy_sock_path,
          'joy_js_path':joy_js_path,
          'mouse_js_path':mouse_js_path,
          }

    JoySockRouter = SockJSRouter(JoySockHandler, r'/'+joy_sock_path)

    application = tornado.web.Application([
        (r'/', MainHandler, dict(cfg=dd)),

        (r'/joystick', JoyHandler, dict(cfg=dd)),
        (r'/'+joy_js_path, JoyJSHandler, dict(cfg=dd)),

        (r'/mouse', MouseHandler, dict(cfg=dd)),
        (r'/'+mouse_js_path, MouseJSHandler, dict(cfg=dd)),

        ]+JoySockRouter.urls,
                                          **settings)


    url = "http://%s"%base_url
    rospy.loginfo("starting web server at %s" % url)

    if args.qr:
        import qrencode
        import Image
        # encode the URL
        _,_,im = qrencode.encode(url)

        # resize the image to be about 512x512
        target_w = 512
        scale = target_w//im.size[0]
        actual_w = im.size[0]*scale
        actual_h = im.size[1]*scale
        im = im.resize( (actual_w, actual_h), Image.NEAREST )

        # save the image
        fobj = tempfile.NamedTemporaryFile(mode='wb',suffix='.png',
                                           prefix='browser_joy_')
        im.save(fobj,'png')
        fname = fobj.name

        # open the image
        if sys.platform.startswith('linux'):
            cmd = 'xdg-open'
        elif sys.platform.startswith('win'):
            cmd = 'start'
        else:
            # mac?
            cmd = 'open'
        full_cmd = ' '.join([cmd,fname])
        subprocess.call(full_cmd,shell=True)

    node_name = os.path.splitext(os.path.basename(__file__))[0]
    rospy.init_node( node_name, disable_signals=True )

    joy_pub = rospy.Publisher("joy", Joy)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(args.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
