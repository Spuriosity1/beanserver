from flask import Blueprint, g, request, render_template, current_app
#from flask_limiter import Limiter
#from flask_limiter.util import get_remote_address

import datetime as dt
from flasgger import Swagger, LazyString, LazyJSONEncoder
import re
import sqlite3

from beanserver.db import open_db

bp = Blueprint('api', __name__, url_prefix='/api')


# @bp.route('/userstats/')
# def user_all_stats():
#     db.open_db()
#     total_shots = g.db.execute(
#             "SELECT crsid, sum(ncoffee) FROM transactions GROUP BY crsid").fetchall()
#     res = {}
#     for row in total_shots:
#         res[row[0]] = {
#                 "total_shots": row[1],
#                 "totals": g.db.execute(
#             "SELECT type, count(ts) FROM transactions \
#                     WHERE crsid=? GROUP BY type",(row[0],)).fetchall()
#                 }
#     return res
# TODO: this is needlessly overcomplicated- get_leaderboard_dt should be the
# only endpoint. The user should be responsible for generating unix time.

def get_leaderboard_dt(begin_dt):
    """
    utility function returning JSON shot leaderboard since a certain date
    ---
    parameters:
        - name: begin_dt
          in: path
          type: integer
          required: true
          description: python datetime to aggregate since
    responses:
        200:
            description: successful response
            examples:
                application/json: {
                        "success": True,
                        "data": [
                            {"crsid": "aaa001", "shots": 51},
                            {"crsid": "abc001", "shots": 11},
                            {"crsid": "abc123", "shots": 0}
                            ]
                        }
    """
    db = open_db()
    total_shots = db.execute(
            "SELECT sum(ncoffee), crsid FROM transactions \
                    WHERE ts > ? \
                    GROUP BY crsid \
                    ORDER BY -sum(ncoffee)",
            (begin_dt.strftime('%s'),)
            ).fetchall()
    data = [{"crsid": r[1], "shots": r[0]} for r in total_shots]
    return {"success": True,
            "data": data}


@bp.route('/leaderboard/',
          defaults={'begin': '2023-01-01T00:00:00'})
