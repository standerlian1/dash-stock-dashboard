# Plotly Dash Stock Dashboard (Render + Supabase + yfinance)

A production-ready Dash dashboard for **TSM, AAPL, NVDA, ^GSPC**, with:

- **30-minute intraday ingestion** (09:30–16:00 New York time) via **yfinance**
- **Daily candles** for zoomed-out views + a default **last ~3 months** view
- **Supabase persistence** (no reliance on live yfinance at startup)
- **In-app scheduler** (APScheduler) with a **Supabase-backed distributed lock** (safe under Render multi-instance scaling)
- **Indicator plugin system** with **schema-driven parameter UI** (SMA/EMA included as examples)

> Note on Yahoo intraday limits: yfinance/Yahoo generally restrict intraday (interval < 1d) history to ~60 days. citeturn0search12  
> To satisfy “last 3 months” default view, this app stores **daily bars** in a separate table.

---

## Final Project Structure (DO NOT CHANGE)

```
dash_stock_dashboard/
  app.py
  src/
    __init__.py
    config.py
    logging_config.py
    supabase_client.py
    data/
      __init__.py
      market_time.py
      yfinance_fetcher.py
      supabase_repo.py
      resample.py
    indicators/
      __init__.py
      base.py
      registry.py
      sma.py
      ema.py
    scheduler/
      __init__.py
      lock.py
      ingest_job.py
      scheduler.py
    ui/
      __init__.py
      layout.py
      indicator_controls.py
      callbacks.py
  requirements.txt
  .env.example
  README.md
```

---

## Supabase Setup (Required)

### 1) Create a Supabase project
- Go to Supabase and create a new project.
- Copy:
  - **Project URL** → `SUPABASE_URL`
  - **Service role key** → `SUPABASE_SERVICE_ROLE_KEY` (server-side only; do not expose to browsers)

### 2) Create tables + indexes

Run the SQL below in Supabase SQL editor.

#### A) Intraday table (30-minute bars)

```sql
create table if not exists public.price_bars_30m (
  ticker text not null,
  ts_utc timestamptz not null,
  ny_date date not null,
  ny_time time not null,
  open double precision not null,
  high double precision not null,
  low double precision not null,
  close double precision not null,
  inserted_at timestamptz not null default now(),
  primary key (ticker, ts_utc)
);

create index if not exists idx_price_bars_30m_ticker_ts on public.price_bars_30m (ticker, ts_utc desc);
create index if not exists idx_price_bars_30m_ny_date on public.price_bars_30m (ticker, ny_date desc);
```

#### B) Daily table (1-day bars)

```sql
create table if not exists public.price_bars_1d (
  ticker text not null,
  ny_date date not null,
  open double precision not null,
  high double precision not null,
  low double precision not null,
  close double precision not null,
  inserted_at timestamptz not null default now(),
  primary key (ticker, ny_date)
);

create index if not exists idx_price_bars_1d_ticker_date on public.price_bars_1d (ticker, ny_date desc);
```

#### C) App state table (last ingestion status)

```sql
create table if not exists public.app_state (
  key text primary key,
  last_success_utc timestamptz null,
  last_error text null,
  updated_at timestamptz not null default now()
);
```

#### D) Distributed lock table + lease

```sql
create table if not exists public.distributed_locks (
  lock_name text primary key,
  owner_id text not null,
  lease_expires_at timestamptz not null,
  heartbeat_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_distributed_locks_expires on public.distributed_locks (lease_expires_at);
```

### 3) Create Postgres functions for atomic lock operations

These functions provide an **atomic** acquire/renew/release using Postgres (safe under multi-instance scaling).

