# UK Job Tribe (UJT) — Backend

Django 6 + DRF + PostgreSQL API for the UJT community platform.
**Fully integrated** with the UJT React frontend (camelCase JSON, JWT auth).

## What's included
- **JWT auth** (`/api/auth/register|login|refresh|me`) using a custom email-based User
- **Profiles** (`/api/profiles/`) — full community profile, onboarding, follow/unfollow, avatar upload
- **Posts** (`/api/posts/`) — feed, create, like, save, comment, image upload, `?mine=true`, `?category=`
- **Members / Jobs / Team** — original community endpoints
- **camelCase** request & response bodies (matches the React frontend exactly)
- **Swagger** at `/api/docs/`, ReDoc at `/api/redoc/`
- **23 passing tests** covering the full auth + posts + profile flow

## Quick start (local, SQLite)
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_team        # optional: loads the real team
python manage.py createsuperuser
python manage.py runserver        # http://localhost:8000
```

## Key endpoints
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /api/auth/register/ | – | Create account |
| POST | /api/auth/login/ | – | Get JWT {access, refresh} |
| GET/PATCH | /api/auth/me/ | ✓ | Current user profile |
| GET | /api/profiles/{id}/ | – | View a profile |
| PATCH | /api/profiles/me/ | ✓ | Update profile / onboarding |
| PATCH | /api/profiles/me/avatar/ | ✓ | Upload avatar |
| POST | /api/profiles/{id}/follow/ | ✓ | Follow / unfollow |
| GET/POST | /api/posts/ | mixed | Feed / create post |
| POST | /api/posts/{id}/like/ | ✓ | Toggle like |
| POST | /api/posts/{id}/save/ | ✓ | Toggle save |
| POST | /api/posts/{id}/comments/ | ✓ | Add comment |

## Production (PostgreSQL)
1. `cp .env.example .env`, set `USE_SQLITE=False` + DB creds + `SECRET_KEY`
2. `pip install -r requirements.txt && python manage.py migrate`
3. `python manage.py collectstatic`
4. `gunicorn config.wsgi:application --bind 0.0.0.0:8000`
5. nginx in front for SSL + serving `/media` and `/static`

## Run tests
```bash
python manage.py test
```
