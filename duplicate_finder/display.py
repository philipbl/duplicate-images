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
        # Remove picture from database and file system
        result = delete_cb(file_name)

        if result:
            # TODO: Make this more efficient
            # If successful, remove from data structure
            i_to_delete = -1
            j_to_delete = -1
            for i, images in enumerate(duplicates):
                for j, image in enumerate(images['items']):
                    print(i, j, image)
                    if file_name == image['file_name']:
                        i_to_delete = i
                        j_to_delete = j
                        break

            if i_to_delete != -1:
                print("Removing item", i_to_delete, j_to_delete)
                del duplicates[i_to_delete]['items'][j_to_delete]

                # If there are no more duplicates, then remove the whole entry
                if len(duplicates[i_to_delete]['items']) == 1:
                    del duplicates[i_to_delete]

        return str(result)

    webbrowser.open("http://localhost:5000")
    app.run()
