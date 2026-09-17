# Deploying EUDAMED Upload on a subdomain (existing VPS: Docker + host nginx + certbot)

> **⚠️ This production VPS does NOT use this runbook's nginx/published-port
> setup.** It runs a separate `Auth` app with a containerised **Caddy** reverse
> proxy on a shared Docker network called `edge`. Every `docker compose` command
> below for THIS box needs an extra overlay file, or the app container gets
> disconnected from `edge` and Caddy returns 502 for `eudamed.asqumis.de`:
> ```bash
> cd ~/apps/Eudamed-Fullstack
> docker compose --env-file .env.prod \
>   -f docker-compose.prod.yml \
>   -f ~/apps/Auth/deploy/eudamed/docker-compose.edge.yml \
>   up -d --build
> ```
> Add the same pair of `-f` flags to every other compose command for this stack
> too (`ps`, `logs`, `exec`, `down`) — see §10 and §11 below, and the overlay
> file's own header comment for why.
>
> **Login and TLS are also different on this box.** §4 (htpasswd) and §6
> (certbot) below do NOT apply here — the `Auth` app's Caddyfile handles both:
> Caddy gets its certificate for `eudamed.asqumis.de` itself (no certbot step
> needed), and every request is gated by `forward_auth` to a separate
> `auth-app` service (password + TOTP, lockout, audit trail) before Caddy
> proxies it to `eudamed-app:8000` — not the shared htpasswd credential from
> §4. That Caddyfile block lives in the `Auth` app's repo, not here. §5's
> nginx server block is also irrelevant on this box for the same reason. The
> nginx/htpasswd/certbot steps below (§4–§8) describe a different, standalone
> deployment style (kept so this repo stays deployable on its own elsewhere).

Runbook for a VPS that is **already set up**: Docker is running, host **nginx**
(systemd) serves a static site, and **certbot** manages Let's Encrypt certs. We
add the EUDAMED tool as a **new subdomain** without touching the existing site.

```
Internet ─443─▶ host nginx (TLS + login) ──proxy──▶ 127.0.0.1:8090 ─▶ app container ─▶ Postgres (internal)
                 (already running)                     (new)            (new)           (new)
```

The app container listens on **127.0.0.1 only** — it is never exposed directly.
nginx terminates TLS (certbot) and adds the login, exactly like your static site.

SSH note: this VPS uses **port 2222**, so connect with `ssh -p 2222 user@host`.

---

## 0. Pick a subdomain and add DNS

