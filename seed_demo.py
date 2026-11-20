"""Seed believable demo data so the app is explorable on first run.

Run inside the project venv:  python seed_demo.py
Safe to re-run: it skips anything that already exists.
"""
import json
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

import database

FARMERS = [
    ("Demo Farmer", "demo@ukulima.test", "Farmer123!", "Nakuru", "0700 000 001"),
    ("Grace Wanjiku", "grace@ukulima.test", "Grace123!", "Kiambu", "0700 000 002"),
]

# (email, crop, county, pest id, severity, status, days_ago, symptoms)
REPORTS = [
    ("demo@ukulima.test", "Maize", "Nakuru", "fall-armyworm", "high", "verified", 2, "Ragged holes and sawdust-like frass in the whorl"),
    ("demo@ukulima.test", "Maize", "Nakuru", "fall-armyworm", "medium", "verified", 5, "Windowing on young leaves, caterpillars in funnel"),
    ("demo@ukulima.test", "Maize", "Nakuru", "fall-armyworm", "high", "pending", 8, "Heavy leaf damage, frass visible"),
    ("demo@ukulima.test", "Potato", "Nakuru", "late-blight", "high", "corrected", 12, "Dark water-soaked patches, white mould underneath"),
    ("demo@ukulima.test", "Maize", "Nakuru", "stem-borer", "medium", "verified", 18, "Dead hearts in young plants"),
    ("grace@ukulima.test", "Tomato", "Kiambu", "tuta-absoluta", "high", "pending", 1, "Blotchy mines on leaves and holes in fruit"),
    ("grace@ukulima.test", "Kale", "Kiambu", "diamondback-moth", "medium", "verified", 4, "Small holes and windows on sukuma leaves"),
    ("grace@ukulima.test", "Kale", "Kiambu", "aphids", "low", "verified", 9, "Sticky leaves with tiny green insects"),
    ("grace@ukulima.test", "Tomato", "Kiambu", "late-blight", "medium", "pending", 15, "Brown lesions on leaves after rain"),
    ("demo@ukulima.test", "Maize", "Uasin Gishu", "mln", "high", "verified", 3, "Yellow mottling and drying from leaf edges"),
    ("demo@ukulima.test", "Maize", "Uasin Gishu", "mln", "medium", "pending", 11, "Stunted plants, small cobs"),
    ("demo@ukulima.test", "Maize", "Trans-Nzoia", "fall-armyworm", "medium", "verified", 6, "Chewed leaves and frass"),
    ("demo@ukulima.test", "Maize", "Bungoma", "stem-borer", "low", "verified", 14, "Shot holes in leaves"),
    ("grace@ukulima.test", "Coffee", "Meru", "coffee-leaf-rust", "medium", "verified", 7, "Orange powder under leaves"),
    ("grace@ukulima.test", "Coffee", "Meru", "coffee-leaf-rust", "high", "pending", 20, "Yellow spots and leaf fall"),
    ("demo@ukulima.test", "Banana", "Kisumu", "banana-xw", "high", "verified", 5, "Yellow wilting leaves, premature ripening"),
    ("demo@ukulima.test", "Cassava", "Kisumu", "cassava-mosaic", "medium", "verified", 16, "Pale mosaic patterns and distorted leaves"),
    ("grace@ukulima.test", "Beans", "Nyeri", "bean-rust", "low", "verified", 10, "Reddish pustules on bean leaves"),
    ("demo@ukulima.test", "Maize", "Narok", "fall-armyworm", "medium", "pending", 22, "Holes in leaves, caterpillars"),
    ("grace@ukulima.test", "Cabbage", "Kiambu", "aphids", "low", "verified", 26, "Curled leaves with insects clusters"),
]

ALERTS = [
    ("Nakuru", "fall-armyworm", "3 reports of Fall armyworm in Nakuru County in the last 14 days. Farmers nearby should scout their fields now. Open the pest library for control advice.", "warning", 1),
    ("Kiambu", None, "Heavy rains expected this week — conditions favour late blight on potato and tomato. Scout fields and remove infected plants early.", "info", 0),
    ("Uasin Gishu", "mln", "Maize lethal necrosis confirmed in two farms. Use certified seed and avoid moving maize residues between fields.", "danger", 0),
]


def ts(days_ago, hour=9):
    d = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return d.replace(hour=hour, minute=15).strftime("%Y-%m-%d %H:%M")


def main():
    database.init()
    con = database.connect()
    try:
        ids = {}
        for name, email, pw, county, phone in FARMERS:
            row = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if row:
                ids[email] = row["id"]
                print(f"= exists   {email}")
                continue
            cur = con.execute(
                "INSERT INTO users(name,email,phone,password,role,county,created) VALUES(?,?,?,?,?,?,?)",
                (name, email, phone, generate_password_hash(pw), "farmer", county, ts(40)))
            con.commit()
            ids[email] = cur.lastrowid
            print(f"+ created  {email} / {pw}")

        n = 0
        for email, crop, county, label, sev, status, days, symptoms in REPORTS:
            if con.execute("SELECT 1 FROM reports WHERE user_id=? AND county=? AND ai_label=? AND symptoms=?",
                           (ids[email], county, label, symptoms)).fetchone():
                continue
            con.execute(
                """INSERT INTO reports(user_id,crop,county,lat,lng,growth_stage,symptoms,tags,photo,
                   ai_label,ai_conf,ai_source,alternatives,severity,status,escalated,created)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ids[email], crop, county, 0, 0, "Vegetative", symptoms, json.dumps(["Holes in leaves"]), None,
                 label, 0.78, "symptom-matcher", json.dumps([]), sev, status,
                 1 if sev == "high" else 0, ts(days)))
            n += 1
        con.commit()
        print(f"+ reports  {n} new")

        # place pins at county centres with a little jitter (imported lazily)
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "data", "counties.json"), encoding="utf-8") as f:
            centres = json.load(f)
        rows = con.execute("SELECT id,county FROM reports WHERE lat=0 AND lng=0").fetchall()
        for i, r in enumerate(rows):
            c = centres.get(r["county"], [-0.3, 36.8])
            j = (i % 7 - 3) / 100
            con.execute("UPDATE reports SET lat=?, lng=? WHERE id=?", (c[0] + j, c[1] - j, r["id"]))
        con.commit()

        a = 0
        for county, pest, msg, level, auto in ALERTS:
            if con.execute("SELECT 1 FROM alerts WHERE county=? AND message=?", (county, msg)).fetchone():
                continue
            con.execute("INSERT INTO alerts(county,pest,message,level,auto,created) VALUES(?,?,?,?,?,?)",
                        (county, pest, msg, level, auto, ts(2, 7)))
            a += 1
        con.commit()
        print(f"+ alerts   {a} new")
        print("\nDone. Log in as demo@ukulima.test / Farmer123! to explore.")
    finally:
        con.close()


if __name__ == "__main__":
    main()