import sys
from datetime import timedelta


DEBUG = False

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DB_NAME = 'grid_fs'

MONGO_DB_REPL_ON = True
MONGO_DB_REPL_URI = 'localhost:27017,localhost:27018'
MONGO_REPLICA_NAME = 'grid_fs_set'

IMAGE_FILTER_MODULE_LOCATION = '/{mode}/{w}x{h}/{id}'

try:
    from settings_local import *
except ImportError:
    pass
