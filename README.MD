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
