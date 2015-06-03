# -*- coding: utf-8 -*-
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
    return r.json()['resource_uri']


def get_serve_url(_id):
    storage_url = urljoin(unistore_url, _id)
    r = requests.get(storage_url, headers=headers)
    assert r.status_code == 200
    return r.json()['data']['url']


# Загружаем png
png_uri = upload_file('fixtures/png.png')
png_serve_url = get_serve_url(png_uri)
assert requests.get(png_serve_url).status_code == 200

# Заказываем оптимизацию
optimize_png_url = urljoin(unistore_url, png_uri) + '?action=optimize'
r = requests.get(optimize_png_url, headers=headers)
assert r.status_code == 200
optimized_png_uri = r.json()['resource_uri']

# Тут же просим serve url
optimized_png_serve_url = get_serve_url(optimized_png_uri)

# Проверяем, что он будет обработан unistore-nginx-serve
assert 'uns' in optimized_png_serve_url

r = requests.get(optimized_png_serve_url)
assert r.status_code == 200
assert 'image/png' in r.headers['content-type']

# Даём операции время выполниться
sleep(10)
# Просим serve url заново

optimized_png_serve_url = get_serve_url(optimized_png_uri)


# Проверяем, что он будет обработан gridfs-serve
assert 'uns' not in optimized_png_serve_url

r = requests.get(optimized_png_serve_url)
assert r.status_code == 200
assert 'image/png' in r.headers['content-type']
