# Auth Service Overview

## 1. Purpose of the service

`auth_service` is the authentication service for ScientificTangle.

Its main purpose is to:

- verify user credentials;
- issue short-lived JWT access tokens;
- manage long-lived refresh sessions securely;
- expose the current authenticated user;
- provide role information for other services;
- publish the public signing key through JWKS so other parts of the system can validate tokens.

In practical terms, this service answers the question: "Who is the user and can we trust this identity?"

It does not implement the full document access-policy logic. It provides authentication and the basic role layer that other services can build on.

## 2. Data structure

The service uses PostgreSQL and stores two main tables.

### `users`

This table stores the application users.

Fields:

- `id` — UUID primary key of the user.
- `username` — unique normalized login name.
- `email` — optional email address.
- `password_hash` — hashed password, never plain text.
- `role` — one of: `admin`, `researcher`, `analyst`, `manager`, `external_partner`.
- `is_active` — whether the user is allowed to sign in.
- `created_at` — creation timestamp.
- `updated_at` — last update timestamp.

Why we store it:

- to identify each user;
- to authenticate by username and password;
- to know the user role for authorization checks;
- to disable a user without deleting their account.

### `refresh_sessions`

This table stores refresh-token sessions.

Fields:

- `id` — UUID primary key of the refresh session.
- `user_id` — reference to the user who owns the session.
- `family_id` — token-family identifier used for rotation and replay detection.
- `token_hash` — SHA-256 hash of the refresh token.
- `expires_at` — refresh-session expiration timestamp.
- `revoked_at` — timestamp when the session was revoked.
- `replaced_by_id` — reference to the next rotated session.
- `created_at` — creation timestamp.
- `last_used_at` — timestamp of last successful use.
- `ip_address` — optional client IP.
- `user_agent` — optional client user agent.

Why we store it:

- to support refresh-token rotation;
- to avoid storing raw refresh tokens in the database;
- to revoke a session on logout;
- to detect replay of an already-rotated refresh token;
- to revoke the full token family if reuse is detected;
- to keep basic security and audit-related metadata.

### Other data-related behavior

- Access tokens are not stored in the database. They are generated on demand and signed with RSA using `RS256`.
- Refresh tokens are stored on the client only as cookies and in the database only as SHA-256 hashes.
- Refresh cookies are configured as `HttpOnly`, `Secure`, `SameSite=Strict`, and are scoped to `/api/auth`.
- Seed users can be created from environment variables such as `AUTH_SEED_ADMIN_USERNAME` and `AUTH_SEED_ADMIN_PASSWORD`.
- The service emits internal audit events for login, refresh, logout, refresh-token reuse, and authorization denial.

## 3. Endpoints

### `POST /api/auth/login`

What it does:

- accepts `username` and `password`;
- validates the credentials;
- checks that the user exists and is active;
- creates a JWT access token;
- creates a refresh token and stores its hash in PostgreSQL;
- sets the refresh token in a secure cookie;
- returns the access token and user info.

Response contains:

- `access_token`;
- `token_type`;
- `expires_in`;
- `user`.

### `POST /api/auth/refresh`

What it does:

- reads the refresh token from the cookie;
- validates request origin against the allowlist;
- checks the stored refresh session;
- rotates the refresh token;
- creates a new access token;
- stores the new refresh-session hash;
- revokes the previous refresh session.

Special behavior:

- if an old rotated refresh token is used again, the service treats it as token reuse or replay and revokes the whole token family.

### `POST /api/auth/logout`

What it does:

- validates request origin;
- reads the refresh token from the cookie;
- revokes the corresponding refresh session if it exists;
- clears the refresh cookie;
- returns `204 No Content`.

### `GET /api/auth/me`

What it does:

- reads the bearer access token from the `Authorization` header;
- validates JWT signature and claims;
- loads the current user from the database;
- returns the authenticated user.

This endpoint is useful when the frontend wants to know who is currently signed in.

### `GET /.well-known/jwks.json`

What it does:

- returns the public RSA key in JWKS format;
- includes the configured `kid`.

This lets gateways or other backend services validate access tokens without needing the private key.

### `GET /health`

What it does:

- returns a simple liveness response;
- shows that the service process is running.

### `GET /ready`

What it does:

- checks that the RSA key pair is valid;
- checks that the database is reachable;
- returns service readiness status.

This endpoint is for deployment and infrastructure readiness checks.

### `GET /metrics`

What it does:

- exposes Prometheus metrics;
- currently includes HTTP request metrics for this service.

## Summary

`auth_service` is the identity entry point of the project.

It stores users and refresh sessions, signs access tokens, rotates refresh tokens safely, and gives the rest of the system a trusted authenticated user with a role.
