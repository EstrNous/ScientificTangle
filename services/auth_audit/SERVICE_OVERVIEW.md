# Auth Service Overview

## 1. Purpose of the service

`auth_audit` is the authentication service for ScientificTangle.

Its main purpose is to:

- register and store user accounts;
- verify user credentials;
- issue short-lived JWT access tokens;
- manage long-lived refresh sessions securely;
- expose the current authenticated user;
- provide role information for other services;
- let users maintain their profile, password, sessions, and account state;
- let administrators manage coarse roles and account activation;
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
- `email` — unique normalized email address, required for self-registration and optional for legacy seed users.
- `password_hash` — hashed password, never plain text.
- `role` — one of: `admin`, `researcher`, `analyst`, `manager`, `external_partner`.
- `is_active` — whether the user is allowed to sign in.
- `created_at` — creation timestamp.
- `updated_at` — last update timestamp.
- `deactivated_at` — timestamp of soft account deactivation.

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
- The service writes structured audit events for identity, session, and role lifecycle actions without credentials or tokens.

## 3. Endpoints

### `POST /api/auth/register`

Creates an active `external_partner` account with a unique username and email, starts a refresh session, and returns the same token response shape as login. The request cannot select a role.

New passwords must be 8–128 characters and contain at least one uppercase ASCII letter, one lowercase ASCII letter, and one digit.

### `POST /api/auth/login`

What it does:

- accepts `identifier` and `password`, where the identifier is a username or email address;
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

### `PATCH /api/auth/me`

Updates the authenticated user's normalized username or email after verifying the current password. Existing sessions remain active.

### `POST /api/auth/change-password`

Verifies the current password, applies the new-password policy, revokes every refresh session, and returns a fresh token pair.

### `POST /api/auth/logout-all`

Revokes every refresh session owned by the authenticated user and clears the refresh cookie.

### `DELETE /api/auth/me`

Verifies the current password, soft-deactivates the account, revokes all refresh sessions, and clears the refresh cookie.

### `GET /api/auth/users`

Returns a bounded paginated user list to administrators.

### `PATCH /api/auth/users/{user_id}`

Lets an administrator change a user's coarse role or active state. Role changes and deactivation revoke all refresh sessions.

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

`auth_audit` is the identity entry point of the project.

It owns the complete practical identity lifecycle: registration, user storage, authentication, profile and password maintenance, refresh sessions, soft deactivation, and coarse role administration. Domain services remain responsible for resource-specific authorization.
