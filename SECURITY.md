# Security Policy

DOC-007-AI is a multi-tenant application, so isolation between tenants is treated as the most important property of the system. This document describes the model that is implemented today and the hardening that is planned.

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue. Use GitHub's private vulnerability reporting on this repository (the **Security** tab, "Report a vulnerability"). Include steps to reproduce and the impact you observed, and you will get an acknowledgement as soon as possible.

## Security model

**Tenant isolation.** Every workspace-scoped database query filters by `workspace_id`, and every vector search sends a mandatory server-side `workspace_id` payload filter to Qdrant that is never controlled by the client. Retrieved chunks are re-checked against the workspace when they are hydrated from the database. Membership is verified on every request, and a request for a workspace you do not belong to returns `404` rather than `403`, so the existence of other tenants is not leaked. Client-supplied document ids are intersected with the workspace filter, so an id from another tenant simply returns nothing.

**Authentication and access control.** Passwords are hashed with argon2id. Authentication uses short-lived JWT access tokens with longer-lived refresh tokens, and the frontend transparently refreshes on expiry. Logout and refresh both revoke tokens through a Redis-backed denylist: refresh tokens are single-use and rotated on every refresh, so a stolen or logged-out token stops working immediately. The authentication endpoints are rate-limited per IP to slow credential stuffing. Google and GitHub SSO are supported. Roles (owner, admin, member) are enforced on every mutating endpoint, and sensitive actions (member and key management, workspace settings, deletion) require the appropriate role.

**Secrets.** API keys and invitation tokens are stored only as SHA-256 hashes and the raw value is shown exactly once. AI provider keys are server-side only and are never exposed to the browser. The `.env` file is gitignored.

**Prompt-injection defense.** Retrieved document text is wrapped in a context block and explicitly marked as untrusted reference data in the system prompt. Document content never enters the instruction (system) role, so a document cannot redirect the model.

**Abuse controls.** The public API is rate-limited per key (Redis fixed window), and each workspace can enforce a monthly question quota that is checked before any tokens are spent.

**Audit trail.** Uploads, deletes, invitations, role changes, and API-key lifecycle events are recorded per workspace.

## Hardening roadmap

This is a portfolio project, and the following defense-in-depth items are tracked as deliberate next steps:

- **PostgreSQL Row-Level Security** as a database-level backstop beneath the application-level workspace scoping.
- **Security headers** (CSP, HSTS, X-Frame-Options, X-Content-Type-Options) via middleware.
- **Streaming upload limits and extraction caps** to bound memory use on very large or adversarial files.
- **OAuth `state` validation and a redirect-URI allowlist** to fully close login-CSRF vectors.

## Scope and expectations

The defaults shipped in `docker-compose.yml` and `.env.example` are for local development (debug mode, development credentials, a placeholder JWT secret). A real deployment must set a strong `JWT_SECRET_KEY`, disable debug, use managed secrets, and not expose the database, Redis, or Qdrant ports publicly.
