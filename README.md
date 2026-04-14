# Project Boilerplate

**Python · Django · JavaScript · React (CDN) · HTML · NGINX · Docker · GCP Cloud Build**

Flexible handler/dispatcher architecture — adding a new endpoint means adding a
handler file and one line in `server/dispatcher.py`. No database yet; storage is
local files under `build/`.

---

## Quick start (no Docker)

```bash
chmod +x scripts/*.sh
./scripts/run.sh        # → http://localhost:8000
```

## Quick start (Docker)

```bash
./scripts/build.sh local
docker run --rm -p 8000:8000 --env-file configs/local/.env mabuhive:local
# → http://localhost:8000
```

---

## File tree

```
project/
├── requirements.txt            Python dependencies
├── settings.py                 Django settings (root-level, DJANGO_SETTINGS_MODULE=settings)
├── .gitignore
│
├── build/                      ← git-ignored, created at runtime
│   └── posts/                    local post storage (JSON files)
│
├── docker/
│   ├── Dockerfile              Multi-stage: base → test / local / deploy
│   └── cloudbuild.yaml         GCP CI/CD: test → build → push → deploy
│
├── configs/
│   ├── local/
│   │   ├── .env                Safe dev defaults (committed)
│   │   └── nginx.conf          Pass-through proxy (Django serves static in dev)
│   ├── test/
│   │   ├── .env                CI-safe values (committed)
│   │   └── nginx.conf          Mirrors production routing
│   └── deploy/
│       ├── .env.example        Template only — real values via Secret Manager
│       └── nginx.conf          Hardened: security headers, 30-day static cache
│
├── server/
│   ├── __init__.py
│   ├── server.py               WSGI app + CLI entry point (acts as manage.py)
│   ├── dispatcher.py           URI → handler routing table
│   ├── statichandler.py        GET  /api/static/<filepath>
│   ├── echohandler.py          ALL  /api/echo
│   └── sitehandler.py          GET  /<page_name> → frontend/page/<page>.html
│
├── frontend/
│   ├── page/
│   │   ├── home.html           Served at /
│   │   └── blog.html           Served at /blog
│   ├── components/             Placeholder for server-side partials (if needed)
│   └── static/
│       ├── css/
│       │   ├── global.css      Shared CSS variables and base styles
│       │   └── blog.css        Blog-page-specific styles
│       └── js/
│           ├── utils.js        Shared helpers: apiFetch, formatDate, el()
│           └── components/     React components (JSX, loaded via Babel CDN)
│               ├── NavBar.jsx
│               ├── PostCard.jsx
│               └── PostForm.jsx
│
├── scripts/
│   ├── run.sh                  Run dev server directly (no Docker)
│   ├── build.sh [target]       Build Docker image (local / test / deploy)
│   ├── test.sh [--docker]      Run test suite
│   └── clean.sh [--docker]     Wipe build/ and optionally Docker images
│
└── tests/
    ├── conftest.py             pytest + Django bootstrap
    └── test_handlers.py        Smoke tests for all handlers and routes
```

---

## URI routing

| Method | URI                       | Handler          | Description                          |
|--------|---------------------------|------------------|--------------------------------------|
| `GET`  | `/`                       | `SiteHandler`    | Serves `frontend/page/home.html`     |
| `GET`  | `/<page_name>`            | `SiteHandler`    | Serves `frontend/page/<page>.html`   |
| `GET`  | `/api/static/<filepath>`  | `StaticHandler`  | Serves `frontend/static/<filepath>`  |
| `ALL`  | `/api/echo`               | `EchoHandler`    | Echoes back the full HTTP request    |

### Adding a new handler

1. Create `server/myhandler.py` with a class extending `django.views.View`
2. Add one line to `server/dispatcher.py`:
   ```python
   path("api/my-route", MyHandler.as_view(), name="my-route"),
   ```
3. That's it.

---

## Docker targets

```
docker build --target base   -t mabuhive:base   -f docker/Dockerfile .
docker build --target local  -t mabuhive:local  -f docker/Dockerfile .
docker build --target test   -t mabuhive:test   -f docker/Dockerfile .
docker build --target deploy -t mabuhive:deploy -f docker/Dockerfile .
```

Or via the script: `./scripts/build.sh [local|test|deploy]`

---

## React (inline CDN)

No npm or build step. Each HTML page loads React from CDN and Babel standalone
for in-browser JSX transformation. Components live in `frontend/static/js/components/`
as `.jsx` files and are loaded with `<script type="text/babel" src="...">`.

---

## CI/CD — GCP Cloud Build

Pipeline in `docker/cloudbuild.yaml`:
**test image → run tests → build deploy image → push to Artifact Registry → deploy to Cloud Run**

### One-time setup

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com

gcloud artifacts repositories create mabuhive \
  --repository-format=docker --location=us-central1
```

Set these substitution variables in the Cloud Build trigger UI:

| Variable        | Example                                                        |
|-----------------|----------------------------------------------------------------|
| `_REGION`       | `us-central1`                                                  |
| `_SERVICE_NAME` | `mabuhive`                                                     |
| `_REPO`         | `us-central1-docker.pkg.dev/YOUR_PROJECT/mabuhive/mabuhive`    |

Push to `main` → pipeline runs automatically.
