#!/usr/bin/env python

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
import tornado.web
from sockjs.tornado import SockJSRouter, SockJSConnection
import tornado.template

assert tornado.version_info >= (2,4,1)

import os
import json
import argparse

# ROS imports
import roslib; roslib.load_manifest('browser_joystick')
import rospy
from  sensor_msgs.msg import Joy

global joy_pub

class EchoHandler(SockJSConnection):
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

class JSHandler(tornado.web.RequestHandler):
    def initialize(self, cfg):
        self.cfg = cfg
    def get(self):
        self.set_header("Content-Type", "application/javascript")
        buf = self.render_string("web_control.js",**self.cfg)
        self.write(buf)

def im2ascii(im):
    c = unichr(0x2588)

    width,height = im.size
    pixels = list(im.getdata())
    pixels = [pixels[i * width:(i + 1) * width] for i in range(height)]

    result = ''
    for row in pixels:
        for char in row:
            if char == 0:
                result += ' '
            elif char == 255:
                result += c
            else:
                raise ValueError('expected 0 or 255')
        result += '\n'
    return result

def main():
    global joy_pub

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--host', type=str, default=None,
        help='host name or IP address',)
    # use argparse, but only after ROS did its thing
    argv = rospy.myargv()
    args = parser.parse_args(argv[1:])

    settings = dict(
        static_path= os.path.join(os.path.dirname(__file__), "static"),
        cookie_secret=os.urandom(1024),
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        xsrf_cookies= True,
        )

    echo_ws_path = 'echo'
    if args.host is None:
        host = 'localhost'
    else:
        host = args.host
    port = 1024
    base_url = '%s:%d'%(host,port)

    js_path='web_control.js'
    dd = {'base_url':base_url,
          'echo_ws_path':echo_ws_path,
          'js_path':js_path,
          }

    EchoRouter = SockJSRouter(EchoHandler, r'/'+echo_ws_path)

    application = tornado.web.Application([
        (r'/', MainHandler, dict(cfg=dd)),
        (r'/'+js_path, JSHandler, dict(cfg=dd)),
        ]+EchoRouter.urls,
                                          **settings)


    url = "http://%s"%base_url
    print "starting web server at", url
    try:
        import qrencode
    except ImportError:
        qrencode = None
    if qrencode is not None:
        _,_,im = qrencode.encode(url)
        if 1:
            fname = 'link.png'
            im.save(fname)
            print 'URL encoded as a QR code in',fname
        else:
            print im2ascii(im)
    else:
        print 'QR encoded link not done'

    node_name = os.path.splitext(os.path.basename(__file__))[0]
    rospy.init_node( node_name, disable_signals=True )

    joy_pub = rospy.Publisher("joy", Joy)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
