# GigOS

GigOS is a production-ready MVP for independent gig-worker shift tracking. It does not connect to Uber, DoorDash, Grubhub, Instacart, Amazon Flex, or any third-party gig platform API.

> GigOS is an independent shift, mileage, break, and earnings tracker for gig workers. Not affiliated with Uber, DoorDash, Grubhub, Instacart, Amazon Flex, or any delivery platform.

## Stack

- Flutter Web mobile-first PWA frontend
- FastAPI backend
- PostgreSQL
- SQLAlchemy + Alembic
- JWT authentication with bcrypt password hashing
- Docker Compose for local development
- Railway-compatible root Dockerfile

## Repository Layout

```text
.
|-- backend
|   |-- alembic
|   |-- app
|   |   |-- routers
|   |   |-- calculations.py
|   |   |-- config.py
|   |   |-- database.py
|   |   |-- main.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   `-- security.py
|   |-- tests
|   |-- Dockerfile
|   `-- requirements.txt
|-- frontend
|   |-- lib
|   |-- web
|   `-- Dockerfile
|-- docker-compose.yml
|-- Dockerfile
|-- railway.json
`-- .env.example
```

## Local Development

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Health: http://localhost:8000/health

## Railway Deployment

1. Create a Railway project.
2. Add a Railway PostgreSQL service.
3. Deploy this repository as a Dockerfile service. Railway detects the root `Dockerfile`.
4. Set these variables on the app service:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET=<strong random secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=https://your-railway-domain.up.railway.app
SEED_DEMO_ACCOUNTS=false
```

The root Dockerfile builds Flutter Web to `build/web`, copies it into the FastAPI image, runs migrations, and serves the PWA and API from the same Railway service. The healthcheck path is `/health`.

## iPhone PWA Install

This repo is set up for the fastest iPhone path: install the Railway-hosted Flutter Web app as a Safari PWA.

1. Deploy GigOS to Railway.
2. Open the Railway app URL in Safari on the iPhone.
3. Tap the Safari share button.
4. Tap **Add to Home Screen**.
5. Launch GigOS from the new home-screen icon.

The frontend includes a web manifest, Apple mobile web app tags, theme color, and app icons. Location features require HTTPS, which Railway provides on deployed services.

## API Routes

- `POST /auth/register`
- `POST /auth/login`
- `GET /me`
- `POST /shifts/start`
- `POST /shifts`
- `PATCH /shifts/{id}/end`
- `PATCH /shifts/{id}`
- `GET /shifts`
- `GET /shifts/{id}`
- `DELETE /shifts/{id}`
- `POST /shifts/{id}/breaks/start`
- `PATCH /breaks/{id}/end`
- `GET /reports/weekly`
- `GET /export/csv`
- `GET /locations/break-zones`
- `GET /locations/activity`
- `GET /vehicles/catalog`
- `GET /vehicles`
- `GET /vehicles/active`
- `POST /vehicles`
- `PATCH /vehicles/{id}/active`
- `GET /health`

## Calculation Rules

- `total_minutes = ended_at - started_at`
- `gross_hourly = gross_earnings / hours`
- `tax_set_aside = gross_earnings * 0.20`
- `maintenance_reserve = miles * 0.15`
- `net_profit = gross_earnings - gas_cost - other_expenses - tax_set_aside - maintenance_reserve`
- `net_hourly = net_profit / hours`
- `earnings_per_mile = gross_earnings / miles`

Break companion:

- Every 80 minutes: prompt for a geo-confirmed break
- 8 hours: fatigue warning

Location intelligence:

- `GET /locations/break-zones` uses public OpenStreetMap Overpass POI data to find nearby 24-hour fuel/convenience locations and other rest stops.
- `GET /locations/activity` estimates hot zones from public restaurant, cafe, convenience, supermarket, and retail POI density.
- These are open-data estimates, not Uber, DoorDash, Grubhub, Instacart, Amazon Flex, or delivery-platform order metrics.

Vehicle profile:

- GigOS seeds a common-vehicle MPG catalog at startup.
- Drivers can add a catalog vehicle and set fuel price per gallon.
- Only one vehicle can be active per user.
- New shifts attach the active vehicle and can estimate gas cost from `miles / mpg_combined * fuel_price_per_gallon` when manual gas cost is not entered.

## Security Notes

- Passwords are hashed with bcrypt.
- Access tokens are signed JWTs with expiration.
- GigOS never stores delivery platform passwords.
- GigOS performs no scraping.
- GigOS does not use third-party gig platform APIs.

## Tests

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Flutter Web:

```bash
cd frontend
flutter pub get
flutter analyze
flutter build web --release --dart-define=API_BASE_URL=http://localhost:8000
```
