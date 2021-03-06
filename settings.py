# -*- coding: utf-8 -*-
import sys
from datetime import timedelta


DEBUG = False

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DB_NAME = 'grid_fs'

MONGO_REPLICATION_ON = True
MONGO_REPLICA_SET_URI = 'localhost:27017,localhost:27018'
MONGO_REPLICA_SET_NAME = 'grid_fs_set'

IMAGE_FILTER_MODULE_RESIZE_LOCATION = '/internal/{mode}/{w}x{h}/{id}'
IMAGE_FILTER_MODULE_ROTATE_LOCATION = '/internal/rotate/{angle}/{id}'

AVERAGE_TASK_TIME = timedelta(seconds=60 * 20)

try:
    from settings_local import *
except ImportError:
    pass
