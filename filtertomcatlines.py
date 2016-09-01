#!/usr/bin/python
# -*- coding: utf-8 -*-


import sys
import re

start_time = sys.argv[1]
end_time = sys.argv[2]
filename = sys.argv[3]
mark = False
with open(filename, "r") as file_handler:
    for line in file_handler:
        time_stamp = line[1:9]
        #print(time_stamp)
        if re.match("\d\d:\d\d:\d\d", time_stamp):
            if time_stamp < start_time:
                pass
            elif time_stamp > end_time:
                break
            else:
                print(line.rstrip())
                mark = True
        elif mark:
                print(line.rstrip())