```sql
create or replace function public.acquire_ingest_lock(
  p_lock_name text,
  p_owner_id text,
  p_lease_seconds int
)
returns boolean
language plpgsql
as $$
declare
  v_now timestamptz := now();
  v_new_exp timestamptz := now() + make_interval(secs => p_lease_seconds);
begin
  insert into public.distributed_locks(lock_name, owner_id, lease_expires_at, heartbeat_at, updated_at)
  values (p_lock_name, p_owner_id, v_new_exp, v_now, v_now)
  on conflict (lock_name) do update
    set owner_id = excluded.owner_id,
        lease_expires_at = excluded.lease_expires_at,
        heartbeat_at = excluded.heartbeat_at,
        updated_at = excluded.updated_at
    where public.distributed_locks.lease_expires_at < v_now
       or public.distributed_locks.owner_id = p_owner_id;

  return exists (
    select 1
    from public.distributed_locks
    where lock_name = p_lock_name
      and owner_id = p_owner_id
      and lease_expires_at >= v_now
  );
end;
$$;


create or replace function public.heartbeat_ingest_lock(
  p_lock_name text,
  p_owner_id text,
  p_lease_seconds int
)
returns boolean
language plpgsql
as $$
declare
  v_now timestamptz := now();
  v_new_exp timestamptz := now() + make_interval(secs => p_lease_seconds);
begin
  update public.distributed_locks
    set lease_expires_at = v_new_exp,
        heartbeat_at = v_now,
        updated_at = v_now
  where lock_name = p_lock_name
    and owner_id = p_owner_id;

  return found;
end;
$$;


create or replace function public.release_ingest_lock(
  p_lock_name text,
  p_owner_id text
)
returns boolean
language plpgsql
as $$
begin
  delete from public.distributed_locks
  where lock_name = p_lock_name
    and owner_id = p_owner_id;
  return found;
end;
$$;
```

---

## Local Development

### 1) Clone repo and install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure env

Copy `.env.example` to `.env` and fill:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Optional:
- `ENABLE_SCHEDULER=true`
- `LOG_LEVEL=INFO`

### 3) Run

```bash
python app.py
```

Open: `http://localhost:8050`

---

## Deployment to Render (Web Service)

Render runs your web service using a **Start Command** like `gunicorn app:server`. citeturn0search1turn0search11turn0search18

### 1) Create a GitHub repo
- Create a new GitHub repository and push this code.

### 2) Create a Render Web Service
- **Environment**: Python
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  gunicorn app:server --workers 2 --threads 2 --timeout 120
  ```

> If you change filenames, keep `server = app.server` in the module and adjust the start command accordingly.

### 3) Render environment variables
Set these in Render Dashboard → Environment:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ENABLE_SCHEDULER=true`
- `LOG_LEVEL=INFO`
- (Optional) `INGEST_LOCK_LEASE_SECONDS=120`

### 4) Scaling considerations (multi-instance)
- Render may run multiple instances/workers.
- **Each process** will start APScheduler.
- **Only one process globally** actually ingests at a time because it must acquire the Supabase lock via `acquire_ingest_lock()`.

---

## How the Scheduler + Distributed Lock Works

- APScheduler triggers ingestion at:
  - **Every 30 minutes** between 09:30 and 16:00 NY time (plus internal guards)
  - **Daily** at 16:20 NY time for daily candles
- Each job attempts to acquire a **Supabase/Postgres lock**:
  - If lock acquired → ingestion proceeds
  - If not → job exits (another instance is ingesting)
- The lock has a **lease** (`lease_expires_at`), so if an instance dies, the lock can be taken after it expires.

### Verify only one instance is ingesting
1. In Supabase, run:
   ```sql
   select * from public.distributed_locks;
   ```
2. Check Render logs across instances:
   - Only one should log “Background scheduler started …” and “Ingestion run complete …”
   - Others should log “Another instance holds ingestion lock; skipping.”

---

## Notes / Operational Tips

- This implementation filters to **weekday** regular session 09:30–16:00 NY time.
- Market holidays are not currently handled (you can add a calendar module later).
- When zooming into a ≤10-day range, the dashboard uses **30-minute candles**; otherwise, it uses **daily candles**.

---

## Adding New Indicators (Plugin Pattern)

1. Add a new file under `src/indicators/`, implementing `Indicator`.
2. Register it in `src/indicators/registry.py`.
3. The UI will auto-generate controls from the indicator’s `param_schema()`.

No ingestion changes required.

---

## Supabase Python Client References

- Client initialization with `create_client()` citeturn1view1
- Upsert support (including `on_conflict`) citeturn1view0
