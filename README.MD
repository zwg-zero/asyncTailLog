### 功能
* 日志文件下载
* 实时显示服务器上的log输出
* 显示某个时间段的日志
* 日志显示在textarea中，scrollbar到最底时显示区域会不断更新，不在最底下时显示区域不更新，内容更新
   scrollbar拉到最顶上时会向服务器请求前一段的日志内容
### 使用主要的库
* tornado paramiko threading 
### communication between backend and frontend through websocket
* fronted send json:
    {"command": "start_tail", "app_name": "web-1", "date": "2016-08-30"}
    {"command": "more_content", "app_name": "web-1"}
    {"command": "filter_log", "app_name": "web-1", "date": "2016-09-13"
     "start_time": "03:00", "end_time": "15:34"}
* frontend received json:
    {"status": "error", "message": "tail log end"}
    {"status": "tail_content", "message": "kslkdsk\nkfsksfk\nkskdsf\n"}
    {"status": "more_log", "message", "sklfsf\njsfjslf\nsdfjdlksjf\n"}
    {"status": "filter_log", "message", "sklfsf\njsfjslf\nsdfjdlksjf\n"}
