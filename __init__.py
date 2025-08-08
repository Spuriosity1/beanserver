from flask import Flask, g, request, current_app, render_template, send_file
from flasgger import Swagger, LazyString, LazyJSONEncoder

import sqlite3
import json
import os



# The factory function
def create_app(test_config=None):

    app = Flask(__name__, instance_relative_config=True)
    app.json_encoder = LazyJSONEncoder
    app.config['SWAGGER'] = {
            'title': 'Beanbot API',
            'uiversion': 3,
            'templates': 'templates/flasgger/swagger_ui.html'
            }

    template = {
            "info": {
                "title": "Beanbot API",
                "description": "API for accessing data pertaining to TCM's coffee habits",
                "contact": {
                    "responsibleOrganization": "als217",
                    "responsibleDeveloper": "als217",
                    "email": "CRSID AT CAM DOT AC DOT UK",
                    "url": "spuriosity1.github.io",
                    },
                "termsOfService": "http://me.com/terms",
                "version": "0.0.1"
                },
            # 'swaggerUiPrefix': LazyString(  lambda : request.environ.get('HTTP_X_SCRIPT_NAME', '')),
            "basePath": "/api",  # base bash for blueprint registration
            }
    swagger = Swagger(app, template=template)


    @app.route('/helloworld', methods=['GET', 'POST'])
    def ping():
        return "Hello from TCM"

    if test_config is None:
        app.config.from_file("config.json", load=json.load)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # set up the API
    from beanserver import api
    app.register_blueprint(api.bp)

#    from beanserver import auth
#    app.register_blueprint(auth.bp)

    from beanserver.db import init_app
    init_app(app)

    @app.route('/favicon.ico')
    def faviconIt():
        return app.send_from_directory('static','favicon.ico')

    @app.route('/')
    @app.route('/index')
    def index():
        return render_template("index.html")

    @app.route('/stats')
    def stats():
        hide_navbar=False
        if 'hide_navbar' in request.args:
            hide_navbar=True
        return render_template("stats.html", hide_navbar=hide_navbar)

    @app.route('/newcrsid')
    def newcrsid():
        return render_template("newuser.html")

    @app.route('/balance')
    def balance():
        return render_template("check_balance.html")

    @app.route('/contact')
    def contact():
        return render_template("contact.html")

    @app.route('/backup')
    def send_db_copy():
        if (os.path.isfile(app.config['PRIMARYDB'])):
            return send_file(app.config['PRIMARYDB'], as_attachment=True)
        else:
            s = "database is misconfigured (this is very bad)"
            s += f"No file at {app.config['PRIMARYDB']}"
            return s, 400

    return app
