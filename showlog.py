#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import time
import paramiko
from threading import Thread
#from queue import Queue
#from queue import Queue, Empty
#from multiprocessing import Process, Queue
from queue import Empty

userName = os.getenv("USER")
priKey = '/home/%s/.ssh/id_rsa' % userName
knownHostKey = '/home/%s/.ssh/known_hosts' % userName
# print(priKey)
TAILLINE = 200
MORELINE = 100

class UnexpectedEndOfStream(Exception):
    pass


class TailLog:
    def __init__(self, hostname, port, username, fullfilename, prikey=priKey, knownHostKey=knownHostKey):
        self.host = hostname
        self.port = port
        self.user = username
        self.fullFileName = fullfilename
        self.key = paramiko.RSAKey.from_private_key_file(prikey)
        self.knownHostKey = knownHostKey
        self.linkHandler = paramiko.SSHClient()
        self.linkHandler.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.linkHandler.load_host_keys(self.knownHostKey)
        self.line_start = 1
        self.tail_pid = ""

    # just establish the ssh connection
    def is_connected(self):
        transport = self.linkHandler.get_transport() if self.linkHandler else None
        return transport and transport.is_active()

    def connect(self):
        try:
            self.linkHandler.connect(self.host, self.port, self.user, pkey=self.key, timeout=3)
        except Exception as e:
            print("Error when connect to server, " + str(e))
            return False
        else:
            return True

    def close(self):
        self.closeTail()
        self.linkHandler.close()

    # kill tail -f command on remote server. The pid of the tail is obtained from shell exec, which
    # is same as the tail pid
    def closeTail(self):
        if self.tail_pid:
            try:
                self.linkHandler.exec_command('kill -9 %s' % self.tail_pid)
            except Exception:
                pass

    def _execute(self, command):
        command = 'echo $$; exec ' + command
        stdin, stdout, stderr = self.linkHandler.exec_command(command)
        pid = stdout.readline().strip()
        return pid, stdin, stdout, stderr

    # a general command execute for not blocking command
    def executeNotBlockedCommand(self, command):
        _, _, stdout, stderr = self._execute(command)
        err_message = stderr.read().decode("utf-8")
        if err_message:
            #print(err_message)
            if re.search("No such file", err_message):
                return {"status": False, "message": "****No Such Log File****"}
            else:
                return {"status": False, "message": err_message}
        else:
            message = stdout.read().decode("utf-8")
            if message:
                return {"status": True, "message": message}
            else:
                return {"status": False, "message": "******* No Content in The Period Time ******"}

    # exectute tail -f file and recode the start line of tail
    def _tailFile(self, filename):
        _, _, stdout, stderr = self._execute("wc -l %s | awk '{print $1}'" % filename )
        print("after wc line")
        err_message = stderr.readline()
        if err_message:
            print(err_message)
            return {"status": False, "err_message": err_message}
        line_end = int(stdout.readline().strip())
        if line_end <= TAILLINE:
            tail_line = "+1"
            self.line_start = 1
        else:
            self.line_start =  line_end - TAILLINE + 1
            tail_line = "+" + str(self.line_start)
        print("before tail")
        self.tail_pid, _, stdout, stderr = self._execute("tail -n %s -f %s" % (tail_line, filename ))
        print("after tail, tail_pid: %s" %self.tail_pid)
        #err_message = stderr.readline()
        #print("after read error")
        #if err_message:
        #    print(err_message)
        #    return {"status": False, "err_message": err_message}
        #else:
        print("before return")
        return {"status": True, "content": {"stdout": stdout, "stderr": stderr}}

    # a thread to get tail -f command out and write a file like object.
    def getTailResult(self, file_to_write):
        def threadExecute(stdout, file_to_write):
            line_number = self.line_start
            while True:
                #content = ""
                #for line in iter(lambda: stdout.readline(2048), ""):
                #    content = content + str(line_number) + "    " + line
                #    line_number = line_number + 1
                #    file_to_write.write(content)
                #time.sleep(1)
                line = stdout.readline()
                if line:
                    file_to_write.write(str(line_number) + "    " + line)
                    line_number += 1
                else:
                    print("End of stdout, this may caused by terminate of tail command!")
                    #file_to_write.write("********* End of stdout! this may be caused by terminate of tail command! *********")
                    self.tail_pid = ""
                    break

        result = self._tailFile(self.fullFileName)
        print("after tail file")
        if result["status"]:
            p = Thread(target=threadExecute, args=(result["content"]["stdout"], file_to_write))
            p.setDaemon(True)
            p.start()
        else:
            file_to_write.write(result["err_message"])
            self.tail_pid = ""

    # get more back content of a file after tail -f command
    def getBackMoreContent(self):
        #print("the line start: %s" % self.line_start)
        if self.line_start == 1:
            return {"status": "True", "message": "Already at the top of file\n"}
        elif self.line_start - 1 > MORELINE:
            stdin, stdout, stderr = self.linkHandler.exec_command("awk 'NR>=%d&&NR<=%d{print NR\"    \"$0}' %s" %
                                                                  (self.line_start - MORELINE,
                                                                   self.line_start - 1,
                                                                   self.fullFileName))
            err_message  = stderr.read()
            if err_message:
                print(err_message)
                return {"status": False, "message": err_message}
            else:
                self.line_start = self.line_start - MORELINE
                return {"status": True, "message": stdout.read().decode("utf-8")}
        else:
            stdin, stdout, stderr = self.linkHandler.exec_command("awk 'NR>=%d&&NR<=%d{print NR\"    \"$0}' %s"  %
                                                                  (1, self.line_start - 1, self.fullFileName))
            err_message  = stderr.read()
            if err_message:
                print(err_message)
                return {"status": False, "message": err_message}
            else:
                self.line_start =1
                return {"status": True, "message": stdout.read().decode("utf-8")}


if __name__ == '__main__':
    class FileObject():
        def __init__(self, filename):
            self.handler = open(filename, 'w')

        def write(self, content):
            self.handler.write(content)
            self.handler.flush()

        def close(self):
            self.handler.close()

    myfile = FileObject("output")

    mylog = TailLog("10.13.2.64", 22, 'zwg', '/home/zwg/log.file')
    #mylog = TailLog("172.16.100.200", 22, 'zhouwg_7', '/app/jbp_job/logs/job.log')
    if not mylog.connect():
        exit()
    mylog.getTailResult(myfile)
    #while True:
    #    try:
    #        print(mylog._q.get(block=True))
    #    except Empty:
    #        break
    #print("after cycle")
    #mylog.close()
    #mylog.close()
    time.sleep(10)
    #mylog.closeTail()
    result = mylog.getBackMoreContent()
    if result["status"]:
        print(result["message"])
    else:
        print(result["message"])
    time.sleep(60)
    mylog.closeTail()
    mylog.close()
    print("end")

