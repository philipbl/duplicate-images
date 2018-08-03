import json
import webbrowser

from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from jinja2 import FileSystemLoader, Environment
from werkzeug.routing import PathConverter


class EverythingConverter(PathConverter):
    regex = '.*?'

app = Flask(__name__)
CORS(app)
app.url_map.converters['everything'] = EverythingConverter


def display_duplicates(duplicates, delete_cb):
    @app.route('/')
    def main_page():
        env = Environment(loader=FileSystemLoader('template'))
        template = env.get_template('index.html')
        return template.render(duplicates=json.dumps(duplicates))

    @app.route('/picture/<everything:file_name>', methods=['GET'])
    def get_picture(file_name):
        return send_file(file_name)

    @app.route('/picture/<everything:file_name>', methods=['DELETE'])
    def delete_picture(file_name):
        result = delete_cb(file_name)
        return result

    # webbrowser.open("http://localhost:5000")
    app.run()
