import os
import sys
import json
import time
import yaml
import tornado.httpserver
import tornado.web
import tornado.ioloop
from tornado import websocket
import showlog

server_list = yaml.load(open('conf.yaml', 'r'))['server_list']

#class FixShowlog(showlog.TailLog):
#    def innerStartTail(self, writeobject):
#        self.linkHandler.connect(self.host, self.port, self.user, pkey=self.key, timeout=3)
#        stdin, stdout, stderr = self.linkHandler.exec_command('tail -50f %s' % self.fullFileName)
#        while True:
#            line = stdout.readline()
#            if line:
#                writeobject.write_message(line)
#            else:
#                #writeobject.write_message("End of file or Error in reading file!\n")
#                break

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("websocket.html", message='', servers="")

# wrap a file like object for showlog to write to
class FileLikeObject:
    def __init__(self, filelikeobject):
        self.file = filelikeobject
    def write(self, content):
        self.file.write_message(content)


class SendHandler(websocket.WebSocketHandler):
    clients = set()

    def open(self):
        SendHandler.clients.add(self)
        message = {'log': 'Please click tailLog to start\n'}
        self.write_message(json.dumps(message))
        self.stream.set_nodelay(True)
        #self.myShowLog = showlog.TailLog("10.13.2.64", 22, 'zwg', '/home/zwg/log.file')
        self.myShowLog = showlog.TailLog("172.16.100.201", 22, 'zhouwg_7', '/app/jbp_app/logs/app.log')
        if not self.myShowLog.connect():
            message = {'log': 'error when connect to server'}
            self.write_message(json.dumps(message))
            return
        myfile = FileLikeObject(self)
        self.myShowLog.getTailResult(myfile)


    #def open(self):
    #    SendHandler.clients.add(self)
    #    self.myShowLog = FixShowlog("10.13.2.64", 22, 'zwg', '/home/zwg/log.file')
    #    self.myShowLog.startTail(self)
    #    #self.write_message(json.dumps({'input': 'connected...'}))
    #    self.stream.set_nodelay(True)

    def on_message(self, message):
        message = json.loads(message)
        if message["command"]:
            self.write_message(json.dumps({'input': 'response...'}))
        i = 0
        while i <= 10:
            i += 1
            self.write_message(json.dumps(message))
            time.sleep(1)
        # 服务器主动关闭
        self.close()
        SendHandler.clients.remove(self)

    def on_close(self):
        # 客户端主动关闭
        self.myShowLog.close()
        SendHandler.clients.remove(self)

if __name__ == '__main__':
    app = tornado.web.Application(
        handlers=[
            (r"/", IndexHandler),
            (r"/send", SendHandler)
        ],
        debug = False,
        template_path = os.path.join(os.path.dirname(__file__), "template"),
        static_path = os.path.join(os.path.dirname(__file__), "static")
    )
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(8200)
    tornado.ioloop.IOLoop.instance().start()