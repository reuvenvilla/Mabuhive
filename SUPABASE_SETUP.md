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

## 7. (Optional) Create the `users` table in Supabase

The local file storage backend stores users in `mnt/data/users.json`. When you migrate to Supabase storage (`STORAGE_BACKEND=supabase`), create a table matching the local schema:

```sql
-- run in Supabase SQL editor
create table public.users (
  id          uuid primary key references auth.users(id) on delete cascade,
  username    text unique not null,
  description text default '',
  avatar_url  text default '',
  email       text default '',
  provider    text default '',
  providers   jsonb default '[]'::jsonb,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- enable row level security
alter table public.users enable row level security;

-- anyone can read any user record (public view)
create policy "users are public"
  on public.users for select using (true);

-- a user can update only their own row
create policy "users update own row"
  on public.users for update
  using (auth.uid() = id) with check (auth.uid() = id);

-- a user can insert only their own row
create policy "users insert own row"
  on public.users for insert
  with check (auth.uid() = id);

-- keep updated_at fresh
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;

create trigger users_set_updated_at
  before update on public.users
  for each row execute function public.set_updated_at();
```

You can stay on `STORAGE_BACKEND=local` (the default) until you're ready — the API surface doesn't change.

## 8. Restart and test

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
- `api/resources/users.py` — `/api/users/me` (GET/POST/PUT) + `/api/users/<username>`.
- `api/avatar.py` — `/api/avatar` upload and `/avatars/<file>` serving.
- `public/js/auth.js` — `window.MabuAuth` client wrapper.
- `public/js/UserSubpage.jsx` — the profile UI (owner + viewer modes).
- `public/js/UserCreateSubpage.jsx` — the onboarding form shown on first sign-in.
- `public/css/user.css` — page styling.
