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
                          "reason": "CRSID 'idontexist' is not registered"
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
                "reason": f"CRSID '{crsid}' is not registered"
                }, 201

    begin_posix = dt.datetime.strptime(begin, "%Y-%m-%dT%H:%M:%S").strftime('%s')
    total_shots, debt = db.execute(
            "SELECT sum(ncoffee), sum(debit) FROM transactions \
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
            "totals": {r[0]: r[1] for r in totals},
            "spend": debt
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
          description: > ISO 8601 time (`YYYY-MM-DDThh:mm:ss` or `YYYY-MM-DD`)
            from which to begin aggregating.
        - name: before
          in: path
          type: string
          required: false
          description: >
            ISO 8601 time (`YYYY-MM-DDThh:mm:ss` or `YYYY-MM-DD`)
            at which to stop aggregating.
        - name: include_debit
          in: path
          type: bool
          required: false
          description: >
            Flag to include the 'debit' part of the transaction
            """
    db = open_db()
    hdr = ["DATETIME(ts,'unixepoch')", "type", "crsid"]
    crsid = request.args.get('crsid')
    after = request.args.get('after')
    before = request.args.get('before')
    include_debit = request.args.get('include_debit') is not None

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

    if include_debit:
        hdr += ['debit']

    condstring = " AND ".join([x[0] for x in conds])

    q = "SELECT " + ", ".join(hdr) + " FROM transactions"
    if len(conds) > 0:
        q += " WHERE " + condstring
    q += " ORDER BY ts"
    # print(q)
    r = db.execute(q, tuple([x[1] for x in conds]))

    data = r.fetchall()
    hdr[0] = 'timestamp'

    retval = {
            "headers": hdr,
            "table": data
            };
    
    return retval;


@bp.route('/balance/<crsid>')
def get_balance(crsid):
    """
    Gets the curent balance of the specified user, returned as a 
    negative number for debt
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
                        "success": false,
                          "balance": -2100
                        }


        201:
            description: Call on a nonexistent user
            examples:
                application/json: {
                          "success": false,
                          "reason": "CRSID 'idontexist' is not registered"
                        }

    """
    db = open_db()


    r1 = db.execute(
            "SELECT count(crsid) FROM users WHERE crsid=?", (crsid,))

    found_id, = r1.fetchone()
    if found_id == 0:
        return {
                "success": False,
                "reason": f"CRSID '{crsid}' is not registered"
                }, 201

    debt, = db.execute(
            "SELECT debt FROM users WHERE crsid = ?", 
            (crsid,)).fetchone()
    expected_debt, = db.execute(
            "SELECT IFNULL(SUM(debit), 0) FROM transactions WHERE crsid = ?",
            (crsid,)).fetchone()

    if debt == expected_debt:
        return {
                "success": True,
                "debt": debt
                }
    else:
        # this is very bad, it means something has gone horribly wrong
        # automatically flag the problem and email a maintainer
        current_app.logger.error(f"Broken account: {crsid} checksums do not match, debt={debt}, sum(debit)={expected_debt}")
        return {
                "success": False,
                "reason": "Checksum inconsistent",
                "debt": debt,
                "debit_sum": expected_debt
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



@bp.route('/listusers')
def listusers():
    """
    Returns a list of all users in the system as a dict, with values showing if a non-null RFID is associated
    ---
    parameters:
    responses:
        200:
            description: successful response for an existing user
            examples:
                application/json: {
                        "success": true, 
                        "users": {
                            "abc123": true, 
                            "abc183": false, 
                            "abc103": true,
                            }

    """
    # check if user exists at all
    db = open_db()
    res = db.execute(
            "SELECT crsid, rfid is not null FROM users ORDER BY crsid")
    return {
            "success": True,
            "users": {
                k: r for k,r in res.fetchall()
                }
            }




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

        current_app.logger.info(f"Successfully added new user {crsid}")
        return render_template('newuser.html', 
                               success=f'''User {crsid} added successfully!
Tap your card on the box to associate it.'''), 201
    except sqlite3.IntegrityError as e:
        current_app.logger.warning(f"User {crsid} already exists in table")
        return render_template('newuser.html', error=f"User {crsid} already exists"), 400


@bp.route('/newpayment', methods=['POST'])
def create_payment():
    crsid = request.form.get('crsid', '').strip().lower()
    password = request.form.get('password', '')
    payment_str = request.form.get('payment', '').strip()

    
    if not password == current_app.config['PAY_PASSWORD']:
        return render_template('newpayment.html', error="Incorrect Password"), 403
    
    if not crsid:
        return render_template('newpayment.html', error="Missing CRSId in request body"), 400
    if len(crsid) > 8:
        return render_template('newpayment.html', error="CRSId must be <= 8 characters"), 400
    if not payment_str:
        return render_template('newpayment.html', error="Missing payment amount"), 400


    try:
    	payment_float = float(payment_str)
    	if payment_float <= 0:          
        	raise ValueError
    	payment = int(round(payment_float * 100))
    except ValueError:
    	return render_template('newpayment.html', error="Payment must be a positive number"), 400


    _db=open_db()

    user_exists= _db.execute("SELECT COUNT(*) FROM users WHERE crsid = ?",
			(crsid,)
		).fetchone()[0]

    if user_exists == 0:
        return render_template('newpayment.html', error=f"No user found with CRSid '{crsid}'"), 400

    ts = int(dt.datetime.utcnow().timestamp())

    try:
        _db.execute("BEGIN TRANSACTION;")

        _db.execute(
            "UPDATE users SET debt = debt - ? WHERE crsid = ?",
            (payment, crsid)
        )

        _db.execute(
            "INSERT INTO transactions (ts, crsid, rfid, type, debit, ncoffee) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, crsid, -1, 'Payment', -payment, 0)
        )

        _db.commit()
        current_app.logger.info(f"Recorded payment of {payment} pence for user {crsid}")

    except sqlite3.Error as e:
       	_db.rollback()
       	current_app.logger.error(f"Failed to record payment for {crsid}: {e}")
       	return render_template('newpayment.html', error="Database error"), 500



    total_debit = _db.execute(
        "SELECT IFNULL(SUM(debit), 0) FROM transactions WHERE crsid = ?",
        (crsid,)
    ).fetchone()[0]

    current_debt = _db.execute(
        "SELECT debt FROM users WHERE crsid = ?",
        (crsid,)
    ).fetchone()[0]

    if total_debit != current_debt:
        current_app.logger.error(f"Debt mismatch for {crsid}: total_debit={total_debit}, debt={current_debt}")
        return render_template('newpayment.html', error="Debt mismatch after update, contact db985"), 500
       
    return render_template('newpayment.html', success=f"Successfully recorded payment of {payment} pence for {crsid}"), 400


