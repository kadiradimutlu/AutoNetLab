# AutoNetLab Production-like Deployment Guide

This guide describes the DigitalOcean VM deployment used for the final AutoNetLab public runtime environment.

## Target architecture

- Ubuntu 24.04 VM
- Docker Engine
- Containerlab
- FastAPI backend served by systemd on `127.0.0.1:8000`
- React/Vite production build served by Nginx
- Nginx reverse proxy for `/api/`
- Browser Web CLI WebSocket traffic proxied through `/api/v1/labs/{session_id}/cli/ws/{device_id}`

## Public URLs

Frontend:

```text
http://139.59.151.126
```

Backend health through Nginx:

```text
http://139.59.151.126/api/v1/health
```

Direct backend port should be used only for debugging:

```text
http://139.59.151.126:8000/api/v1/health
```

## Backend environment

Create `/opt/autonetlab/backend/.env`:

```env
APP_NAME=AutoNetLab Backend API
API_PREFIX=/api/v1
ENVIRONMENT=production
CORS_ORIGINS=http://139.59.151.126,http://139.59.151.126:5173,http://139.59.151.126:5174
```

## Frontend environment

Create `/opt/autonetlab/frontend/.env.production`:

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=/api/v1
```

Build frontend:

```bash
cd /opt/autonetlab/frontend
npm install
npm run build
```

## Backend service

Install service:

```bash
cp /opt/autonetlab/deploy/systemd/autonetlab-backend.service /etc/systemd/system/autonetlab-backend.service
systemctl daemon-reload
systemctl enable autonetlab-backend
systemctl restart autonetlab-backend
systemctl status autonetlab-backend --no-pager
```

## Nginx

Install and configure:

```bash
apt install -y nginx
cp /opt/autonetlab/deploy/nginx/autonetlab.conf /etc/nginx/sites-available/autonetlab
ln -sf /etc/nginx/sites-available/autonetlab /etc/nginx/sites-enabled/autonetlab
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx
```

## Smoke tests

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/meta/runtime-readiness
curl -s http://139.59.151.126/api/v1/health
curl -I http://139.59.151.126
docker ps
containerlab inspect --all
```

Expected result:

- Backend health returns ok.
- Runtime readiness returns ready true.
- Frontend opens from port 80.
- Lab deploy, Web CLI, and destroy work from browser.
- Destroy leaves no lab containers behind.
