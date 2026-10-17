"""Ukulima — Step 6: outbreak map + knowledge library + JSON APIs."""
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   render_template_string, request, send_from_directory,
                   session, url_for)
from werkzeug.datastructures import MultiDict
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import ai
import database
import i18n

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, "uploads")
ALLOWED = {"png", "jpg", "jpeg", "webp"}
ALERT_THRESHOLD = 3       # reports of same pest in one county ...
ALERT_WINDOW_DAYS = 14    # ... within this many days raise an alert

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
os.makedirs(UPLOAD_DIR, exist_ok=True)

with open(os.path.join(BASE, "data", "counties.json"), encoding="utf-8") as f:
    COUNTIES = json.load(f)


# ---------- database ----------
def db():
    if "db" not in g:
        g.db = database.connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


database.init()


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


# ---------- language ----------
def current_lang():
    lang = session.get("lang", i18n.DEFAULT_LANG)
    return lang if lang in i18n.LANGS else i18n.DEFAULT_LANG


# ---------- security ----------
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf") or request.headers.get("X-CSRF")
        if not sent or sent != session.get("csrf"):
            abort(400, "Invalid or missing CSRF token. Go back, refresh the page and try again.")


def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    return db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = current_user()
            if not u:
                flash("Please log in to continue.", "info")
                return redirect(url_for("login", next=request.path))
            if roles and u["role"] not in roles:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


@app.context_processor
def inject():
    lang = current_lang()
    return dict(user=current_user(), csrf_token=csrf_token, kb=ai.KB_BY_ID,
                counties=sorted(COUNTIES), lang=lang, langs=i18n.LANGS,
                t=i18n.translator(lang))


@app.template_filter("pest")
def pest_name(label):
    if not label:
        return "Not yet identified"
    return ai.KB_BY_ID[label]["name"] if label in ai.KB_BY_ID else "Unknown / needs expert"


# ---------- alerts (early-warning engine) ----------
def final_label(r):
    return r["officer_label"] or r["ai_label"]


def check_outbreak(county, label):
    """Raise an automatic alert when enough reports of one pest appear in a county."""
    if not label or label == "unknown":
        return
    since = (datetime.now(timezone.utc) - timedelta(days=ALERT_WINDOW_DAYS)).strftime("%Y-%m-%d %H:%M")
    rows = db().execute(
        "SELECT officer_label, ai_label FROM reports WHERE county=? AND created>=? AND status!='rejected'",
        (county, since)).fetchall()
    n = sum(1 for r in rows if (r["officer_label"] or r["ai_label"]) == label)
    if n < ALERT_THRESHOLD:
        return
    recent = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    if db().execute("SELECT 1 FROM alerts WHERE county=? AND pest=? AND auto=1 AND created>=?",
                    (county, label, recent)).fetchone():
        return
    name = ai.KB_BY_ID[label]["name"]
    msg = (f"{n} reports of {name} in {county} County in the last {ALERT_WINDOW_DAYS} days. "
           f"Farmers nearby should scout their fields now. Open the pest library for control advice.")
    db().execute("INSERT INTO alerts(county,pest,message,level,auto,created) VALUES(?,?,?,?,1,?)",
                 (county, label, msg, "warning", now()))
    db().commit()


# ---------- public pages ----------
@app.route("/")
def index():
    d = db()
    stats = dict(
        reports=d.execute("SELECT COUNT(*) c FROM reports").fetchone()["c"],
        verified=d.execute("SELECT COUNT(*) c FROM reports WHERE status!='pending'").fetchone()["c"],
        counties=d.execute("SELECT COUNT(DISTINCT county) c FROM reports").fetchone()["c"])
    alerts = d.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 3").fetchall()
    top = d.execute(
        """SELECT COALESCE(officer_label, ai_label) l, COUNT(*) n FROM reports
           WHERE COALESCE(officer_label, ai_label) IS NOT NULL
             AND COALESCE(officer_label, ai_label)!='unknown'
           GROUP BY l ORDER BY n DESC LIMIT 4""").fetchall()
    top_pests = [{"name": pest_name(r["l"]), "n": r["n"]} for r in top]
    return render_template("index.html", stats=stats, alerts=alerts, top_pests=top_pests)


@app.route("/knowledge")
def knowledge():
    crop = request.args.get("crop", "")
    items = [k for k in ai.KB if not crop or crop in k["crops"]]
    return render_template("knowledge.html", items=items, crop=crop, crops=ai.CROPS)


@app.route("/knowledge/<kid>")
def knowledge_item(kid):
    if kid not in ai.KB_BY_ID:
        abort(404)
    return render_template("knowledge_item.html", k=ai.KB_BY_ID[kid])


@app.route("/uploads/<path:name>")
def uploads(name):
    return send_from_directory(UPLOAD_DIR, name)


@app.route("/lang/<code>")
def set_lang(code):
    if code in i18n.LANGS:
        session["lang"] = code
    return redirect(request.referrer or url_for("index"))


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(os.path.join(BASE, "static"), "manifest.webmanifest",
                               mimetype="application/manifest+json")


