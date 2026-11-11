# Project explanation for presentation

## One-line summary

The User Management Service stores customer profiles and delivery addresses in its own MySQL database. It never handles passwords or login. It trusts the JWT issued by the Authentication Service, takes the user ID from that token, and lets each user touch only their own data.

## Overall flow

```
Client ──login──▶ Authentication Service ──JWT──▶ Client
Client ──Bearer JWT──▶ User Service ──▶ shopease_user_db
```

1. The client logs in on the Authentication Service and receives a JWT containing the user ID (`sub`) and role.
2. The client calls the User Service with `Authorization: Bearer <token>`.
3. `core/security.py` verifies the token (signature and expiry, or by calling the auth service in remote mode) and returns the user ID.
4. `routers/dependencies.py` uses that ID to load the user's own profile. The client never sends an ID to prove who they are.
5. The router calls a service function. The service applies the rules and saves through SQLAlchemy.
6. The response schema returns only the fields meant to be public.

## Request layers

| Layer | Folder | Responsibility |
|---|---|---|
| Router | `routers/` | HTTP only: paths, status codes, dependencies |
| Schema | `schemas/` | Validates input, shapes output |
| Service | `services/` | Business rules: duplicates, ownership, default address |
| Model | `models/` | Table definitions and relationships |
| Security | `core/security.py` | Token verification |
| Database | `database/connection.py` | Engine, session, commit with rollback |

## File by file

### app/main.py
Creates the FastAPI app, registers the profile and address routers, adds `/health`, and registers a handler that turns any `DatabaseError` into a clean 500 response. Say: "Entry point. It only wires things together, there is no business logic here."

### app/core/config.py
Reads all settings from environment variables with Pydantic Settings: database parts, JWT secret and algorithm, token verification mode, auth service URL. It builds the database URL safely so special characters in the password do not break it. Say: "Nothing is hardcoded, so the same image runs in any environment."

### app/core/security.py
The integration point with the Authentication Service. `get_auth_user` reads the Bearer token and returns an `AuthUser` (id, role). Two modes:
- `local`: verifies signature and expiry with the shared secret. Fast, no network call.
- `remote`: calls the auth service's `/api/auth/verify-token`. Also catches deactivated accounts.
Missing or bad token gives 401, inactive account gives 403, auth service down gives 503. Say: "This is the only file that knows how tokens work. Every other file just receives a trusted user ID."

### app/database/connection.py
Creates the SQLAlchemy engine and session factory, `get_db` (opens a session per request and always closes it), and `safe_commit` (commit, and on failure roll back and raise `DatabaseError`). Say: "A failed save never leaves a half-written transaction."

### app/models/user_model.py
`UserProfile` maps to `user_profiles`. `auth_user_id` is unique, so one profile per authenticated user. It has `is_active` for deactivation and a one-to-many `addresses` relationship with cascade delete. Say: "No password column exists here, by design."

### app/models/address_model.py
`UserAddress` maps to `user_addresses`, with a foreign key to the profile (ON DELETE CASCADE) and an `is_default` flag. Say: "Addresses belong to the local profile ID, not directly to the auth ID."

### app/models/__init__.py
Imports both models so Alembic and SQLAlchemy see them.

### app/schemas/validators.py
Shared validation: phone numbers (10 to 15 digits, optional +, spaces and dashes cleaned), postal codes, and trimmed text types. Used by both profile and address schemas so rules stay in one place.

### app/schemas/user_schema.py
Request and response models for profiles: `ProfileCreate`, `ProfileUpdate` (PUT, full replacement), `ProfilePatch` (all fields optional, required fields cannot be set to null), `ContactUpdate`, `ProfileOut`, `AccountOut`. All request models forbid extra fields, so sending `auth_user_id` returns 422. Date of birth cannot be in the future and gender is limited to a fixed list.

### app/schemas/address_schema.py
`AddressCreate`, `AddressUpdate` and `AddressOut`. Address type must be Home, Office or Other (case-insensitive). Required fields are validated, and `user_id` in the body is rejected.

### app/services/user_service.py
Profile logic: create (409 for duplicates, including a race caught through the unique constraint), PUT, PATCH (400 if empty), contact update, activate and deactivate, delete. Say: "Routes stay thin. All decisions happen here."

