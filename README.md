# Ride API

A Django REST Framework API for managing rides, built for a take-home assessment.
Admin-only access, JWT auth, and a Ride list endpoint tuned to stay within a fixed
query budget on large tables (filtering, dual sorting, pagination, and a
last-24h `RideEvent` prefetch — see [Design notes](#design-notes) below).

## Requirements

- Python 3.10+
- PostgreSQL (a running server you have credentials for)

## Setup

1. **Clone and create a virtualenv**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create the database**

   ```bash
   createdb ride_api
   # or: psql -U postgres -c "CREATE DATABASE ride_api;"
   ```

3. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `DATABASE_URL` to your Postgres connection string
   (`postgres://USER:PASSWORD@HOST:PORT/ride_api`) and a real `SECRET_KEY`.
   `.env` is gitignored — never commit it.

4. **Run migrations**

   ```bash
   python manage.py migrate
   ```

5. **Create an admin user**

   The API rejects every request unless the authenticated user's `role` is
   `admin`. `createsuperuser` is wired to set that automatically:

   ```bash
   python manage.py createsuperuser
   ```

   (Prompts for email/password — there's no `username` field; see
   [Design notes](#design-notes).)

6. **Run the server**

   ```bash
   python manage.py runserver
   ```

7. **Run the tests**

   ```bash
   python manage.py test
   ```

## Using the API

All endpoints require a JWT for a user with `role=admin`.

**Log in:**

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
# -> {"access": "...", "refresh": "..."}
```

Use the access token on every request: `Authorization: Bearer <access>`.
Refresh it at `POST /api/token/refresh/` with `{"refresh": "..."}`.

**Endpoints** (all full CRUD via `ModelViewSet`, all under `/api/`):

| Endpoint          | Model     |
|-------------------|-----------|
| `/api/users/`     | `User`    |
| `/api/rides/`     | `Ride`    |
| `/api/ride-events/` | `RideEvent` |

**Ride list — filtering, sorting, pagination:**

```
GET /api/rides/?status=pickup
GET /api/rides/?rider_email=rider@example.com
GET /api/rides/?ordering=pickup_time          (or -pickup_time)
GET /api/rides/?ordering=distance&lat=14.5995&lng=120.9842   (or -distance)
GET /api/rides/?page=2&page_size=50
```

`ordering=distance` requires `lat`/`lng`; omitting them, or passing an
unsupported `ordering` value, returns `400`.

Each `Ride` in the response includes the full related rider and driver
(`id_rider`, `id_driver`) and `todays_ride_events` — that ride's `RideEvent`s
from the last 24 hours only.

## Design notes

- **Project layout**: `rideflow/` is the Django project package (settings split
  into `base.py`/`local.py`/`production.py`, config read from `.env` via
  `django-environ`). `rideflow/apps/` holds the two domain apps (`users`,
  `rides`); `apis/` is a thin routing layer — routers, URLs, the
  `IsAdminRole` permission — kept separate from the domain apps so the apps
  stay reusable outside this particular API surface. `rideflow/services/`
  holds the Ride list's query-building logic, kept out of the view so it's
  independently testable. `rideflow/utils/` holds the geo-distance and
  pagination helpers.

- **`User` model**: built on `AbstractBaseUser` + `PermissionsMixin` rather
  than `AbstractUser`, dropping the stock `username` field — `email` is the
  login field (`USERNAME_FIELD`), matching the spec's table (which has no
  `username` column). `role` (`admin`/`rider`/`driver`) is what the API's
  access control checks; it's intentionally separate from Django's own
  `is_staff`/`is_superuser`, which only gate the built-in admin site (kept
  working, for convenience, via custom `UserCreationForm`/`UserChangeForm` —
  the stock ones hardcode the default `auth.User` model). Primary keys
  (`Ride`, `RideEvent`, `User`) are Django's default `id`, not literally
  `id_ride`/`id_ride_event`/`id_user` — the spec's tables read as a conceptual
  schema, and renaming Django's PK convention buys nothing functionally.
  Foreign keys follow the same reasoning: model fields are `rider`/`driver`/
  `ride` (Django's usual `*_id` column convention), not literally
  `id_rider`/`id_driver`/`id_ride`.

- **`id_rider`/`id_driver` in the Ride response**: the spec asks the list to
  include "the related rider and driver (id_rider, id_driver)" — since DRF
  already serializes a bare FK id by default, this only makes sense as a
  request for the *related objects*, not just their ids. `RideSerializer`
  exposes `id_rider`/`id_driver` as nested, read-only `UserSerializer`s
  (`source='rider'`/`source='driver'`), populated via `select_related` at
  zero extra query cost. Writes use separate, plain `rider`/`driver` PK
  fields.

- **`todays_ride_events` (performance requirement)**: `RideQueryService`
  attaches it via
  `Prefetch('ride_events', queryset=RideEvent.objects.filter(created_at__gte=cutoff), to_attr='todays_ride_events')`
  alongside `select_related('rider', 'driver')`. The prefetch issues one
  `WHERE ride_id IN (...) AND created_at >= cutoff` query for the whole page —
  it never scans or loads the full `RideEvent` table, and costs nothing extra
  per row. `RideSerializer.todays_ride_events` is a `SerializerMethodField`
  that just reads the prefetched attribute.

  **Measured query count for `GET /api/rides/`: exactly 3** — 1 `COUNT(*)`
  (pagination), 1 main `SELECT` (`rides_ride` `INNER JOIN` `users_user` twice,
  for rider and driver), 1 prefetch `SELECT` for today's events. Same count
  for both `pickup_time` and `distance` ordering. Proven by
  `assertNumQueries(3)` in `rideflow/apps/rides/tests.py`, not just a manual
  check.

- **Distance sort**: `rideflow/utils/geo.py` builds a great-circle (Haversine
  via the spherical law of cosines) distance expression purely from Django's
  `ACos`/`Cos`/`Sin`/`Radians` ORM math functions and `F()` — no raw SQL
  string. These are cross-backend (Django's SQLite backend registers them
  natively; Postgres has them built in), and the whole computation runs in
  the database via `ORDER BY`, not in Python. It's only annotated when
  `ordering=distance` is actually requested, so `pickup_time` sorts pay
  nothing for it. `pickup_time` itself has a real b-tree index
  (`db_index=True`) for efficient sorting on a large table.

  **Trade-off**: true index-accelerated geospatial sorting needs a
  PostGIS/GiST geometry index, which the spec doesn't allow for (the `Ride`
  table's structure is fixed, and no PostGIS dependency was introduced). The
  ORM-math approach here still computes and sorts entirely in the database —
  just via a full-table `ORDER BY` rather than an index seek. At a scale
  where that matters, the standard next step is either a PostGIS `geography`
  column with a GiST index, or a bounding-box pre-filter on
  `pickup_latitude`/`pickup_longitude` before the exact distance
  computation.

- **`Ride.rider`/`Ride.driver` are required (non-nullable)**: the spec's
  table doesn't call out nullability, so I went with the simpler literal
  reading. A ride that's requested but not yet matched to a driver isn't
  representable as-is; if that's a real scenario, `driver` should become
  nullable.

## Bonus: trips over 1 hour, by month and driver

Each ride's duration is the time between its `'Status changed to pickup'`
and `'Status changed to dropoff'` `RideEvent`s. The CTE pairs those two
timestamps per ride with conditional aggregation (`MIN(...) FILTER (...)`,
robust to more than one matching event per ride), then the outer query keeps
only rides whose dropoff came more than an hour after pickup, and counts them
grouped by the pickup month and driver:

```sql
WITH ride_pickup_dropoff AS (
    SELECT
        re.ride_id,
        MIN(re.created_at) FILTER (WHERE re.description = 'Status changed to pickup')  AS pickup_at,
        MIN(re.created_at) FILTER (WHERE re.description = 'Status changed to dropoff') AS dropoff_at
    FROM rides_rideevent re
    GROUP BY re.ride_id
)
SELECT
    TO_CHAR(rpd.pickup_at, 'YYYY-MM')                AS month,
    CONCAT(u.first_name, ' ', LEFT(u.last_name, 1))  AS driver,
    COUNT(*)                                         AS "count_of_trips_gt_1hr"
FROM ride_pickup_dropoff rpd
JOIN rides_ride  r ON r.id = rpd.ride_id
JOIN users_user  u ON u.id = r.driver_id
WHERE rpd.pickup_at IS NOT NULL
  AND rpd.dropoff_at IS NOT NULL
  AND rpd.dropoff_at > rpd.pickup_at
  AND (rpd.dropoff_at - rpd.pickup_at) > INTERVAL '1 hour'
GROUP BY month, u.id, u.first_name, u.last_name
ORDER BY month, driver;
```

Grouping by `u.id` (not just the formatted `driver` string) avoids merging
two different drivers who happen to share a first name and last-name
initial.
