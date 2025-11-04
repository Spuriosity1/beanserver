import functools
import srp
from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for)

from beanbot.db import open_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register',methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        crsid = request.form['crsid']
        passwd = request.form['password']
        db = open_db()
        error = None

        if not crsid:
            error = "Username is required. (it can be anything at all)"
        if not passwd:
            error = "You must set a password."

        if error is None:
           try:
                salt, vkey = srp.create_salted_verification_key(crsid,passwd, hash_alg=srp.SHA256)
                db.execute(
                    "UPDATE users SET crsid=?, salt=?, vkey=?, access_level=0)",
                   (crsid, salt, vkey) 
                )
                db.commit()
           except db.IntegrityError:
                error = f"User {crsid} is already registered."
           else:
                return redirect(url_for("auth.login")) 
        flash(error)
 
    return render_template('auth/register.html')

@bp.route('/startlogin',methods=('GET','POST'))
def startlogin():
    if request.method == 'POST': 
        crsid = request.form['crsid']
        passwd = request.form['password']
        challenge_A = request.form['challenge_A']
        db = open_db()
        error=None
        user = db.execute(
            'SELECT crsid, salt, vkey FROM users WHERE crsid = ?', (username,)
        ).fetchone()

        if user is None:
            error = "Username is not a web user. (This is not your crsid.)"
        if challenge_A is None:
            error = "Malformed SRP handshake"

        if error is None:
            session['verif'] = srp.Verifier(user[0], user[1], user[2], challenge_A, hash_alg=srp.SHA256)
            s, B = session['verif'].get_challenge()
            return {'s': s, 'B': B}
    # redirect...

@bp.route('/login',methods=('GET','POST'))
def login():
    if request.method == 'POST':
        crsid = request.form['crsid']
        verif_M = request.form['M']
        db = open_db()
        user = db.execute(
            'SELECT crsid, salt, vkey FROM users WHERE crsid = ?', (username,)
        ).fetchone()

        if user is None:
            error = "Username is not a web user. (This is not your crsid.)"
        if verif_M is None:
            error = "Malformed SRP handshake"
         
        if error is None:
            session['verif'].verify_session(verif_M)
            if not v.authenticated():
                error = "Incorrect password."
            else:
                session.clear()
                session['user_access_level'] = get_db().execute(
                        'SELECT access_level FROM users WHERE crsid=?', (crsid,)).fetchone()[0]

    #redirect...

        


@bp.before_app_request
def load_logged_in_user():
    access_level = session.get('user_access')
    if access_level is None:
        g.user_access_level=0
    else:
        g.user_access_level=access

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# decorator
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user_access_level==0:
            return redirect(url_for('auth.login'))
        
        return view(**kwargs)
    return wrapped_view
