# Kommunitea — Deployment Guide

This covers deploying the Django backend + React frontend to a VPS (e.g. Hostinger VPS, DigitalOcean, etc.).

## 1. Server prep (Ubuntu)
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip postgresql nginx
```

## 2. PostgreSQL
```bash
sudo -u postgres psql
CREATE DATABASE kommunitea;
CREATE USER kommunitea_user WITH PASSWORD 'your-strong-db-password';
GRANT ALL PRIVILEGES ON DATABASE kommunitea TO kommunitea_user;
\q
```

## 3. Backend
```bash
cd /var/www/kommunitea/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env:
#   SECRET_KEY=<generated>   DEBUG=False   USE_SQLITE=False
#   DB_* values, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```
Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Run with gunicorn (via systemd):
```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

## 4. Media files
Uploaded avatars/posts/stories go to `MEDIA_ROOT` (`media/`). In production either:
- Serve `media/` through nginx (simple), or
- Use object storage (S3 / Cloudflare R2) with `django-storages` (recommended at scale).

## 5. nginx (reverse proxy + SSL)
```nginx
server {
  server_name api.yourdomain.com;
  location /static/ { alias /var/www/kommunitea/backend/staticfiles/; }
  location /media/  { alias /var/www/kommunitea/backend/media/; }
  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```
Then add free SSL:
```bash
sudo certbot --nginx -d api.yourdomain.com
```

## 6. Frontend
```bash
cd /var/www/kommunitea/frontend
echo "VITE_API_URL=https://api.yourdomain.com/api" > .env
npm install && npm run build      # outputs dist/
```
Serve `dist/` as a static site (nginx, Netlify, Vercel, or Cloudflare Pages).
nginx for the frontend domain:
```nginx
server {
  server_name yourdomain.com;
  root /var/www/kommunitea/frontend/dist;
  location / { try_files $uri /index.html; }   # SPA fallback
}
```

## 7. Production checklist
- [ ] `DEBUG=False`
- [ ] Strong random `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` set to your domains
- [ ] `CORS_ALLOWED_ORIGINS` = your frontend URL, `CORS_ALLOW_ALL_ORIGINS=False`
- [ ] PostgreSQL (not SQLite)
- [ ] SSL on both domains (HSTS auto-enabled when DEBUG=False)
- [ ] `collectstatic` run; media served
- [ ] superuser created for the admin panel
