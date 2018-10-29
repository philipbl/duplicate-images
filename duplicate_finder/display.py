import json
import math
import webbrowser

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from jinja2 import FileSystemLoader, Environment
from werkzeug.routing import PathConverter


class EverythingConverter(PathConverter):
    regex = '.*?'

app = Flask(__name__)
CORS(app)
app.url_map.converters['everything'] = EverythingConverter


def display_duplicates(duplicates, delete_cb, duplicates_per_page=10):
    @app.route('/')
    def main_page():
        env = Environment(loader=FileSystemLoader('template'))
        template = env.get_template('index.html')

        current = int(request.args.get('current', 0))
        total = math.ceil(len(duplicates) / duplicates_per_page)

        # Validate current
        if current < 0:
            current = 0
        if current >= total:
            current = total - 1

        start = current * duplicates_per_page
        end = (current + 1) * duplicates_per_page

        return template.render(duplicates=duplicates[start:end],
                               current=current,
                               total=total)

    @app.route('/json', methods=['GET'])
    def get_json():
        return jsonify(duplicates)

    @app.route('/picture/<everything:file_name>', methods=['GET'])
    def get_picture(file_name):
        return send_file(file_name)

    @app.route('/picture/<everything:file_name>', methods=['DELETE'])
    def delete_picture(file_name):
        result = delete_cb(file_name)
        return str(result)

    webbrowser.open("http://localhost:5000")
    app.run()
