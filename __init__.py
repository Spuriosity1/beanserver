from flask import Flask, g, request, current_app, render_template
import json
import os
# app = Flask(__name__)


# The factory function
def create_app(test_config=None):

    app = Flask(__name__, instance_relative_config=True)

    @app.route('/ping', methods=['GET', 'POST'])
    def ping():
        return "Pong!"

    # Defaults to be overridden
#    app.config.from_mapping(
#            PRIMARYDB=os.path.join(app.instance_path, 'testDB1.sqlite'),
#            SECONDARYDB=os.path.join(app.instance_path, 'testDB2.sqlite')
#            )

    if test_config is None:
        app.config.from_file("config.json", load=json.load)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from beanbot import api
    app.register_blueprint(api.bp)

#    from beanbot import auth
#    app.register_blueprint(auth.bp)

    from beanbot.db import init_app
    init_app(app)

    @app.route('/favicon.ico')
    def faviconIt():
        return app.serve_static('favicon.ico')

    @app.route('/')
    @app.route('/index')
    def index():
        return render_template("index.html")

    @app.route('/stats')
    def stats():
        return render_template("stats.html")

    @app.route('/docs')
    def docs():
        return render_template("docs.html")

    @app.route('/contact')
    def contact():
        return render_template("contact.html")

#    @bp.route('/newuser/<crsid>', methods=['POST'])
#    @auth.login_required
#    def create_user(crsid):
#        if len(crsid) > 8:
#            return {"reason": "crsid must be <= 8 characters"}, 400
#        if 'debt' not in request.args:
#            return {"reason": "Malformed query: debt is mandartory"}, 400
#        debt = request.args['debt']

#        db.open_db()
#        try:
#            res = {
#                "added_user": True,
#                "added_init_transactions": False
#                }
#            g.db.execute(
#                    "INSERT INTO users (crsid, debt) VALUES (?, ?)",
#                (crsid, debt))
#            if debt != 0:
#                g.db.execute(
#                        "INSERT INTO transactions (ts, crsid, debit, type, ncoffee) VALUES (datetime('now'), ?, ?, 'prevbalance', 0)",
#                        (crsid, debt))
#                res["added_init_transactions"] = True
#            g.db.commit()
#            return res
#        except sqlite3.IntegrityError as e:
#            return {"reason": f"User {crsid} already exists"}, 400
#        # this is a really, really bad idea...

    return app

