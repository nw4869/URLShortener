from functools import wraps

from flask import Flask, render_template, redirect, url_for
from flask_restful import Resource, Api, abort, reqparse
import json

from uuid import uuid4


class MyCustomEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


class MyConfig(object):
    RESTFUL_JSON = {
        'cls': MyCustomEncoder
    }

    @staticmethod
    def init_app(app):
        app.config['RESTFUL_JSON']['cls'] = app.json_encoder = MyCustomEncoder


app = Flask(__name__)
app.config.from_object(MyConfig)
MyConfig.init_app(app)

api = Api(app)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'


class ShortenedUrl:
    def __init__(self, id, url):
        self.id = id
        self.url = url


class UrlShortener:
    def __init__(self):
        self.shortenedUrls = {
            'nw': ShortenedUrl('nw', 'https://nightwind.me'),
        }
        self.tokens = [
            'nw4869',
        ]

    def get(self, id):
        return self.shortenedUrls.get(id)

    def all(self):
        return self.shortenedUrls

    def id_available(self, id):
        return id not in self.shortenedUrls

    def put(self, id, url):
        shortened_url = ShortenedUrl(id, url)
        self.shortenedUrls[id] = shortened_url
        return shortened_url

    def delete(self, id):
        del self.shortenedUrls[id]

    def verify_token(self, token):
        return token in self.tokens


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        parser = reqparse.RequestParser()
        parser.add_argument('token', required=True)
        args = parser.parse_args()

        if not url_shortener.verify_token(args.token):
            abort(401)
        return func(*args, **kwargs)

    return wrapper


class ShortenedUrlResource(Resource):
    def get(self, id):
        shortened_url = url_shortener.get(id)
        if shortened_url is None:
            abort(404)
        return shortened_url, 200

    @authenticate
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('url', help='url')
        parser.add_argument('token', required=True)
        args = parser.parse_args()
        url = args.url

        url_shortener.put(id, url)
        return ShortenedUrl(id, url), 201

    @authenticate
    def delete(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('token', required=True)
        args = parser.parse_args()

        if url_shortener.get(id) is None:
            abort(404)

        url_shortener.delete(id)
        return '', 204


class ShortenedUrlsResource(Resource):
    def get(self):
        return url_shortener.all(), 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', help='id')
        parser.add_argument('url', help='url')
        args = parser.parse_args()
        url = args.url

        id = args.id
        if id is not None and not url_shortener.id_available(id):
            abort(400, message='\'%s\' is not available.' % id)

        if id is None:
            while True:
                id = uuid4().hex[:4]
                if url_shortener.id_available(id):
                    break

        url_shortener.put(id, url)
        return ShortenedUrl(id, url), 201

url_shortener = UrlShortener()
api.add_resource(ShortenedUrlResource, '/api/v1/shortened_urls/<string:id>')
api.add_resource(ShortenedUrlsResource, '/api/v1/shortened_urls')


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')


@app.route('/<id>')
def shortened_url_redirect(id):
    url = url_shortener.get(id)
    if url is None:
        abort(404)
    return redirect(url.url)


if __name__ == '__main__':
    app.run(debug=True)
