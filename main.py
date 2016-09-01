#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import tornado.ioloop
import tornado.httpserver
import tornado.web
import tornado.gen
import os
import datetime
import re
import subprocess
import time
import yaml
from concurrent.futures import ThreadPoolExecutor
from tornado import concurrent
MAX_WORKERS = 4
current_path = os.path.dirname(__file__)

stream = file(os.path.join(current_path, 'conf.yaml'), 'r')
server_list = yaml.load(stream)['server_list']

class MainHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    
    def validate_form(self, appname, logtime):
        if (appname == "") or (logtime == ""):
            return False
        else:
            if appname in server_list.keys():
                if re.match(r'20[12][\d]-[01][\d]-[0-3][\d]$', logtime):
                    return True
            else:
                return False


    def get(self):
        servers = server_list.keys()
        # print(servers)
        self.render("index.html", message='', servers=servers)

    @tornado.gen.coroutine
    def post(self):
        servers = server_list.keys()
        appname = self.get_argument("appname")
        logtime = self.get_argument("logtime")
        #print("appname: %s, logtime: %s" % (appname, logtime))
        if self.validate_form(appname, logtime):
            result = yield self.download(appname, logtime)                
            if result[0] == "success":
                with open(result[1], 'rb') as f:
                    self.set_header('Content-Type', 'application/octet-stream')
                    self.set_header('Content-Description', 'File Download')
                    self.set_header('Content-Disposition', 'attachment; filename='+os.path.basename(result[1]))
                    try:
                        while True:
                            data = f.read(4096)
                            if not data:
                                break
                            self.write(data)
			#self.render("index.html", message="Download Success",servers=servers)
                    except Exception as exc:
                        self.render("index.html", message=exc, servers=servers)

            else:
                self.render("index.html", message=result[1], servers=servers)
        else:
            message="appname or logtime was not validate!"
            self.render("index.html", message=message, servers=servers)
        
    
    @concurrent.run_on_executor
    def download(self, appname, logtime):
        today = datetime.date.isoformat(datetime.date.today())
        # print("logtime:%s, today: %s" % (logtime,  today))
                
        if appname in server_list.keys():
            if logtime != today:
                real_logname = server_list[appname]["logname"] + "." + logtime
                try:
                    origin_size = os.path.getsize("/tmp/"+real_logname+"_"+appname)
                    while True:
                        time.sleep(1)
                        last_size = os.path.getsize("/tmp/"+real_logname+"_"+appname)
                        if last_size != origin_size:
                            origin_size = last_size
                        else:
                            break
                    return ("success",  "/tmp/"+real_logname+"_"+appname)
                except OSError:
                    pass
            else:
                real_logname = server_list[appname]["logname"]
            try:
                #print(server_list[appname])
                result = subprocess.check_output("ssh %s@%s ls %s/%s" % (server_list[appname]["user"],
                                                                         server_list[appname]["ip"],
                                                                         server_list[appname]["logpath"],
                                                                         real_logname), shell=True) 
                #print(result)
                if re.match("%s/%s" % (server_list[appname]["logpath"], real_logname), result):
                    if subprocess.call("scp %s@%s:%s/%s /tmp/%s" % (server_list[appname]["user"], server_list[appname]["ip"], server_list[appname]["logpath"], real_logname, real_logname+"_"+appname),shell=True) == 0:
                        if os.path.exists("/tmp/%s" % real_logname+"_"+appname):
                            return ("success", "/tmp/" + real_logname+"_"+appname)
                        else:
                            return ("fail", "through scp successful, but can not find tmp file on localhost!")
                    else:
                        return ("fail", "error when scp file from server!")
                else:
                    return ("fail", "can not find then log on server matchine!")
            except Exception:
                return ("fail", "no such log file!")
                
        else:
            return ("fail", "To get this appname's log was not suported!") 

 
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookie=True,
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)


if __name__ == "__main__":
    application = tornado.httpserver.HTTPServer(Application())
    application.listen(8000)
    tornado.ioloop.IOLoop.current().start()
