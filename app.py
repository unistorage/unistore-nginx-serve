# -*- coding: utf-8 -*-
import gridfs
from bson.objectid import ObjectId
from pymongo import Connection, ReplicaSetConnection
from flask import Flask, Response, g, abort

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


def try_serve_zip_collection(_id):
    """Возвращает ответ для mod_zip (заголовок X-Archive-Files и список файлов в формате,
    указанном mod_zip) либо None в случае, если ZipCollection с заданным `_id` не существует.
    """
    zip_collection_data = g.db.zip_collections.find_one(_id)
    if not zip_collection_data:
        return None
    
    headers = {
        'X-Archive-Files': 'zip',
        'Content-Disposition': 'attachment; filename=%s' % zip_collection_data['filename']
    }
    
    rows = []
    for file_id in zip_collection_data['file_ids']:
        file_data = g.db.fs.files.find_one(file_id)
        
        crc32 = '%08x' % file_data['crc32']
        length = file_data['length']
        path = '/%s' % file_data['_id']
        filename = file_data['filename']

        # Критично: в конце _каждой_ строки должен быть перевод каретки и строки!
        row = '%s %s %s %s\r\n' % (crc32, length, path, filename)
        rows.append(row)

    response_data = ''.join(rows)
    return Response(response_data, headers=headers)


def try_serve_resized_image(_id):
    """Если файл с заданным `_id` -- картинка, для которой заказана операция resize с параметром
    mode равным keep или crop, возвращает X-Accel-Redirect на internal location в nginx, где
    картинка ресайзится на лету с помощью http_image_filter_module.
    """
    file_data = g.db.fs.files.find_one(_id)
    if not file_data or not file_data['pending']:
        return None

    original_content_type = file_data['original_content_type']
    actions = file_data['actions']

    supported_types = ('image/gif', 'image/png', 'image/jpeg')
    if not original_content_type in supported_types or len(actions) > 1:
        return None

    action_name, action_args = actions[0]
    if action_name == 'resize':
        mode, w, h = action_args
        if mode not in ('keep', 'crop'):
            return None
        if mode == 'keep':
            mode = 'resize'

        nginx_filter_args = {
            'id': file_data['original'],
            'mode': mode,
            'w': w or '-',
            'h': h or '-',
        }
        internal_location = settings.IMAGE_FILTER_MODULE_RESIZE_LOCATION.format(**nginx_filter_args)
    elif action_name == 'rotate':
        angle = action_args[0]
        nginx_filter_args = {
            'id': file_data['original'],
            'angle': angle
        }
        internal_location = settings.IMAGE_FILTER_MODULE_ROTATE_LOCATION.format(**nginx_filter_args)
    else:
        return None

    headers = {'X-Accel-Redirect': internal_location}
    return Response(headers=headers)


@app.route('/uns/<string:_id>/')
def get_file_info(_id=None):
    # TODO Как сделать так, чтобы указывать префикс /uns только в nginx.conf?
    _id = ObjectId(_id)
    response = try_serve_zip_collection(_id) or \
               try_serve_resized_image(_id)

    if not response:
        abort(404)
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=settings.DEBUG)