@app.route("/alerts")
def alerts():
    u = current_user()
    rows = db().execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100").fetchall()
    return render_template("alerts.html", rows=rows, mine=(u["county"] if u else None))


@app.route("/alerts/new", methods=["POST"])
@login_required("officer", "admin")
def alert_new():
    county, msg = request.form.get("county", ""), request.form.get("message", "").strip()[:500]
    level = request.form.get("level") if request.form.get("level") in ("info", "warning", "danger") else "warning"
    if (county not in COUNTIES and county != "All counties") or not msg:
        flash("Choose an area and write a message.", "error")
    else:
        pest = request.form.get("pest") if request.form.get("pest") in ai.KB_BY_ID else None
        db().execute("INSERT INTO alerts(county,pest,message,level,created_by,auto,created) VALUES(?,?,?,?,?,0,?)",
                     (county, pest, msg, level, session["uid"], now()))
        db().commit()
        flash("Alert published.", "success")
    return redirect(url_for("alerts"))


# ---------- auth ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        email = f.get("email", "").strip().lower()
        pw = f.get("password", "")
        if not name or "@" not in email or len(pw) < 8:
            flash("Enter your name, a valid email and a password of at least 8 characters.", "error")
        elif db().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            flash("That email is already registered. Try logging in.", "error")
        else:
            db().execute(
                "INSERT INTO users(name,email,phone,password,role,county,created) VALUES(?,?,?,?,?,?,?)",
                (name, email, f.get("phone", "").strip(), generate_password_hash(pw), "farmer",
                 f.get("county") if f.get("county") in COUNTIES else None, now()))
            db().commit()
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        u = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if u and check_password_hash(u["password"], pw):
            session.clear()
            session["uid"] = u["id"]
            session["csrf"] = secrets.token_hex(16)
            nxt = request.args.get("next", "")
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = url_for("dashboard")
            return redirect(nxt)
        flash("Wrong email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required()
def dashboard():
    u = current_user()
    if u["role"] == "officer":
        return redirect(url_for("officer"))
    if u["role"] == "admin":
        return redirect(url_for("admin"))
    return redirect(url_for("my_reports"))


# ---------- farmer: reports ----------
@app.route("/report/new", methods=["GET", "POST"])
@login_required()
def report_new():
    u = current_user()
    if request.method == "POST":
        f = request.form
        crop, county = f.get("crop", ""), f.get("county", "")
        if crop not in ai.CROPS or county not in COUNTIES:
            flash("Please choose a crop and a county.", "error")
            return render_template("report_new.html", tags=ai.SYMPTOM_TAGS, crops=ai.CROPS, form=f)
        tags = [t for t in f.getlist("tags") if t in ai.SYMPTOM_TAGS]
        text = f.get("symptoms", "").strip()[:1000]
        photo = None
        file = request.files.get("photo")
        if file and file.filename:
            ext = secure_filename(file.filename).rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED:
                flash("Photo must be a PNG, JPG or WEBP image.", "error")
                return render_template("report_new.html", tags=ai.SYMPTOM_TAGS, crops=ai.CROPS, form=f)
            photo = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_DIR, photo))
        try:
            lat, lng = float(f.get("lat")), float(f.get("lng"))
            assert -5 <= lat <= 6 and 33 <= lng <= 43
        except (TypeError, ValueError, AssertionError):
            clat, clng = COUNTIES[county]   # fall back to county centre with small jitter
            lat, lng = clat + secrets.randbelow(200) / 1000 - 0.1, clng + secrets.randbelow(200) / 1000 - 0.1
        result = ai.diagnose(crop, tags, text, os.path.join(UPLOAD_DIR, photo) if photo else None)
        severity = f.get("severity") if f.get("severity") in ("low", "medium", "high") else "medium"
        escalated = int(result["confidence"] < 0.5 or severity == "high" or result["label"] == "unknown")
        cur = db().execute(
            """INSERT INTO reports(user_id,crop,county,lat,lng,growth_stage,symptoms,tags,photo,ai_label,ai_conf,
               ai_source,alternatives,severity,status,escalated,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (u["id"], crop, county, lat, lng, f.get("growth_stage", "")[:40], text, json.dumps(tags), photo,
             result["label"], result["confidence"], result["source"], json.dumps(result["alternatives"]),
             severity, "pending", escalated, now()))
        db().commit()
        check_outbreak(county, result["label"])
        return redirect(url_for("report_view", rid=cur.lastrowid))
    return render_template("report_new.html", tags=ai.SYMPTOM_TAGS, crops=ai.CROPS, form=MultiDict())


def get_report(rid):
    r = db().execute("""SELECT r.*, u.name farmer_name, u.phone farmer_phone FROM reports r
                        JOIN users u ON u.id=r.user_id WHERE r.id=?""", (rid,)).fetchone()
    if not r:
        abort(404)
    return r


@app.route("/report/<int:rid>")
@login_required()
def report_view(rid):
    u, r = current_user(), get_report(rid)
    if u["role"] == "farmer" and r["user_id"] != u["id"]:
        abort(403)
    label = final_label(r)
    return render_template("report_view.html", r=r, label=label, k=ai.KB_BY_ID.get(label),
                           tags=json.loads(r["tags"] or "[]"), alts=json.loads(r["alternatives"] or "[]"))


@app.route("/reports")
@login_required()
def my_reports():
    rows = db().execute("SELECT * FROM reports WHERE user_id=? ORDER BY id DESC", (session["uid"],)).fetchall()
    return render_template("my_reports.html", rows=rows)


# ---------- officer: review ----------
@app.route("/officer")
@login_required("officer", "admin")
def officer():
    f = request.args.get("filter", "pending")
    q = "SELECT r.*, u.name farmer_name FROM reports r JOIN users u ON u.id=r.user_id"
    if f == "pending":
        q += " WHERE r.status='pending' ORDER BY r.escalated DESC, r.id DESC"
    elif f == "done":
        q += " WHERE r.status!='pending' ORDER BY r.id DESC"
    else:
        q += " ORDER BY r.id DESC"
    return render_template("officer.html", rows=db().execute(q).fetchall(), filter=f)


@app.route("/officer/review/<int:rid>", methods=["POST"])
@login_required("officer", "admin")
def review(rid):
    r = get_report(rid)
    label = request.form.get("label")
    if label not in ai.KB_BY_ID and label != "unknown":
        abort(400)
    status = "verified" if label == r["ai_label"] else "corrected"
    db().execute("UPDATE reports SET officer_id=?, officer_label=?, officer_notes=?, status=?, reviewed=? WHERE id=?",
                 (session["uid"], label, request.form.get("notes", "").strip()[:1000], status, now(), rid))
    db().commit()
    check_outbreak(r["county"], label)
    flash("Review saved. The farmer can now see your decision.", "success")
    return redirect(url_for("officer"))


# ---------- map + JSON APIs ----------
@app.route("/map")
def outbreak_map():
    return render_template("map.html", crops=ai.CROPS)


@app.route("/api/reports")
def api_reports():
    try:
        days = int(request.args.get("days", 60))
    except ValueError:
        days = 60
    days = max(1, min(365, days))
    crop = request.args.get("crop", "")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    rows = db().execute("SELECT * FROM reports WHERE created>=? AND status!='rejected'", (since,)).fetchall()
    out = []
    for r in rows:
        if crop and r["crop"] != crop:
            continue
        lbl = final_label(r)
        out.append(dict(id=r["id"], lat=round(r["lat"], 2), lng=round(r["lng"], 2),  # rounded to protect farm
                        crop=r["crop"], county=r["county"], pest=pest_name(lbl), severity=r["severity"],
                        status=r["status"], date=r["created"][:10]))
    return jsonify(out)


@app.route("/api/heatmap")
def api_heatmap():
    """County-level report counts for the choropleth layer."""
    rows = db().execute(
        """SELECT county, COUNT(*) n,
                  SUM(CASE WHEN severity='high' THEN 1 ELSE 0 END) high
           FROM reports WHERE status!='rejected' GROUP BY county""").fetchall()
    return jsonify([{"county": r["county"], "n": r["n"], "high": r["high"]} for r in rows])


@app.route("/api/trend")
def api_trend():
    """Daily report counts over the last N days for the trend chart."""
    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        days = 30
    days = max(7, min(120, days))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    rows = db().execute(
        "SELECT substr(created,1,10) d, COUNT(*) n FROM reports WHERE created>=? GROUP BY d ORDER BY d",
        (since,)).fetchall()
    return jsonify([{"date": r["d"], "n": r["n"]} for r in rows])



_PLACEHOLDER = """<!doctype html><meta charset="utf-8">
<title>Coming soon · Ukulima</title>
<body style="font-family:system-ui;background:#f6efe1;color:#143d2b;padding:60px;text-align:center">
<h1>Coming in a later step</h1>
<p>The <b>{{ name }}</b> page is built in a later step.</p>
<p><a href="{{ url_for('index') }}">&larr; Back to the landing page</a></p>
</body>"""


def soon(name):
    return render_template_string(_PLACEHOLDER, name=name)


@app.route("/admin")
@login_required("admin")
def admin():
    return soon("Admin")


@app.route("/assistant")
@login_required()
def assistant():
    return soon("Ask Ukulima")


# ---------- errors ----------
@app.errorhandler(400)
def e400(e):
    return render_template("error.html", code=400, msg=getattr(e, "description", "Bad request")), 400


@app.errorhandler(403)
def e403(e):
    return render_template("error.html", code=403, msg="You do not have permission to open this page."), 403


@app.errorhandler(404)
def e404(e):
    return render_template("error.html", code=404, msg="Page not found."), 404


@app.errorhandler(500)
def e500(e):
    return render_template("error.html", code=500, msg="Something went wrong on our side."), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))