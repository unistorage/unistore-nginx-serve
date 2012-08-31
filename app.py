from bson.objectid import ObjectId

import gridfs
from pymongo import Connection, ReplicaSetConnection
from flask import Flask, Response, request, g, jsonify, abort

import settings


app = Flask(__name__)

if settings.DEBUG:
    app.config['PROPAGATE_EXCEPTIONS'] = True


def get_mongodb_connection():
    if settings.MONGO_DB_REPL_ON:
        return ReplicaSetConnection(settings.MONGO_DB_REPL_URI,
                    replicaset=settings.MONGO_REPLICA_NAME)
    else:
        return Connection(settings.MONGO_HOST, settings.MONGO_PORT)


@app.before_request
def before_request():
    g.connection = get_mongodb_connection()
    g.db = g.connection[settings.MONGO_DB_NAME]
    g.fs = gridfs.GridFS(g.db)


@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'connection'):
        g.connection.close()


@app.route('/uns/<string:_id>/')
def get_file_info(_id=None):
    _id = ObjectId(_id)
    file_data = g.db.fs.files.find_one(_id)
    if not file_data or not file_data.get('pending', False):
        abort(404)

    action = file_data['action']
    if action['name'] != 'resize':
        abort(404)
    mode, width, height = action['args']
    # `http_image_filter_module` supports only `keep` and `crop` modes.
    if mode not in ('keep', 'crop'):
        abort(404)

    # Our `keep` mode called `resize` in `http_image_filter_module`.
    if mode == 'keep':
        mode = 'resize'
    nginx_filter_args = {
        'id': file_data['original'],
        'mode': mode,
        'w': width or '-',
        'h': height or '-',
    }
    internal_location = settings.IMAGE_FILTER_MODULE_LOCATION.format(**nginx_filter_args)
    headers = {'X-Accel-Redirect': internal_location}
    return Response(headers=headers, status=200)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=settings.DEBUG)
