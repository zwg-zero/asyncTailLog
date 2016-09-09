import os
import re
import json
import time
import datetime
import yaml
import subprocess
import tornado.httpserver
import tornado.web
import tornado.gen
import tornado.ioloop
from tornado import websocket
import showlog
from concurrent.futures import ThreadPoolExecutor
from tornado import concurrent
MAX_WORKERS = 4
current_path = os.path.dirname(__file__)

server_list = yaml.load(open(os.path.join(current_path,'conf.yaml'), 'r'))['server_list']

def getSshVariables(app_name, log_time):
    if app_name not in server_list.keys():
        return {"status": False, "message": "The app: %s was not found" % app_name}
    today = datetime.date.isoformat(datetime.date.today())
    if log_time:
        if log_time != today:
            log_name = os.path.join(server_list[app_name]["logpath"],server_list[app_name]["logname"]+"."+log_time)
        else:
            log_name = os.path.join(server_list[app_name]["logpath"],server_list[app_name]["logname"])
        ip = server_list[app_name]["ip"]
        port = server_list[app_name]["port"]
        user = server_list[app_name]["user"]
        return {"status": True, "content": (ip, port, user, log_name)}
    else:
        return {"status": False, "message": "log_time can't be null!"}


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
        self.render("websocket.html", message='', servers=servers)

    @tornado.gen.coroutine
    def post(self):
        servers = server_list.keys()
        appname = self.get_argument("appname")
        logtime = self.get_argument("logtime")
        print("appname: %s, logtime: %s" % (appname, logtime))
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
                        self.render("websocket.html", message=exc, servers=servers)

            else:
                print("the returned error message from download: %s" % result[1])
                self.render("websocket.html", message=result[1], servers=servers)
        else:
            message="appname or logtime was not validate!"
            self.render("websocket.html", message=message, servers=servers)

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
                print("The log's variables: %s" % server_list[appname])
                result = subprocess.check_output("ssh %s@%s ls %s/%s" % (server_list[appname]["user"],
                                                                         server_list[appname]["ip"],
                                                                         server_list[appname]["logpath"],
                                                                         real_logname), shell=True)
                print("The result of remote ls command: %s" % result)
                if re.match("%s/%s" % (server_list[appname]["logpath"], real_logname), result.decode("utf-8").strip()):
                    if subprocess.call("scp %s@%s:%s/%s /tmp/%s" % (server_list[appname]["user"], server_list[appname]["ip"], server_list[appname]["logpath"], real_logname, real_logname+"_"+appname),shell=True) == 0:
                        if os.path.exists("/tmp/%s" % real_logname+"_"+appname):
                            return ("success", "/tmp/" + real_logname+"_"+appname)
                        else:
                            return ("fail", "through scp successful, but can not find tmp file on localhost!")
                    else:
                        return ("fail", "error when scp file from server!")
                else:
                    return ("fail", "can not find then log on server!")
            except Exception as e:
                print("Exception in scp log file process : %s" % str(e))
                return ("fail", "no such log file!")

        else:
            return ("fail", "To get this appname's log was not suported!")

# wrap a file like object for showlog to write to
class FileLikeObject:
    def __init__(self, filelikeobject):
        self.file = filelikeobject
    def write(self, content):
        message = {"status": "start_tail", "message": content}
        self.file.write_message(json.dumps(message))


class SendHandler(websocket.WebSocketHandler):
    clients = set()

    def open(self):
        print("open a websocket")
        if self in SendHandler.clients:
            SendHandler.clients.remove(self)
        SendHandler.clients.add(self)
        message = {'status': "error", "message": 'Starting ... o o o ...\n'}
        self.write_message(json.dumps(message))
        self.stream.set_nodelay(True)
        #self.myShowLog = showlog.TailLog("10.13.2.64", 22, 'zwg', '/home/zwg/log.file')
        #self.myShowLog = showlog.TailLog("172.16.100.201", 22, 'zhouwg_7', '/app/jbp_app/logs/app.log')
        #if not self.myShowLog.connect():
        #    message = {'log': 'error when connect to server'}
        #    self.write_message(json.dumps(message))
        #    return
        #myfile = FileLikeObject(self)
        #self.myShowLog.getTailResult(myfile)


    #def open(self):
    #    SendHandler.clients.add(self)
    #    self.myShowLog = FixShowlog("10.13.2.64", 22, 'zwg', '/home/zwg/log.file')
    #    self.myShowLog.startTail(self)
    #    #self.write_message(json.dumps({'input': 'connected...'}))
    #    self.stream.set_nodelay(True)

    def on_message(self, message):
        message = json.loads(message)
        if message["command"] == "stop_tail":
             if hasattr(self, 'myShowLog') and self.myShowLog:
                    self.myShowLog.close()
        elif message["command"] == "start_tail":
            result = getSshVariables(message["app_name"], message["date"])
            if result["status"]:
                if hasattr(self, 'myShowLog') and self.myShowLog:
                    self.myShowLog.close()
                self.myShowLog = showlog.TailLog(result["content"][0], result["content"][1], result["content"][2],
                                                 result["content"][3])
                if not self.myShowLog.connect():
                    self.write_message(json.dumps({"status":"error", "message": "error when connect to server"}))
                else:
                    self.appname = message["app_name"]
                    myfile = FileLikeObject(self)
                    self.write_message(json.dumps({"status":"error", "message": ""}))
                    print("begain to get tail result")
                    self.myShowLog.getTailResult(myfile)

            else:
                self.write_message(json.dumps({"status":"error","message": result["message"]}))
        elif message["command"] == "more_content":
            result = self.myShowLog.getBackMoreContent()
            if result["status"]:
                self.write_message(json.dumps({"status":"more_content","message":result["message"]}))
            else:
                self.write_message(json.dumps({"status":"error","message":result["message"]}))
        elif message["command"] == "filter_log":
            result = getSshVariables(message["app_name"], message["date"])
            if result["status"]:
                if hasattr(self, 'myShowLog') and self.myShowLog:
                    self.myShowLog.close()
                self.myShowLog = showlog.TailLog(result["content"][0], result["content"][1], result["content"][2],
                                                 result["content"][3])
                if not self.myShowLog.connect():
                    self.write_message(json.dumps({"status":"error", "message": "error when connect to server"}))
                else:
                    print("start_time: %s, end_time: %s" % (message["start_time"], message["end_time"]))
                    myresult = self.myShowLog.executeNotBlockedCommand("/tmp/filtertomcatlines.py %s %s %s" %
                                                                       (message["start_time"],
                                                                        message["end_time"],
                                                                        result["content"][3]))
                    if myresult["status"]:
                        self.write_message(json.dumps({"status": "error", "message": ""}))
                        self.write_message(json.dumps({"status": "filter_log", "message": myresult["message"]}))
                    else:
                        self.write_message(json.dumps({"status": "error", "message": myresult["message"]}))
            else:
                self.write_message(json.dumps({"status":"error","message": result["message"]}))
        else:
            self.write_message(json.dumps({"status":"error","message": "unknown command!"}))

    def on_close(self):
        print("closing a websocket")
        # 客户端主动关闭
        try:
            self.myShowLog.close()
        except Exception:
            pass
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