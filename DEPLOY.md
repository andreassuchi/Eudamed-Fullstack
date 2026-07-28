# Deploying EUDAMED Upload to a VPS (Debian 13, public HTTPS)

Step-by-step runbook for an IONOS (or any) VPS: **Debian 13 ("Trixie")**, a
non-root user **with `sudo`**, reached as a **public HTTPS site behind a login**.
The app never talks to EUDAMED directly — it generates XML you upload manually —
so the only thing exposed is the web UI, protected by TLS + basic-auth.

```
Internet ──443/80──▶ Caddy (TLS + login) ──▶ app :8000 ──▶ Postgres  (all internal)
```

Everything runs from the repo via Docker Compose using two files:
`docker-compose.yml` (base) + `docker-compose.prod.yml` (this production overlay,
which removes the public app/DB ports and adds the Caddy proxy).

---

## 0. Before you start — you need

- The **VPS public IP** and SSH access as your sudo user (root SSH disabled is fine).
- A **domain or subdomain** you control, e.g. `eudamed.yourcompany.com`.
- A **DNS A record** for that name pointing at the VPS IP. Create it now (at your
  DNS provider) so it has time to propagate:
  ```
  eudamed.yourcompany.com.   A   <VPS-PUBLIC-IP>
  ```
  Verify from your laptop before continuing:
  ```
  nslookup eudamed.yourcompany.com
  ```
- A **GitHub Personal Access Token (PAT)** or **deploy key** — the repo is private,
  so cloning needs credentials (Step 5).

All commands below run **on the VPS** unless stated otherwise.

---

## 1. First login and system update

```bash
ssh youruser@<VPS-PUBLIC-IP>
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git ufw curl ca-certificates
```

## 2. Firewall — allow only SSH + web

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp     # Let's Encrypt HTTP challenge + redirect to HTTPS
sudo ufw allow 443/tcp    # the app
sudo ufw enable
sudo ufw status
```
The database and the app's own port are **never** opened — only Caddy is public.

## 3. Install Docker Engine + Compose plugin (official repo)

Do **not** use `apt install docker.io` (it lags). Use Docker's repo:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Let your user run Docker without `sudo`, then re-login so the group applies:

```bash
sudo usermod -aG docker $USER
exit
# ssh back in:
ssh youruser@<VPS-PUBLIC-IP>
docker run --rm hello-world     # sanity check
```

## 4. Clone the repository

Using a PAT (paste the token as the password when prompted, username = your GitHub user):

```bash
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/andreassuchi/Eudamed-Fullstack.git
cd Eudamed-Fullstack
```
(Or set up an SSH deploy key if you prefer key-based pulls.)

## 5. Create the production environment file

```bash
cp .env.prod.example .env.prod
```

Generate the two secrets and edit the file:

```bash
# a strong DB password:
openssl rand -base64 24

# a bcrypt hash for the web login (choose your own password):
docker run --rm caddy:2 caddy hash-password --plaintext 'choose-a-strong-password'
```

```bash
nano .env.prod
```
Set:
- `EUDAMED_DOMAIN` = your domain (must match the DNS A record exactly)
- `ACME_EMAIL`     = your e-mail (Let's Encrypt expiry notices)
- `BASIC_AUTH_USER` = a login name; `BASIC_AUTH_HASH` = the `$2a$...` hash from above
- `POSTGRES_PASSWORD` = the random password from above
- leave `POSTGRES_USER`, `POSTGRES_DB`, `EUDAMED_PROFILE` as-is unless you have a reason

`.env.prod` is git-ignored — it stays only on the server.

## 6. Bring the stack up

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
On first start Docker builds the app image, Postgres initialises its volume, the
app runs Alembic migrations automatically, and Caddy requests the TLS certificate.

Watch it come up:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```
Look for Caddy "certificate obtained successfully" and uvicorn "Application startup
complete". `Ctrl-C` stops following (containers keep running).

## 7. Verify

From your laptop, open **https://eudamed.yourcompany.com** — you should get a
browser login prompt (your basic-auth user), then the dashboard, on a valid
padlock. Certificate issuance can take up to a minute on first load.

Quick checks on the server:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps      # all "running"/"healthy"
curl -sI https://eudamed.yourcompany.com | head -n1                      # HTTP/2 200/401
```

---

## 8. Off-box backups (recommended, QMS record-retention)

The app already writes scheduled `pg_dump` files into `./backups/` inside the repo
(every 24 h by default, keeps 30). To survive a VPS loss, copy them off-box —
e.g. a nightly cron to an EU object store or a second host:

```bash
crontab -e
# 03:30 daily: mirror dumps to a remote (configure rclone first, or use scp/rsync)
30 3 * * *  rclone sync ~/apps/Eudamed-Fullstack/backups remote:eudamed-backups
```
Record the backup location, schedule and retention in your QMS infrastructure docs.

## 9. Updating the app later

```bash
cd ~/apps/Eudamed-Fullstack
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
Migrations run automatically on start. The `pgdata` volume persists your data
across rebuilds.

## 10. Operations cheat-sheet

Prefix is long; set an alias once: `alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod'`

| Task | Command |
|---|---|
| Status | `dc ps` |
| Logs (all / one) | `dc logs -f` / `dc logs -f app` |
| Restart app only | `dc restart app` |
| Stop everything | `dc down` (data volumes kept) |
| Start again | `dc up -d` |
| Add a web login | edit `deploy/Caddyfile` (add a `user hash` line), then `dc restart caddy` |
| psql shell | `dc exec db psql -U eudamed -d eudamed` |
| Manual DB dump | `dc exec app pg_dump -h db -U eudamed eudamed > manual-$(date +%F).sql` |
| Reload Caddy config | `dc restart caddy` |

## 11. Notes / hardening

- **Do not** add Adminer or a public DB port on this server. Use `dc exec db psql`
  for ad-hoc queries, or an SSH tunnel (`ssh -L 5433:localhost:5432 ...` won't work
  since the DB port isn't published — tunnel via `docker exec` or temporarily add a
  `127.0.0.1:5433:5432` mapping only while you need it).
- Consider `sudo apt install unattended-upgrades` for automatic security patches.
- For per-user accountability beyond basic-auth, you can later put an OIDC proxy
  (Authelia) in front — the same Caddy setup accommodates it.
- **QMS:** record provider, region/data-centre, OS version (Debian 13), the DPA,
  and the backup policy in your supplier/infrastructure documentation.