Choose e.g. `eudamed.yourdomain.com`. Add a DNS **A record** → the VPS public IP
(a CNAME to the existing site's host also works). Verify from your laptop:

```bash
nslookup eudamed.yourdomain.com      # must resolve to the VPS IP before certbot
```

## 1. Clone the repository

```bash
ssh -p 2222 youruser@<VPS-IP>
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/andreassuchi/Eudamed-Fullstack.git
cd Eudamed-Fullstack
```
(Private repo → use a GitHub PAT as the password, or an SSH deploy key. This
repo is currently **public**, so a plain `git pull` over HTTPS needs no
credentials — if `git pull` suddenly asks for a username/password on the VPS,
check whether the repo was switched back to private on GitHub.)

## 2. Production environment file

```bash
cp .env.prod.example .env.prod
openssl rand -base64 24          # copy this as the DB password
nano .env.prod
```
Set `POSTGRES_PASSWORD` to the random value. Leave `APP_PORT=8090` unless that
port is already used on the host — check with `sudo ss -tlnp | grep 8090` (no
output = free). `.env.prod` is git-ignored and stays only on the server.

## 3. Start the containers (localhost-only)

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```
This builds the app image, initialises Postgres, runs Alembic migrations
automatically, and publishes the app on **127.0.0.1:8090** only.

Verify it's up and *not* public:
```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8090/  # expect 200
sudo ss -tlnp | grep 8090                        # should show 127.0.0.1:8090, NOT 0.0.0.0
docker compose -f docker-compose.prod.yml ps      # containers running/healthy
```
(Use a plain GET, not `curl -sI`/HEAD — the app's routes only register `GET` and
will correctly 405 a HEAD request; that's not a failure.)

## 4. Create the login (HTTP basic-auth)

The app has no login of its own, so nginx enforces one:
```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd-eudamed team      # prompts for a password
# add more users later WITHOUT -c:  sudo htpasswd /etc/nginx/.htpasswd-eudamed alice
```

## 5. Add the nginx server block

Copy the template from the repo and set your real subdomain:
```bash
sudo cp deploy/nginx-eudamed.conf /etc/nginx/sites-available/eudamed
sudo sed -i 's/eudamed.example.com/eudamed.yourdomain.com/' /etc/nginx/sites-available/eudamed
sudo ln -s /etc/nginx/sites-available/eudamed /etc/nginx/sites-enabled/eudamed
sudo nginx -t          # syntax OK?
sudo systemctl reload nginx
```
If `APP_PORT` isn't 8090, also edit the `proxy_pass` line to match.

> If your nginx uses `conf.d/` instead of `sites-available`/`sites-enabled`
> (no symlink pattern), copy the file to `/etc/nginx/conf.d/eudamed.conf` instead.

## 6. Get the TLS certificate

certbot's nginx plugin issues the cert and rewrites the block to add HTTPS +
an HTTP→HTTPS redirect:
```bash
sudo certbot --nginx -d eudamed.yourdomain.com
```
Choose "redirect" if asked. Renewal is automatic (certbot's timer already runs
for your existing site).

## 7. Verify end-to-end

From your laptop open **https://eudamed.yourdomain.com** → browser login prompt
(your htpasswd user) → the dashboard, valid padlock.
```bash
curl -sI https://eudamed.yourdomain.com | head -n1      # HTTP/2 401 (before auth) is expected
```

---

## 8. Firewall (only if you run one)

No new ports are needed — the app is localhost-only and nginx already uses 80/443.
Just make sure 80 and 443 (and SSH 2222) are allowed; **do not** open 8090 or the
DB port. If using ufw and it's not configured yet:
```bash
sudo ufw allow 2222/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable
```

## 9. Off-box backups (recommended, QMS retention)

The app writes scheduled `pg_dump` files into `./backups/` (every 24 h, keeps 30).
Mirror them off the VPS so a host loss isn't data loss, e.g.:
```bash
crontab -e
30 3 * * *  rclone sync ~/apps/Eudamed-Fullstack/backups remote:eudamed-backups
```
Record the backup location, schedule and retention in your QMS docs.

## 10. Updating the app later

```bash
cd ~/apps/Eudamed-Fullstack
git pull
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```
Migrations run on start; the `pgdata` volume persists your data across rebuilds.

> **On this VPS (Caddy/`edge` network — see the warning at the top), always add
> the edge overlay or the update will take the app offline:**
> ```bash
> cd ~/apps/Eudamed-Fullstack
> git pull
> docker compose --env-file .env.prod \
>   -f docker-compose.prod.yml \
>   -f ~/apps/Auth/deploy/eudamed/docker-compose.edge.yml \
>   up -d --build
> ```

## 11. Operations cheat-sheet

Alias once (nginx/standalone box): `alias dc='docker compose --env-file .env.prod -f docker-compose.prod.yml'`

On this VPS (Caddy/`edge`), use this alias instead so every `dc` command below
keeps the app on the `edge` network:
```bash
alias dc='docker compose --env-file .env.prod -f docker-compose.prod.yml -f ~/apps/Auth/deploy/eudamed/docker-compose.edge.yml'
```

| Task | Command |
|---|---|
| Status | `dc ps` |
| Logs (all / app) | `dc logs -f` / `dc logs -f app` |
| Restart app | `dc restart app` |
| Stop / start | `dc down` (keeps data) / `dc up -d` |
| psql shell | `dc exec db psql -U eudamed -d eudamed` |
| Manual dump | `dc exec app pg_dump -h db -U eudamed eudamed > manual-$(date +%F).sql` |
| Add a login | `sudo htpasswd /etc/nginx/.htpasswd-eudamed <user>` (no reload needed) |
| Edit proxy/site | edit `/etc/nginx/sites-available/eudamed` → `sudo nginx -t && sudo systemctl reload nginx` |

## 12. Notes

- The existing static site is untouched — this is an independent server block and
  an independent Docker stack.
- **Do not** deploy Adminer or publish the DB port on this server. Use
  `dc exec db psql` for ad-hoc queries.
- **QMS:** record provider, region/data-centre, OS version, DPA, and the backup
  policy in your supplier/infrastructure documentation.
