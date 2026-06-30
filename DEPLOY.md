# Deploying DOC-007-AI

This guide covers two ways to run DOC-007-AI in production:

- Option A: a single virtual machine running everything with Docker Compose.
- Option B: a managed/split setup (web on Vercel, API on a container host, managed datastores).

The application has three runtime pieces and three datastores:

- `apps/api` - FastAPI served by gunicorn with uvicorn workers.
- `apps/api` worker - a Celery worker for background document processing.
- `apps/web` - the Next.js front end (standalone production build).
- Postgres, Redis, and Qdrant.

Read the production hardening checklist at the bottom before you go live.

## Prerequisites

- A domain name and the ability to point DNS at your server.
- A TLS certificate (the easiest path is a reverse proxy that gets one from Let's Encrypt automatically, for example Caddy, Traefik, or nginx with certbot).
- Real API keys: an OpenRouter key for the LLM and an OpenAI key for embeddings.
- A strong random value for `JWT_SECRET_KEY`. Generate one with:

  ```
  openssl rand -hex 32
  ```

## Environment configuration

All configuration lives in a single `.env` file at the repo root. Start from the template:

```
cp .env.example .env
```

Then edit `.env`. The values that must change for production:

- `ENVIRONMENT=production`
- `DEBUG=false`
- `JWT_SECRET_KEY` - set to the random value you generated. Never ship the default.
- `POSTGRES_PASSWORD` - a strong password (the prod compose refuses to start without it).
- `OPENROUTER_API_KEY` - your real key.
- `OPENAI_API_KEY` - your real key.
- `CORS_ORIGINS` - your real front-end origin, for example `https://app.example.com`. Comma-separate if you have more than one.
- `NEXT_PUBLIC_API_BASE_URL` - the public URL the browser uses to reach the API, for example `https://app.example.com/api` or `https://api.example.com`. This is baked into the web bundle at build time, so changing it requires a web rebuild.

In `docker-compose.prod.yml` the `DATABASE_URL`, `REDIS_URL`, `CELERY_*`, and `QDRANT_URL` values are set to reach the other containers by their service names, so you do not need to set those host values yourself for Option A.

---

## Option A: single VM with Docker Compose

This brings up Postgres, Redis, Qdrant, the API, the Celery worker, and the web app on one host. The datastores are kept on the internal Docker network and are not published to the host.

1. Install Docker Engine and the Compose plugin on the VM.
2. Clone the repo and create `.env` as described above.
3. Build and start everything:

   ```
   docker compose -f docker-compose.prod.yml up -d --build
   ```

4. Database migrations. The `api` service runs `alembic upgrade head` automatically before gunicorn starts, so the schema is applied on every deploy. To run migrations manually (for example to inspect status) you can use:

   ```
   docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
   ```

5. Check health:

   ```
   docker compose -f docker-compose.prod.yml ps
   curl -fsS http://127.0.0.1:8000/healthz
   ```

6. Updating to a new version:

   ```
   git pull
   docker compose -f docker-compose.prod.yml up -d --build
   ```

   Old images can be cleaned up with `docker image prune`.

### Reverse proxy and TLS

The compose file publishes only the web app on port 3000 and binds the API to `127.0.0.1:8000` (loopback only). Do not expose those directly. Put a reverse proxy in front that terminates TLS and routes traffic:

- Route browser requests for the app to the `web` container (port 3000).
- Route API requests to the `api` container (port 8000). A common setup is to serve the front end at `https://app.example.com` and proxy `https://app.example.com/api` to the API, or to use a separate `https://api.example.com` host.

Make sure `CORS_ORIGINS` and `NEXT_PUBLIC_API_BASE_URL` match whatever public URLs you settle on. If you change `NEXT_PUBLIC_API_BASE_URL` you must rebuild the web image, because it is compiled into the client bundle.

Caddy is the lowest-effort option for automatic TLS. A minimal `Caddyfile` looks like:

```
app.example.com {
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
```

(If you proxy `/api/*` to the API, make sure the API routes match what the front end calls, or strip the prefix at the proxy.)

### Backups

The data lives in named Docker volumes prefixed with the compose project name `doc-007-ai-prod`: `doc-007-ai-prod_pgdata`, `doc-007-ai-prod_qdrantdata`, `doc-007-ai-prod_redisdata`, and `doc-007-ai-prod_uploads`. Back up at least the pgdata, qdrantdata, and uploads volumes. A simple approach is `docker run --rm -v doc-007-ai-prod_pgdata:/data -v $(pwd):/backup alpine tar czf /backup/pgdata.tgz /data`, scheduled with cron.

---

## Option B: managed / split deployment

Run each piece on a service that fits it best. This avoids managing a VM and gives you managed backups and scaling, at the cost of more moving parts.

### Web on Vercel

1. Import the repo into Vercel and set the project root to `apps/web`.
2. Vercel detects Next.js automatically; no custom build command is needed.
3. Set the environment variable `NEXT_PUBLIC_API_BASE_URL` to your API's public URL (for example `https://api.example.com`). This is required at build time.
4. Deploy. Vercel handles TLS and CDN for the front end.

### API and worker on a container host

Host the API and the Celery worker on a container platform such as Render, Railway, or Fly.io. Both use the production image built from `apps/api/Dockerfile`.

- API service command (run migrations, then serve):

  ```
  sh -c "alembic upgrade head && gunicorn doc007.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000"
  ```

- Worker service command:

  ```
  celery -A doc007.workers.celery_app.celery_app worker --loglevel=info
  ```

- Set all the environment variables from `.env` on each service. Point `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and `QDRANT_URL` at your managed services (below).
- Set `CORS_ORIGINS` to your Vercel domain.
- Expose only the API's HTTP port; the worker needs no inbound ports.
- Note on uploads: the local storage backend writes to a disk path (`STORAGE_LOCAL_PATH`). On a container host with ephemeral disk you need a persistent/attached volume shared between API and worker, or switch to an S3-compatible backend when that lands. For a fully managed setup this is the main thing to plan for.

### Managed datastores

- Postgres: any managed Postgres (Render Postgres, Railway, Neon, Supabase, RDS). Put the connection string in `DATABASE_URL` using the `postgresql+asyncpg://` scheme.
- Redis: a managed Redis (Upstash, Render, Railway). Used for the Celery broker, result backend, and cache.
- Qdrant: Qdrant Cloud. Set `QDRANT_URL` to the cluster URL and `QDRANT_API_KEY` to the cluster key.

Run migrations once against the managed Postgres before first traffic (`alembic upgrade head`), which the API command above does automatically on deploy.

---

## Production hardening checklist

- [ ] `JWT_SECRET_KEY` is a strong random value, not the default from `.env.example`.
- [ ] `DEBUG=false` and `ENVIRONMENT=production`.
- [ ] `POSTGRES_PASSWORD` is strong and unique.
- [ ] Real `OPENROUTER_API_KEY` and `OPENAI_API_KEY` are set.
- [ ] `CORS_ORIGINS` lists only your real front-end origin(s), not `localhost`.
- [ ] `NEXT_PUBLIC_API_BASE_URL` points at the public API URL and the web image was built with it.
- [ ] Postgres, Redis, and Qdrant are NOT published to the public internet. In Option A their ports are unpublished by design; do not add port mappings.
- [ ] TLS is terminated by a reverse proxy in front of the app; nothing serves plain HTTP publicly.
- [ ] `.env` is never committed and has restrictive file permissions on the server.
- [ ] Backups are configured for the Postgres, Qdrant, and uploads volumes (Option A) or enabled on the managed services (Option B).
- [ ] Database migrations have been applied (`alembic upgrade head`).
