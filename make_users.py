
"""New web signups are always farmers, so staff accounts are seeded here.
Run inside the project venv:  python make_users.py
"""
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash

import database

STAFF = [
    ("Officer Amina", "officer@ukulima.test", "Officer123!", "officer", "Nakuru"),
    ("Admin Baraka", "admin@ukulima.test", "Admin123!", "admin", "Nairobi"),
]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def main():
    database.init()
    con = database.connect()
    try:
        for name, email, pw, role, county in STAFF:
            if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                con.execute(
                    "UPDATE users SET name=?,password=?,role=?,county=? WHERE email=?",
                    (name, generate_password_hash(pw), role, county, email))
                con.commit()
                print(f"~ reset    {email} / {pw}  ({role})")
                continue
            con.execute(
                "INSERT INTO users(name,email,phone,password,role,county,created) VALUES(?,?,?,?,?,?,?)",
                (name, email, "", generate_password_hash(pw), role, county, now()))
            con.commit()
            print(f"+ created  {email} / {pw}  ({role})")
        print("\nDone. You can now log in with the officer or admin account.")
    finally:
        con.close()


if __name__ == "__main__":
    main()