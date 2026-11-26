# ElectroHub — EV community platform

Web platform for electric-vehicle owners: parts shop, peer-to-peer marketplace with real-time chat, charging-station map with booking and payments, community forum and AI-generated vehicle reports.

> Diploma project (Odesa College of Computer Technologies «Server», 2025).

**Stack:** Python · Django 5 · Django REST Framework · PostgreSQL + PostGIS · Django Channels (WebSockets) + Redis · Stripe · Tailwind CSS · Docker · Nginx · Gunicorn / Daphne

## Features

| Module | What it does |
|---|---|
| `product`, `cart`, `order` | Parts catalogue with filters, reviews, favourites; cart and checkout with **Stripe** payments |
| `marketplace` | User listings with photos and features; **real-time buyer–seller chat** over WebSockets (Channels + Redis) |
| `charge_stations` | Charging-station map (PostGIS + DRF-GIS API), data imported from **Open Charge Map** on a schedule (APScheduler), slot booking with Stripe, routes via **openrouteservice** |
| `transport` | User's vehicles and **AI-generated condition reports** (Google Gemini) exported to **PDF** (ReportLab) |
| `forum` | Questions, answers, categories, blog posts with view tracking |
| `administration` | Custom admin dashboard: users, products, orders, listings, statuses |
| `core` | Auth, profiles, newsletter, AI-written transactional emails, UAH exchange rates |

## Run with Docker

```bash
cp .env.example .env          # fill in the keys you need
docker build -t django-ecommerce:latest .
docker compose up -d
```

Open `http://localhost:${NGINX_EXTERNAL_PORT}` (8080 by default).

## Run locally

Requires PostgreSQL with PostGIS, GDAL and Redis.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set POSTGRES_HOST=127.0.0.1
python manage.py migrate
python manage.py parse_ocm_stations   # optional: import charging stations
daphne vivasonya.asgi:application
```

## Tests

```bash
pytest
```

## License

MIT
