
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timezone
import sqlite3
from threading import Lock
import os

DATABASE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "..", "invites.db"))
EVENT_ID = "WED-1447-03-20"
NAMES_HEADER = "محمد - ريم"
BLESSING = "اللهم بارك لهما و بارك عليهما و اجمع بينهما في خير"

app = Flask(__name__, template_folder="templates", static_folder="static")
lock = Lock()

def get_db():
    return sqlite3.connect(DATABASE, timeout=10, isolation_level=None)

@app.route("/")
def index():
    return render_template("index.html", names=NAMES_HEADER, event_id=EVENT_ID)

@app.route("/manual", methods=["GET", "POST"])
def manual():
    if request.method == "POST":
        token = request.form.get("token", "").strip()
        if token:
            return redirect(url_for("redeem", token=token))
    return render_template("manual.html", event_id=EVENT_ID)

@app.route("/invite/<token>")
def redeem(token):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    gate = request.args.get("gate", "main")

    with lock:
        conn = get_db()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT token, status, used_at, expires_at FROM invites WHERE token = ?", (token,)).fetchone()
            if row is None:
                conn.rollback()
                return render_template("used.html", reason="رمز غير معروف"), 404

            token_db, status, used_at_val, expires_at = row
            if expires_at and expires_at < now:
                conn.rollback()
                return render_template("used.html", reason="انتهت الصلاحية"), 410

            if status == "used":
                conn.rollback()
                return render_template("used.html", reason=f"تم استخدامه سابقًا عند {used_at_val}"), 409

            c.execute("UPDATE invites SET status = 'used', used_at = ?, used_by = ? WHERE token = ?", (now, gate, token))
            conn.commit()
        finally:
            conn.close()

    return render_template("ok.html", names=NAMES_HEADER, event_id=EVENT_ID, used_at=now, blessing=BLESSING)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
