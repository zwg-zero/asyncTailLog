# -*- coding: utf-8 -*-

import os
DEBUG = True
DIRNAME = os.path.dirname(__file__)
STATIC_PATH = os.path.join(DIRNAME, 'static')
TEMPLATE_PATH = os.path.join(DIRNAME, 'template')


import logging

logging.basicConfig(filename="error.log",
                    level=logging.INFO,
                    filemode ='w',
                    format='%(asctime)s - %(levelname)-8s - file:%(filename)s line:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %Hh%Mm%Ss')

#import base64
#import uuid
#base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)

COOKIE_SECRET = 'quK77bVRSEeQwa+X44YW5Kba4IQookjEkiyYbag58cY='
