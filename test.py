import requests, json

from main import APIKEY

name = input()


def coordinating(name):
    serv = 'https://geocode-maps.yandex.ru/1.x/'
    params = {
        'apikey': APIKEY,
        'geocode': name,
        'format': 'json'
    }
    req = requests.get(serv, params=params).json()
    object_data = req['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']
    coords = object_data["Point"]["pos"]
    coords = ', '.join(coords.split()[::-1])
    return coords


print(coordinating(name))
