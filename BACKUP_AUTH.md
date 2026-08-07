# Backup Endpoint Authentication

## Overview

The backup endpoints (`/backups`, `/backups/run`, `/backups/download/{name}`) are now protected with HTTP Basic Authentication to prevent unauthorized access to sensitive database backup files.

## Configuration

Authentication credentials are configured via environment variables:

- `EUDAMED_ADMIN_USERNAME` - Admin username (default: "admin")
- `EUDAMED_ADMIN_PASSWORD` - Admin password (default: "changeme")

**IMPORTANT**: The default password MUST be changed in production environments.

## Setting Credentials

### Via Environment Variables

```bash
export EUDAMED_ADMIN_USERNAME="your_username"
export EUDAMED_ADMIN_PASSWORD="your_secure_password"
```

### Via .env File

```
EUDAMED_ADMIN_USERNAME=your_username
EUDAMED_ADMIN_PASSWORD=your_secure_password
```

## Usage

When accessing backup endpoints, users will be prompted for credentials:

1. Browser access: A login dialog will appear
2. API/curl access: Use HTTP Basic Auth headers

Example with curl:
```bash
curl -u username:password http://localhost:8000/backups
curl -u username:password http://localhost:8000/backups/download/eudamed_20240101_120000.dump
```

## Security Notes

- Credentials are validated using constant-time comparison to prevent timing attacks
- All backup operations (list, download, manual trigger) require authentication
- The scheduled automatic backup process runs without authentication (internal operation)
- Use strong passwords in production environments
- Consider using HTTPS to protect credentials in transit