@bp.route('/leaderboard/after/<begin>')
def get_leaderboard(begin):
    """
    Returns a tally of shots taken from <begin> to now.
    ---
    parameters:
        - name: begin
          in: path
          type: string
          required: false
          description: >
            ISO 8601 time (`YYYY-MM-DDThh:mm:ss` or `YYYY-MM-DD`)
            from which to begin aggregating. If omitted, all users' records
            are returned.
    responses:
        200:
            description: successful response
            examples:
                application/json: {
                        "success": True,
                        "data": [
                            {"crsid": "aaa001", "shots": 51},
                            {"crsid": "abc001", "shots": 11},
                            {"crsid": "abc123", "shots": 0}
                            ]
                        }

        400:
            descripton: malformed request
    """
    if 'T' not in begin:
        begin = begin + "T00:00:00"

    try:
        begin_dt = dt.datetime.strptime(begin, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return {"success": False, "reason": "Malformed request"}
    return get_leaderboard_dt(begin_dt)


@bp.route('/leaderboard/sinceday/<day>')
def get_leaderboard_day(day):
    """
    Returns a tally of shots taken since the last <day> of thw week.
    ---
    parameters:
        - name: day
          in: path
          type: integer
          required: true
          description: Day of the UNIX week, 0-6 inclusive
    responses:
        200:
            description: successful response
            examples:
                application/json: {
                        "success": True,
                        "data": [
                            {"crsid": "aaa001", "shots": 51},
                            {"crsid": "abc001", "shots": 11},
                            {"crsid": "abc123", "shots": 0}
                            ],
                        "datesince": "2024-05-06T00:11:02"
                        }
    """
    today = dt.datetime.today()
    dest = today - dt.timedelta(days=(today.weekday() - int(day) - 1) % 7 + 1)
    dest = dest.replace(hour=0, minute=0, second=1)

    payload = get_leaderboard_dt(dest)
    payload['datesince'] = dest.strftime("%Y-%m-%dT%H:%M:%S")
    return payload


@bp.route('/leaderboard/interval/<spec>')
def get_leaderboard_interval(spec):
    """
    Tallies total shots taken since some time in the past,
    with the interval specified in the format of many number-letter pairs.
    ---
    parameters:
        - name: spec
          in: path
          type: string
          required: true
          description: |
            Interval specification, in the format
            `N#M#O#`
            for integers `N,M,O` and # chosen from
            * (y)ears
            * (d)ays
            * (w)eeks
            * (h)ours
            * (m)inutes
            * (s)econds.
          examples:
            oneday:
              value: 1d5h
              summary: Since 1 day and 5 hours ago
            complex:
              value: 1w4d10y5h5m5s
              summary: >
                Since 1 week, 4 days, 10 years, 5 hours, 5 minutes 
                and 5 seconds ago

    responses:
        200:
            description: successful response
            examples:
                application/json: {
                        "success": True,
                        "data": [
                            {"crsid": "aaa001", "shots": 51},
                            {"crsid": "abc001", "shots": 11},
                            {"crsid": "abc123", "shots": 0}
                            ],
                        "datesince": "2024-05-06T00:11:02"
                        }
    """
    spec = spec.replace(' ', '').lower()
    specifiers = re.findall(r'\D+', spec)
    quantifiers = re.findall(r'\d+', spec)

    bad_retval = {"success": False, "bad_request": "malformed query"}
    if len(specifiers) != len(quantifiers):
        return bad_retval
    timespec = {}
    lmap = {
            'd': 'days',
            's': 'seconds',
            'm': 'minutes',
            'h': 'hours',
            'w': 'weeks'
            }
    lhs = []
    for s, q in zip(specifiers, quantifiers):
        lhs = lmap.get(s)
        if lhs is None:
            return bad_retval
        timespec[lhs] = int(q)

    if len(lhs) == 0:
        return bad_retval

    d = dt.timedelta(**timespec)

    tod = dt.datetime.now()
    a = tod - d

    payload = get_leaderboard_dt(a)
    payload['datesince'] = a.strftime("%Y-%m-%dT%H:%M:%S")
    return payload


@bp.route('/userstats/<crsid>',
          defaults={'begin': '2023-01-01T00:00:00'})
@bp.route('/userstats/<crsid>/after/<begin>')
def user_stats(crsid, begin):
    """
    Gets the coffee habits of a particular user.
    Note that "total_shots" is a different number to the sum of all totals -
    americano2 and cappuccino2 count as two shots each.
    ---
    parameters:
        - name: crsid
          in: path
          type: string
          required: true
          description: >
            The regisered crsid of a particular user. Note that this tag is
            user provided, so is not 100% guaranteed to be a valid crsid.
        - name: begin
          in: path
          type: datetime
          required: false
          description: >
            ISO 8601 time (`YYYY-MM-DDThh:mm:ss` or `YYYY-MM-DD`)
            from which to begin aggregating. If omitted, all users' records
            are returned.

    responses:
        200:
            description: successful response for an existing user
            examples:
                application/json: {
                          "success": true,
                          "total_shots": [
                            35
                          ],
                          "totals": {
                            "americano2": 2,
                            "cappuccino": 1,
                            "cappuccino2": 1,
                            "espresso": 20,
                            "espresso2": 4
                          }
                        }


        201:
            description: Call on a nonexistent user
            examples:
                application/json: {
                          "success": false,
                          "reason": "CRSID <idontexist> is not registered"
                        }

    """

    db = open_db()
    if 'T' not in begin:
        begin = begin + "T00:00:00"

    # check that user exists
    r1 = db.execute(
            "SELECT count(crsid) FROM users WHERE crsid=?", (crsid,))

    found_id, = r1.fetchone()
    if found_id == 0:
        return {
                "success": False,
                "reason": f"CRSID <{crsid}> is not registered"
                }, 201

    begin_posix = dt.datetime.strptime(begin, "%Y-%m-%dT%H:%M:%S").strftime('%s')
    total_shots, = db.execute(
            "SELECT sum(ncoffee) FROM transactions \
                    WHERE crsid=? AND ts > ?",
            (crsid, begin_posix)).fetchone()
    totals = db.execute(
            "SELECT type,count(ts) FROM transactions \
                    WHERE crsid=? AND ts > ? GROUP BY type",
            (crsid, begin_posix)).fetchall()

    if total_shots is None:
        total_shots = 0
    return {
            "success": True,
            "total_shots": total_shots,
            "totals": {r[0]: r[1] for r in totals}
            }


@bp.route('/timeseries')
def get_timeseries():
    """
    Returns the full time series of transactions.
    ---
    parameters:
        - name: crsid
          in: path
          type: string
          required: false
          description: >
            The regisered crsid of a particular user (if omitted, all users'
            records are returned). Note that this tag is
            user provided, so is not 100% guaranteed to be a valid crsid.
        - name: after
          in: path
          type: string
          required: false
          description: >
            ISO 8601 time (`YYYY-MM-DDThh:mm:ss` or `YYYY-MM-DD`)
            from which to begin aggregating.
        - name: before
          in: path
          type: string
          required: false
          description: >
            ISO 8601 time (`YYYY-MM-DDThh:mm:ss` or `YYYY-MM-DD`)
            at which to stop aggregating.
            """
    db = open_db()
    hdr = ["DATETIME(ts,'unixepoch')", "type", "crsid"]
    crsid = request.args.get('crsid')
    after = request.args.get('after')
    before = request.args.get('before')

    conds = []

    if crsid is not None:
        hdr.remove('crsid')
        conds += [("crsid=?", crsid)]

    if after is not None:
        after = dt.datetime.strptime(after, "%Y-%m-%dT%H:%M:%S").strftime('%s')
        conds += [('ts >= ?', after)]

    if before is not None:
        before = dt.datetime.strptime(before, "%Y-%m-%dT%H:%M:%S").strftime('%s')
        conds += [('ts <= ?', before)]

    q = "SELECT " + ", ".join(hdr) + " FROM transactions"
    if len(conds) > 0:
        q += " WHERE " + " AND ".join([x[0] for x in conds])
    r = db.execute(q, tuple([x[1] for x in conds]))

    data = r.fetchall()
    hdr[0] = 'timestamp'

    return {
            "headers": hdr,
            "table": data
            }

@bp.route('/existsuser/<crsid>')
def exists_user(crsid):
    """
    Tests if a user exists, and returns the index of their RFID card if they do.
    ---
    parameters:
        - name: crsid
          in: path
          type: string
          required: true
          description: >
            The regisered crsid of a particular user. Note that this tag is
            user provided, so is not 100% guaranteed to be a valid crsid.
    responses:
        200:
            description: successful response for an existing user
            examples:
                application/json: {
                    "rfid": 775545127858,
                    "user-exists": true
                }

        201:
            description: unsuccessful response - user does not exist
            examples:
                application/json: {
                    "user-exists": false
                        }

    """
    # check if user exists at all
    db = open_db()
    r1 = db.execute(
            "SELECT count(crsid), rfid FROM users WHERE crsid=?", (crsid,))
    found_id, rfid = r1.fetchone()
    if found_id != 0:
        return {"user-exists": True, "rfid": rfid}, 200

    return {"user-exists": False}, 201



@bp.route('/newuser', methods=['POST'])
def create_user():
    crsid = request.form.get('crsid', '').strip().lower()
    password = request.form.get('password', '')
    
    if not password == current_app.config['BOT_PASSWORD']:
        return render_template('newuser.html', error="Incorrect Password"), 403
    
    if not crsid:
        return render_template('newuser.html', error="Missing CRSId in request body"), 400
    if len(crsid) > 8:
        return render_template('newuser.html', error="CRSId must be <= 8 characters"), 400
    
    _db = open_db()
    try:
        _db.execute(
            "INSERT INTO users (crsid, debt) VALUES (?, ?)",
            (crsid, 0))
        _db.commit()
        return render_template('newuser.html', 
                               success=f'''User {crsid} added successfully!
Tap your card on the box to associate it.'''), 201
    except sqlite3.IntegrityError as e:
        return render_template('newuser.html', error=f"User {crsid} already exists"), 400


