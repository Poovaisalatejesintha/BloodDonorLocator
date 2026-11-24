import re
import sqlite3
from datetime import date, datetime, timedelta

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-sharing"  
DB_FILE = "donors.db"
GAP_DAYS = 90  

COMPATIBLE = {
    "O-":  ["O-"],
    "O+":  ["O-", "O+"],
    "A-":  ["O-", "A-"],
    "A+":  ["O-", "O+", "A-", "A+"],
    "B-":  ["O-", "B-"],
    "B+":  ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}
BLOOD_GROUPS = list(COMPATIBLE)


# ---------- Database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_FILE) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            available INTEGER NOT NULL DEFAULT 1,
            last_donated TEXT,
            created_at TEXT NOT NULL)""")


# ---------- Helper functions ----------
def next_eligible(last_donated):
    """Date when the donor can donate again (None = eligible now)."""
    if not last_donated:
        return None
    last = datetime.strptime(last_donated, "%Y-%m-%d").date()
    nxt = last + timedelta(days=GAP_DAYS)
    return nxt if nxt > date.today() else None


def whatsapp_number(phone):
    return "91" + phone if len(phone) == 10 else phone  # assumes India (+91)


# ---------- Pages ----------
@app.route("/")
def index():
    rows = get_db().execute("SELECT available, last_donated FROM donors").fetchall()
    total = len(rows)
    ready = sum(1 for r in rows if r["available"] and not next_eligible(r["last_donated"]))
    return render_template("index.html", groups=BLOOD_GROUPS, total=total, ready=ready)


@app.route("/search")
def search():
    group = request.args.get("group", "")
    city = request.args.get("city", "").strip()
    if group not in COMPATIBLE or not city:
        flash("Please choose a blood group and enter a city.", "error")
        return redirect(url_for("index"))

    allowed = COMPATIBLE[group]
    marks = ",".join("?" * len(allowed))
    rows = get_db().execute(
        f"SELECT * FROM donors WHERE available=1 AND lower(city)=lower(?) "
        f"AND blood_group IN ({marks})", [city] + allowed).fetchall()

    donors = []
    for r in rows:
        if next_eligible(r["last_donated"]):
            continue  # still resting
        donors.append({"name": r["name"], "blood_group": r["blood_group"],
                       "phone": r["phone"], "wa": whatsapp_number(r["phone"]),
                       "exact": r["blood_group"] == group})
    donors.sort(key=lambda d: not d["exact"])  # exact matches first
    return render_template("search.html", donors=donors, group=group, city=city)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        group = request.form["blood_group"]
        phone = re.sub(r"\D", "", request.form["phone"])[-10:]
        city = request.form["city"].strip().title()
        pin = request.form["pin"].strip()

        if not name or not city:
            flash("Name and city are required.", "error")
        elif group not in COMPATIBLE:
            flash("Please select a valid blood group.", "error")
        elif len(phone) != 10:
            flash("Enter a valid 10-digit phone number.", "error")
        elif not (pin.isdigit() and len(pin) == 4):
            flash("PIN must be exactly 4 digits.", "error")
        else:
            try:
                get_db().execute(
                    "INSERT INTO donors (name, blood_group, phone, city, pin_hash, created_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (name, group, phone, city, generate_password_hash(pin),
                     date.today().isoformat()))
                get_db().commit()
                flash("Thank you! You are now a registered donor. Log in to manage your status.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("This phone number is already registered.", "error")
    return render_template("register.html", groups=BLOOD_GROUPS)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = re.sub(r"\D", "", request.form["phone"])[-10:]
        pin = request.form["pin"].strip()
        donor = get_db().execute("SELECT * FROM donors WHERE phone=?", (phone,)).fetchone()
        if donor and check_password_hash(donor["pin_hash"], pin):
            session["donor_id"] = donor["id"]
            return redirect(url_for("dashboard"))
        flash("Wrong phone number or PIN.", "error")
    return render_template("login.html")


def current_donor():
    donor_id = session.get("donor_id")
    if not donor_id:
        return None
    return get_db().execute("SELECT * FROM donors WHERE id=?", (donor_id,)).fetchone()


@app.route("/dashboard")
def dashboard():
    donor = current_donor()
    if not donor:
        return redirect(url_for("login"))
    return render_template("dashboard.html", donor=donor,
                           next_date=next_eligible(donor["last_donated"]))


@app.route("/toggle", methods=["POST"])
def toggle():
    donor = current_donor()
    if not donor:
        return redirect(url_for("login"))
    get_db().execute("UPDATE donors SET available=? WHERE id=?",
                     (0 if donor["available"] else 1, donor["id"]))
    get_db().commit()
    return redirect(url_for("dashboard"))


@app.route("/donated", methods=["POST"])
def donated():
    donor = current_donor()
    if not donor:
        return redirect(url_for("login"))
    get_db().execute("UPDATE donors SET last_donated=? WHERE id=?",
                     (date.today().isoformat(), donor["id"]))
    get_db().commit()
    flash(f"Thank you for saving lives! You can donate again after {GAP_DAYS} days.", "success")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


init_db()
if __name__ == "__main__":
    app.run(debug=True)
