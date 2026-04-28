# MabuHive
**Python · Django · JavaScript · React (CDN) · HTML · NGINX · Docker · GCP Cloud Build**

Flat handler/router architecture — adding a new endpoint means adding a handler
file and one line in `server/router.py`. No database yet; CRUD endpoints write
straight to local files under `mnt/`. . 

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
├── mnt/                        Local CRUD storage — folder kept in git, contents gitignored
│
├── docker/
│   ├── Dockerfile              Multi-stage: base → test / local / deploy
│   └── cloudbuild.yaml         GCP CI/CD: test → build → push → deploy
│
├── configs/
│   ├── local/   (.env, nginx.conf — pass-through proxy)
│   ├── test/    (.env, nginx.conf — mirrors prod routing)
│   └── deploy/  (.env.example, nginx.conf — security headers + 30d cache)
│
├── server/                     HTTP server logic
│   ├── server.py               WSGI app + CLI entry + SiteHandler (page serving)
│   ├── router.py               URI → handler routing table
│   └── static.py               StaticHandler — serves /public/<filepath>
│
├── api/                        CRUD endpoints — each route in its own file
│   ├── __init__.py             Shared helpers (MNT_ROOT, resolve_path, json_error)
│   ├── create.py               POST   /api/create?path=...
│   ├── read.py                 GET    /api/read?path=...
│   ├── update.py               PUT    /api/update?path=...
│   ├── delete.py               DELETE /api/delete?path=...&recursive=...
│   └── echo.py                 ALL    /api/echo  (debug)
│
├── public/                     Frontend — served as-is at /public/<filepath>
│   ├── home.html, hives.html, journal.html, profile.html, quests.html
│   ├── css/                    (global.css, …)
│   ├── js/                     (utils.js, default_page.js, NavBar.jsx, *Subpage.jsx, …)
│   ├── data/                   Static data files
│   └── images/                 Static images
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

| Method   | URI                          | Handler          | Description                                  |
|----------|------------------------------|------------------|----------------------------------------------|
| `GET`    | `/`                          | `SiteHandler`    | Serves `public/home.html`                    |
| `GET`    | `/<page_name>`               | `SiteHandler`    | Serves `public/<page_name>.html`             |
| `GET`    | `/public/<filepath>`         | `StaticHandler`  | Serves files from `public/`                  |
| `ALL`    | `/api/echo`                  | `EchoHandler`    | Echoes back the full HTTP request            |
| `POST`   | `/api/create?path=<path>`    | `CreateHandler`  | Writes raw body to `mnt/<path>` (409 if exists) |
| `GET`    | `/api/read?path=<path>`      | `ReadHandler`    | Returns file bytes, or JSON dir listing      |
| `PUT`    | `/api/update?path=<path>`    | `UpdateHandler`  | Overwrites existing `mnt/<path>` (404 if missing) |
| `DELETE` | `/api/delete?path=<path>`    | `DeleteHandler`  | Removes file or empty dir (`&recursive=true` to force) |

### Adding a new endpoint

* **A new CRUD-ish API:** create `api/<name>.py` with a `View` subclass, then
  add one `path("api/<name>", NameHandler.as_view(), …)` line to
  `server/router.py`.
* **A new server-side route (e.g. healthcheck):** add the handler to
  `server/server.py` (small) or its own file in `server/`, then wire it in
  `server/router.py`.

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
for in-browser JSX transformation. Components live flat in `public/js/` as
`.jsx` files and are loaded with `<script type="text/babel" src="...">`.

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
