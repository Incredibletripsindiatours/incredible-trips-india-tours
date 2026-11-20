# Incredible Trips India Tours

A complete, editable demo website for an Indian domestic tour company, built with **Python + FastAPI + SQLite + Jinja2 + plain CSS/JavaScript**. No frontend build step, no Node installation and no external database required.

## Features

- Responsive public homepage, destination catalogue, tour filters and detail pages
- Customer enquiry form without account creation
- Customer registration/login **only when requesting a booking**
- Booking requests with preferred date and number of travellers; no payments or instant confirmations
- Private admin dashboard: tour creation/editing, prices, itinerary, featured tours, publish/unpublish, image upload, category tabs, homepage copy, contact details, enquiries and booking statuses
- Password hashing, signed HttpOnly session cookies, CSRF tokens on all state-changing forms, role checks and validated image uploads
- Demo tour packages for Rajasthan, Uttar Pradesh, Himachal Pradesh, Kashmir, Uttarakhand, Madhya Pradesh and Punjab

## Quick start on Windows

Double-click `start_windows.bat` to install dependencies and run the site. For your admin account, open Command Prompt in this folder and run `.venv\Scripts\python.exe create_admin.py` (only once).

## Run locally

Install Python 3.10+ (3.11+ recommended). Open a terminal in this folder:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
python create_admin.py
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000/**. Sign in with the admin credentials you just created and open **http://127.0.0.1:8000/admin**.

The database and uploaded images are created automatically in `data/`. Keep this folder private and back it up regularly. For a fresh demo, stop the server and remove `data/site.db` (this **deletes all customers, bookings, tours and settings**).

## Admin editing guide

- **Tour Packages**: Add/edit title, route, state, duration, indicative starting price, highlights, day-wise itinerary and cover image. Uncheck Published to hide a package. A tour with booking requests is archived instead of deleted.
- **Categories / Tabs**: Create or delete categories; assign a category while editing a tour. Categories appear in the public filters.
- **Website Content**: Edit homepage hero, tagline, about copy, owner, contact details and hero image.
- **Enquiries**: Read customer enquiries and mark New / Contacted / Closed.
- **Bookings**: Read requests and update status. Confirmed is a **manual admin status**; no payment is collected.

## Demo caveats / before public launch

1. All tour prices, itinerary details and inclusions are **illustrative** and require verification. Admin should update them before publishing.
2. Photos use externally hosted Unsplash URLs by default. Internet access is needed to display them. Upload your own licensed destination photos from admin for production reliability. Replace fixed destination-card background images in `static/css/style.css` if needed.
3. The brand illustration is an original inline SVG, not a registered trademark. Confirm branding and business details with the owner.
4. No real-time inventory, payment gateway, transactional emails, SMS or WhatsApp API is connected. Customer enquiries and booking requests are stored in the admin panel; the team must follow up manually.
5. Before going live: deploy behind HTTPS, set `COOKIE_SECURE=1`, use a persistent `SECRET_KEY`, enable regular backups, add privacy/terms/refund policies, verify business and tax details, implement rate limiting and spam protection, and consider email notifications. For high traffic, migrate SQLite to a managed database.
6. Only an admin created with `create_admin.py` can access admin features. Public registration always creates a customer account.
7. Admin can edit **site content and packages**, not arbitrary source-code/layout. To change navigation structure, typography, logo or page templates, edit the repository.

## Structure

```
app.py                 Routes, database, authentication and admin logic
create_admin.py        Admin account creation / password reset
requirements.txt       Python dependencies
templates/             Public and admin HTML templates
static/css/style.css   All styling
static/js/site.js      Mobile menu and date helper
tests/                 Automated smoke/integration tests
data/                  Runtime database, images, session secret (auto-created)
```

## Tests

```bash
python -m unittest discover -s tests -v
```

For test client integration checks, `httpx` is required (`pip install httpx`).