### app/services/address_service.py
Address logic and the two most important rules:
- Ownership: `get_owned_address` returns 404 if the address does not exist and 403 if it belongs to someone else, so changing the ID in the URL gives nothing.
- Single default: setting a default clears the old one in the same transaction, with the profile row locked to avoid two defaults under concurrent requests. The first address becomes default automatically, and deleting the default promotes the oldest remaining address.

### app/routers/dependencies.py
`get_current_profile` finds the profile of the token's user (404 if none). `get_active_profile` adds a check that the profile is not deactivated (403). Routes declare which one they need.

### app/routers/user_routes.py
Profile CRUD, contact update, deactivate and reactivate, and the account overview. Each route receives the current profile from a dependency, so there is no user ID in any URL or body.

### app/routers/address_routes.py
The six address endpoints. All require an active profile, and `address_id` is always checked for ownership in the service.

### alembic/env.py, alembic.ini, script.py.mako
Alembic setup. `env.py` takes the database URL from the same settings as the app and uses the models' metadata.

### alembic/versions/0001_create_profiles_and_addresses.py
Creates both tables, the unique index on `auth_user_id`, and the foreign key with cascade delete. It has a working `downgrade`. Say: "Schema changes are versioned and reversible instead of created by the app on startup."

### Dockerfile
Python 3.11 slim image, installs `requirements.txt`, copies the app, exposes port 8002. The start command runs `alembic upgrade head` and then Uvicorn, so migrations are part of startup.

### docker-compose.yml
Two services: `user-db` (MySQL 8 with a named volume and a `mysqladmin ping` health check) and `user-service`. The service starts only when the database is healthy, connects with the host name `user-db`, and has `host.docker.internal` mapped so it can reach the auth service in remote mode.

### .env / .env.example
Real values for local use, and a template for the repository. `.env` is git-ignored. The JWT secret must match the Authentication Service.

### .dockerignore, .gitignore
Keep `.env`, virtual environments, caches and tests out of the image and out of Git.

### requirements.txt, requirements-dev.txt
Pinned runtime dependencies, and the same plus pytest for development.

### tests/
- `test_profile.py`: tokens (missing, invalid, expired, wrong secret), create, duplicate, validation, PUT, PATCH, contact, delete with cascade, deactivate and reactivate, account overview, and isolation between two users.
- `test_addresses.py`: add, list, get, update, set default, one-default rule, delete and promotion, validation, and cross-user access (403) and missing address (404).
- `test_auth_integration.py`: remote verification with a mocked auth service (valid, invalid, inactive, service down).
- `conftest.py`: in-memory test database and token helpers.

### postman/ShopEase_User_Service.postman_collection.json
30 requests that register and log in two users on the Authentication Service, then run every mandatory scenario with status checks.

### README.md
Setup, environment, endpoints, account status rules, Docker commands, test results and GitHub steps.

## Demo order (about 4 minutes)

1. Start the Authentication Service, then this service (`docker compose up --build -d`).
2. In the auth Swagger, register and log in two users (A and B). Keep both tokens.
3. User service Swagger: call `/api/users/profile` with no token (401), then authorize as A and create a profile (201). Create again (409).
4. Add three addresses, make the third the default, then call the default endpoint on another one. List addresses and show there is exactly one default.
5. Authorize as B and open one of A's address IDs. Show 403. Open ID 99999. Show 404.
6. Try to send `"auth_user_id": 1` in a request body. Show 422.
7. Deactivate the profile, show 403 on addresses, reactivate.
8. Show the tables in MySQL: no passwords, `auth_user_id` unique, foreign key between the tables.

## Likely questions

**Why does the User Service not verify users through the database?** It has no user table for credentials on purpose. Identity belongs to the Authentication Service, which keeps the services independent.

**Why a shared secret instead of calling the auth service every time?** It is faster and keeps working if the auth service is down. The cost is that a deactivated account's token works until it expires. Remote mode closes that gap at the price of a network call per request.

**Why 403 for another user's address and not 404?** The task asks for 403 when access is not permitted. Returning 404 would hide whether an address exists. It is a one-line change in `get_owned_address` if the team prefers that.

**How do you guarantee one default address?** The change happens in one transaction, with the profile row locked, and the service clears the old default before setting the new one. MySQL cannot enforce a "one true per user" rule with a simple constraint.

**What happens to the profile if the auth account is deleted?** It stays, because there is no event between the services yet. A cleanup job or message would be the next step.

**What are the limitations?** No admin role to view other users, no profile image upload (only a path or URL), no pagination on addresses, and no event sync with the Authentication Service.
