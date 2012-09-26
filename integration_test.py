# -*- coding: utf-8 -*-
"""
Интеграционный тест: тестирует связку unistore, gridfs-serve и unistore-nginx-serve.
"""
import argparse
from urlparse import urljoin
from time import sleep

import requests


parser = argparse.ArgumentParser(prog=__file__)
parser.add_argument('unistore_url', help='unistore url')
parser.add_argument('token', help='unistore access token')
args = parser.parse_args()

unistore_url = args.unistore_url
token = args.token
headers = {'Token': token}


def upload_file(path):
    r = requests.post(unistore_url,
            files={'file': open(path, 'rb')},
            headers=headers)
    assert r.status_code == 200
    return r.json['id']


def get_serve_url(_id):
    storage_url = urljoin(unistore_url, _id)
    r = requests.get(storage_url, headers=headers)
    assert r.status_code == 200

    if 'information' in r.json: # Regular file
        return r.json['information']['uri']
    elif 'uri' in r.json: # Pending file
        return r.json['uri']


# Загружаем png
png_id = upload_file('fixtures/png.png')
png_serve_url = get_serve_url(png_id)
assert requests.get(png_serve_url).status_code == 200

# Заказываем ресайз
resize_png_url = urljoin(unistore_url, png_id) + '?action=resize&w=100&h=100&mode=keep' 
r = requests.get(resize_png_url, headers=headers)
assert r.status_code == 200
resized_png_id = r.json['id']

# Тут же просим serve url
resized_png_serve_url = get_serve_url(resized_png_id)

# Проверяем, что он будет обработан unistore-nginx-serve
assert 'uns' in resized_png_serve_url
r = requests.get(resized_png_serve_url)
assert r.status_code == 200
assert 'image/png' in r.headers['content-type']

# Даём операции время выполниться
sleep(1)
# Просим serve url заново
resized_png_serve_url = get_serve_url(resized_png_id)
# Проверяем, что он будет обработан gridfs-serve
assert 'uns' not in resized_png_serve_url
r = requests.get(resized_png_serve_url)
assert r.status_code == 200
assert 'image/png' in r.headers['content-type']


# Загружаем jpg
jpg_id = upload_file('fixtures/cat.jpg')

# Создаём zip
r = requests.post(urljoin(unistore_url, 'zip'), data={
        'file_id': [png_id, jpg_id],
        'filename': 'images.zip'
    }, headers=headers)
zip_id = r.json['id']

zip_serve_url = get_serve_url(zip_id)
# Проверяем, что он будет обработан unistore-nginx-serve 
assert 'uns' in zip_serve_url

r = requests.get(zip_serve_url, headers=headers)
assert r.status_code == 200
assert 'application/zip' in r.headers['content-type']

print 'OK!'
