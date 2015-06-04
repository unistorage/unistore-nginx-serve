# coding: utf-8
from datetime import datetime

import gridfs
from bson.objectid import ObjectId
from pymongo import Connection, ReplicaSetConnection
from flask import Flask, Response, g, abort, redirect

import settings


app = Flask(__name__)

if settings.DEBUG:
    app.config['PROPAGATE_EXCEPTIONS'] = True


def get_mongodb_connection():
    if settings.MONGO_REPLICATION_ON:
        return ReplicaSetConnection(settings.MONGO_REPLICA_SET_URI,
                                    replicaset=settings.MONGO_REPLICA_SET_NAME)
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


def get_internal_location_part(action_name, action_args):
    internal_location_part = None

    if action_name == 'resize':
        mode, w, h = action_args
        if mode not in ('keep', 'crop'):
            return None
        if mode == 'keep':
            mode = 'resize'
        internal_location_part = '{mode}_{w}x{h}'.format(mode=mode, w=w, h=h)
    elif action_name == 'rotate':
        angle = action_args[0]
        internal_location_part = 'rotate_{angle}'.format(angle=angle)

    return internal_location_part


def try_serve_resized_image(_id):
    """Если файл с заданным `_id` -- картинка, для которой заказана операция resize с параметром
    mode равным keep или crop, возвращает X-Accel-Redirect на internal location в nginx, где
    картинка ресайзится на лету с помощью http_image_filter_module.
    """
    file_data = g.db.fs.files.find_one(_id)
    if not file_data:
        return None
    if not file_data['pending']:
        if datetime.utcnow() - file_data['uploadDate'] <= settings.AVERAGE_TASK_TIME:
            return redirect('/%s' % _id)
        else:
            return None
    
    original_content_type = file_data['original_content_type']
    actions = file_data['actions']
    supported_types = ('image/gif', 'image/png', 'image/jpeg')
    if original_content_type not in supported_types:
        return None

    internal_location_parts = ['/{0}'.format(settings.INTERNAL_LOCATION)]
    for action_name, action_args in actions:
        if action_name == 'optimize':
            continue
        part = get_internal_location_part(action_name, action_args)
        if not part:
            return None
        internal_location_parts.append(part)
    internal_location_parts.append(str(file_data['original']))

    headers = {'X-Accel-Redirect': '/'.join(internal_location_parts)}
    return Response(headers=headers)


@app.route('/<string:_id>')
def get_file_info(_id=None):
    _id = ObjectId(_id)
    response = try_serve_zip_collection(_id) or try_serve_resized_image(_id)

    if not response:
        abort(404)
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=settings.DEBUG)
