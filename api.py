from flask import Blueprint, g, request, render_template
from datetime import datetime as dt

from beanbot.db import open_db

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

@bp.route('/leaderboard',
           defaults={'begin': '2023-01-01T00-00-00'})
@bp.route('/leaderboard/<begin>')
def get_leaderboard(begin):
    db = open_db()
    begin_posix = dt.strptime(begin, "%Y-%m-%dT%H-%M-%S").strftime('%s')
    total_shots = db.execute(
            "SELECT sum(ncoffee), crsid FROM transactions \
                    WHERE ts > ? \
                    GROUP BY crsid \
                    ORDER BY -sum(ncoffee)", (begin_posix,)).fetchall()
    return [{"crsid": r[1], "shots": r[0]} for r in total_shots]



@bp.route('/userstats/<crsid>', defaults={'begin': '2023-01-01T00-00-00'})
@bp.route('/userstats/<crsid>/<begin>')
def user_stats(crsid, begin):
    db = open_db()
    begin_posix = dt.strptime(begin, "%Y-%m-%dT%H-%M-%S").strftime('%s')
    total_shots = db.execute(
            "SELECT sum(ncoffee) FROM transactions \
                    WHERE crsid=? AND ts > ?",
            (crsid, begin_posix)).fetchone()
    totals = g.db.execute(
            "SELECT type,count(ts) FROM transactions \
                    WHERE crsid=? AND ts > ? GROUP BY type",
            (crsid, begin_posix)).fetchall()
    return {
            "total_shots": total_shots,
            "totals": {r[0]: r[1] for r in totals}
            }

@bp.route('/timeseries')
def get_timeseries():
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
        after = dt.strptime(after, "%Y-%m-%dT%H-%M-%S").strftime('%s')
        conds += [('ts >= ?', after)]

    if before is not None:
        before = dt.strptime(before, "%Y-%m-%dT%H-%M-%S").strftime('%s')
        conds += [('ts <= ?', before)]

    q = "SELECT " + ", ".join(hdr) + " FROM transactions"
    if len(conds) > 0:
        q += " WHERE " + " AND ".join([x[0] for x in conds])
    print(q)
    r = g.db.execute(q, tuple([x[1] for x in conds]))

    data = r.fetchall()
    hdr[0] = 'timestamp'

    return {
            "headers": hdr,
            "table": data
            }

@bp.route('/existsuser/<crsid>')
def exists_user(crsid):
    # check if user exists at all
    db = open_db()
    r1 = db.execute(
            "SELECT count(crsid), rfid FROM users WHERE crsid=?", (crsid,))
    found_id, rfid = r1.fetchone()
    if found_id != 0:
        return {"user-exists": True, "rfid": rfid}

    return {"user-exists": False}


