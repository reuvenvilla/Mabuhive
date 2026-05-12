# Supabase OAuth setup

This walks you through everything you need on the Supabase side to make
the profile page work. You only have to do this once per environment
(local dev, staging, prod).

## 1. Create a Supabase project

1. Go to <https://supabase.com> and sign in.
2. **New project** → pick an org, name it (e.g. `mabuhive-dev`), pick a region close to you, set a database password (save it — you won't need it for OAuth but you'll want it eventually).
3. Wait ~1 minute for the project to provision.

## 2. Grab the two values you need

In the Supabase dashboard:

| Value | Where to find it | Used in |
|---|---|---|
| `SUPABASE_URL` | Project Settings → **API** → "Project URL" | server + browser |
| `SUPABASE_ANON_KEY` | Project Settings → **API** → "anon / public" key | server + browser |

Open `configs/local/.env` and paste them in:

```
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
```

> The anon key is meant to be public — it ends up in the browser. The server
> verifies incoming JWTs by calling Supabase's `/auth/v1/user` endpoint (no
> shared JWT secret needed). `SUPABASE_JWT_SECRET` in the .env is optional
> and currently unused.

## 3. Configure redirect URLs

Authentication → **URL Configuration**:

- **Site URL**: `http://localhost:8000` (dev) — change for prod.
- **Redirect URLs** (add one line per environment, including the trailing path you'll come back to):
  - `http://localhost:8000/user`
  - `http://localhost:8000/user/*`
  - `http://localhost:8000/user-create`
  - your production URL(s)

These have to match where the user is when they click "Continue with Google/Discord" — `MabuAuth.signInWithOAuth` sends them back to `window.location.origin + window.location.pathname`.

## 4. Enable email/password

Authentication → **Providers** → **Email**: toggle on.

Optionally turn off "Confirm email" while testing — otherwise users have to click a confirmation link before they can sign in.

## 5. Enable Google OAuth

In the Supabase dashboard:

1. Authentication → Providers → **Google**: toggle on.
2. You'll see Supabase's callback URL — copy it (`https://<project>.supabase.co/auth/v1/callback`).

In the [Google Cloud Console](https://console.cloud.google.com):

1. Pick a project (or create one).
2. APIs & Services → **OAuth consent screen** → configure (External user type, app name, support email). Add your email as a test user.
3. APIs & Services → **Credentials** → **Create credentials → OAuth client ID**:
   - Application type: **Web application**
   - Authorised redirect URIs: paste the Supabase callback URL from step 2 above.
4. Copy the **Client ID** and **Client secret** back into the Supabase Google provider form, **Save**.

## 6. Enable Discord OAuth

In the Supabase dashboard:

1. Authentication → Providers → **Discord**: toggle on, copy the callback URL.

In the [Discord developer portal](https://discord.com/developers/applications):

1. **New Application** → name it.
2. **OAuth2** tab → **Redirects** → add the Supabase callback URL from above → **Save Changes**.
3. Copy the **Client ID** and **Client Secret** back into the Supabase Discord provider form, **Save**.

## 7. **Required:** create the `public.users` table

User records are stored directly in Supabase Postgres. Authorisation is
enforced by row-level-security policies — the backend forwards each
caller's JWT to PostgREST so RLS sees the right `auth.uid()`. Before
anything works, run this in **Supabase Dashboard → SQL editor → New query**:

```sql
-- ── Table ────────────────────────────────────────────────────────────────
-- Only the editable display-side bits live here. Email + OAuth provider
-- stay in auth.users (the backend pulls them from the JWT on read).
create table public.users (
  id          uuid primary key references auth.users(id) on delete cascade,
  username    text not null,
  description text not null default '',
  avatar_url  text not null default '',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- Case-insensitive username uniqueness ("JDoe" and "jdoe" collide).
create unique index users_username_lower_idx
  on public.users (lower(username));

-- ── Row Level Security ───────────────────────────────────────────────────
alter table public.users enable row level security;

-- anyone can read any user record (public view)
drop policy if exists "users are public" on public.users;
create policy "users are public"
  on public.users for select using (true);

-- a user can insert only their own row
drop policy if exists "users insert own row" on public.users;
create policy "users insert own row"
  on public.users for insert
  with check (auth.uid() = id);

-- a user can update only their own row
drop policy if exists "users update own row" on public.users;
create policy "users update own row"
  on public.users for update
  using (auth.uid() = id) with check (auth.uid() = id);

-- a user can delete only their own row (optional — feature for later)
drop policy if exists "users delete own row" on public.users;
create policy "users delete own row"
  on public.users for delete
  using (auth.uid() = id);

-- ── Updated-at trigger ───────────────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;

drop trigger if exists users_set_updated_at on public.users;
create trigger users_set_updated_at
  before update on public.users
  for each row execute function public.set_updated_at();
```

Run it. If you see "table public.users already exists" you've already done
this — only re-run the RLS / trigger blocks if you want to refresh policies.

### Sanity check

In the SQL editor:

```sql
select count(*) from public.users;
```

If you get a count back (zero is fine) without an RLS error, you're good.

## 8. **Required:** create the `avatars` Storage bucket

Avatar images live in Supabase Storage (a separate service from Postgres,
also bundled with your project). The user table only stores the public
URL; the image bytes go to a bucket.

### 8a. Create the bucket (dashboard)

1. Supabase Dashboard → **Storage** → **New bucket**.
2. **Name:** `avatars`
3. **Public bucket:** ✅ on (so the URLs in `users.avatar_url` resolve
   without a signed-URL handshake).
4. **File size limit:** `5 MB` (matches `MAX_BYTES` in `api/avatar.py`).
5. **Allowed MIME types** (optional but recommended):
   `image/png, image/jpeg, image/jpg, image/gif, image/webp`
6. Click **Create bucket**.

### 8b. RLS policies for the bucket (SQL editor)

Storage objects are gated by RLS in the `storage.objects` table. Run this
in the SQL editor so each user can only write into their own folder
(`avatars/<their-uid>/...`) while anyone can read:

```sql
-- ── Storage policies for the avatars bucket ─────────────────────────────

-- Anyone can read avatars (public bucket).
drop policy if exists "Avatars are publicly readable" on storage.objects;
create policy "Avatars are publicly readable"
  on storage.objects for select
  using ( bucket_id = 'avatars' );

-- A user can upload into their own folder: avatars/<uid>/...
drop policy if exists "Users upload own avatar" on storage.objects;
create policy "Users upload own avatar"
  on storage.objects for insert
  with check (
    bucket_id = 'avatars'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

-- ...and update their own files (re-upload over an existing path).
drop policy if exists "Users update own avatar" on storage.objects;
create policy "Users update own avatar"
  on storage.objects for update
  using (
    bucket_id = 'avatars'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

-- ...and delete their own old files (used by the cleanup-on-format-change path).
drop policy if exists "Users delete own avatar" on storage.objects;
create policy "Users delete own avatar"
  on storage.objects for delete
  using (
    bucket_id = 'avatars'
    and auth.uid()::text = (storage.foldername(name))[1]
  );
```

The `(storage.foldername(name))[1]` trick takes the first path segment of
the object key, so `avatars/<uid>/avatar.png` → `<uid>`. The backend
always writes to `<uid>/avatar.<ext>`, so RLS matches the JWT's
`auth.uid()` against that first segment.

### 8c. Sanity check

After uploading an avatar from the profile page, check:

- **Storage → avatars bucket** → you should see a folder named after your user UID containing `avatar.png` (or `.jpg`, `.webp`, etc.).
- **Table editor → public.users → your row** → `avatar_url` should look like
  `https://<project>.supabase.co/storage/v1/object/public/avatars/<uid>/avatar.png?v=...`.
- Visiting that URL directly in the browser should display the image.

## 9. Restart and test

```bash
./scripts/run.sh        # or ./scripts/dockrun.sh
```

Visit <http://localhost:8000/user>:

- Not signed in → you see the sign-in card.
- Sign in with Google/Discord → you bounce through the provider and land back on the user page. First time through you're redirected to `/user-create` to pick a username.
- Sign in with email/password → if "Confirm email" is on, you have to click the link in your inbox first. Same first-time creation flow afterwards.
- After picking a username, the URL rewrites to `/user/<your-username>`.
- Open that same URL in an incognito window → you see only username, avatar, and description.

## File reference

- `api/config.py` — serves the public Supabase values to the browser.
- `api/auth.py` — verifies bearer tokens via Supabase `/auth/v1/user` (with a 60s cache).
- `api/supabase_client.py` — thin urllib wrapper around Supabase PostgREST (`/rest/v1/*`). Forwards the user's JWT so RLS enforces ownership.
- `api/resources/users.py` — `/api/users/me` (GET/POST/PUT) + `/api/users/<username>`. Reads/writes `public.users` in Supabase, **not** local files.
- `api/avatar.py` — `POST /api/avatar`: uploads to the Supabase `avatars` bucket at `<uid>/avatar.<ext>` and PATCHes `public.users.avatar_url` with the bucket's public URL. No more local-disk avatars.
- `public/js/auth.js` — `window.MabuAuth` client wrapper.
- `public/js/UserSubpage.jsx` — the profile UI (owner + viewer modes).
- `public/js/UserCreateSubpage.jsx` — the onboarding form shown on first sign-in.
- `public/css/user.css` — page styling.
