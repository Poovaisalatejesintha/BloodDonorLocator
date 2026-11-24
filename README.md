# Emergency Blood Donor Locator and Availability Tracker

Full-stack Python project: Flask (backend), SQLite (database), HTML/CSS (frontend).

## Run it
1. Install Python 3.9+ and open a terminal in this folder.
2. `pip install -r requirements.txt`
3. `python app.py`
4. Open http://127.0.0.1:5000 in your browser.

## Features
- Search donors by blood group and city (blood-group compatibility included)
- Donor registration with phone + 4-digit PIN (PIN is stored hashed)
- Donor login to switch Available / Unavailable
- "I donated today" starts a 90-day rest period (change GAP_DAYS in app.py)
- One-tap Call and WhatsApp buttons

## Files
- app.py: all backend logic (routes, database, rules)
- templates/: HTML pages (Jinja2)
- static/style.css: styling
- donors.db: created automatically on first run
