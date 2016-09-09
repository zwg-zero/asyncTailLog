#!/usr/bin/python
# -*- coding: utf-8 -*-


import sys
import re
import os.path
start_time = sys.argv[1]
end_time = sys.argv[2]
filename = sys.argv[3]
basefilename = os.path.basename(filename)
mark = False
with open(filename, "r") as file_handler:
    i = 1
    printed_line_number = 0
    if basefilename.startswith("access"):
        def time_filter(line):
            return line.split(" ")[4][13:21]
    else:
        def time_filter(line):
            return line[1:9]
    for line in file_handler:
        time_stamp = time_filter(line)
        if re.match("\d\d:\d\d:\d\d", time_stamp):
            if time_stamp < start_time:
                pass
            elif time_stamp > end_time:
                break
            else:
                if printed_line_number == 5000:
                    print("*********** 5000 Lines Have Printed, I'm So Tired! ***********")
                    break
                else:
                    print("%s    %s" % (str(i),line.rstrip()))
                    printed_line_number += 1
                    mark = True
        elif mark:
            if printed_line_number == 5000:
                print("5000 lines have printed, I'm too tired!")
                break
            else:
                print("%s    %s" % (str(i),line.rstrip()))
                printed_line_number += 1
        i = i + 1
