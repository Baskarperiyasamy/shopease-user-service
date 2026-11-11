# ShopEase User Management Service

Independent microservice that manages customer profiles and delivery addresses for ShopEase. It does not handle registration or login. Users are identified by the JWT issued by the Authentication Service (`shopease-auth-service`), and every user can only read and change their own data.

## Technology stack

| Area | Tool |
|---|---|
| Backend | Python 3.11, FastAPI |
| Database | MySQL 8 (`shopease_user_db`) |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Authentication | JWT issued by the Authentication Service (PyJWT, httpx for remote verification) |
| Validation | Pydantic v2 |
| Containers | Docker, Docker Compose |
| Testing | Swagger UI, Postman, pytest |

## Project structure

```
shopease-user-service/
├── app/
│   ├── main.py                       app setup, routers, database error handler, /health
│   ├── routers/
│   │   ├── user_routes.py            profile and account endpoints
│   │   ├── address_routes.py         address endpoints
│   │   └── dependencies.py           get_current_profile, get_active_profile
│   ├── services/
│   │   ├── user_service.py           profile business logic
│   │   └── address_service.py        address logic, default address rule, ownership check
│   ├── models/
│   │   ├── user_model.py             UserProfile table
│   │   └── address_model.py          UserAddress table
│   ├── schemas/
│   │   ├── user_schema.py            profile request and response schemas
│   │   ├── address_schema.py         address request and response schemas
│   │   └── validators.py             shared phone and postal code validation
│   ├── core/
│   │   ├── config.py                 settings from environment
│   │   └── security.py               JWT verification (local or remote)
│   └── database/connection.py        engine, session, get_db, safe_commit
├── alembic/                          migration environment and versions
├── alembic.ini
├── tests/                            pytest suite
├── postman/                          Postman collection
├── docs/PROJECT_EXPLANATION.md       file-by-file explanation and presentation guide
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env  /  .env.example
├── .dockerignore
└── README.md
```

## Database

Database `shopease_user_db`.

`user_profiles`

| Column | Type | Notes |
|---|---|---|
| id | INT | primary key |
| auth_user_id | INT | user ID from the Authentication Service, **unique** |
| full_name | VARCHAR(100) | |
| phone_number | VARCHAR(20) | |
| date_of_birth | DATE | optional |
| gender | VARCHAR(20) | optional |
| profile_image | VARCHAR(255) | optional path or URL |
| is_active | BOOLEAN | profile status, default true (used for deactivation) |
| created_at / updated_at | DATETIME | |

`user_addresses`

| Column | Type | Notes |
|---|---|---|
| id | INT | primary key |
| user_id | INT | foreign key to `user_profiles.id`, ON DELETE CASCADE |
| address_type | VARCHAR(20) | Home, Office or Other |
| full_name, phone_number | | recipient |
| address_line_1, address_line_2 | VARCHAR(255) | line 2 optional |
| city, state, country | VARCHAR(100) | |
| postal_code | VARCHAR(10) | |
| is_default | BOOLEAN | only one true per user |
| created_at / updated_at | DATETIME | |

One profile has many addresses (`UserProfile.addresses` and `UserAddress.profile`). No passwords or credentials are stored here.

## Environment variables

Copy `.env.example` to `.env`.

| Variable | Purpose |
|---|---|
| MYSQL_ROOT_PASSWORD | MySQL root password for the DB container |
| MYSQL_USER, MYSQL_PASSWORD | Application database user |
| MYSQL_DATABASE | `shopease_user_db` |
| MYSQL_HOST, MYSQL_PORT | `localhost` and `3309` when running the app on your machine. Docker Compose overrides them to `user-db` and `3306`. |
| JWT_SECRET_KEY | **Must be identical to the Authentication Service's value** |
| JWT_ALGORITHM | `HS256` |
| TOKEN_VERIFICATION_MODE | `local` (default) or `remote` |
| AUTH_SERVICE_URL | Used in remote mode. Default `http://host.docker.internal:8001` |

`.env` is in `.gitignore`. Never commit it.

## Authentication integration

The User Service has no login or registration. The client logs in on the Authentication Service, then sends the token here:

```
Authorization: Bearer <access_token>
```

Two verification modes are supported:

| Mode | How it works | Trade-off |
|---|---|---|
| `local` (default) | Verifies the signature and expiry with the shared `JWT_SECRET_KEY`. No network call. | Fast and independent. A token stays valid until it expires even if the auth account is deactivated meanwhile. |
| `remote` | Calls `POST {AUTH_SERVICE_URL}/api/auth/verify-token`. | Also checks the account is still active in the Authentication Service. Needs the auth service running. |

In both modes the user ID comes from the token (`sub`). Request bodies that contain `auth_user_id` or `user_id` are rejected with 422, so a client can never claim another user's identity.

Results: 401 for a missing, invalid or expired token. 403 when access is not permitted (another user's address, deactivated profile, inactive auth account in remote mode). 503 if the auth service is unreachable in remote mode.

## Account status across the two services

| Situation | What happens |
|---|---|
| User deactivates profile here (`POST /api/users/profile/deactivate`) | Only `user_profiles.is_active` is set to false. Nothing is sent to or deleted in the Authentication Service. The user can still log in there. Profile update and address endpoints return 403 until the profile is reactivated. Reading the profile and reactivating still work. |
| User deletes profile here (`DELETE /api/users/profile`) | The profile and its addresses are removed. The Authentication Service account is untouched, and the user can create a new profile with the same login. |
| Account is deactivated in the Authentication Service | Login and new tokens are blocked there. In `remote` mode this service returns 403 immediately. In `local` mode existing tokens keep working until they expire (30 minutes by default), so use `remote` if immediate blocking is required. |
| Account is deleted in the Authentication Service | This service does not receive an event, so the profile remains as an orphan. A cleanup job or event would be the next step. |

Rule: the Authentication Service owns identity, credentials and the right to log in. The User Service owns profile data and profile status. Neither service changes the other's data.

## API endpoints

All endpoints need a Bearer token.

### Profile

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/users/profile | Create profile |
| GET | /api/users/profile | Get current user's profile |
| PUT | /api/users/profile | Update profile (full replacement of editable fields) |
| PATCH | /api/users/profile | Partially update profile |
| DELETE | /api/users/profile | Delete profile and addresses |
| PATCH | /api/users/profile/contact | Update contact details (phone number) |
| POST | /api/users/profile/deactivate | Deactivate profile |
| POST | /api/users/profile/reactivate | Reactivate profile |
| GET | /api/users/account | Account overview: token identity, profile, address count, default address |

### Addresses

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/users/addresses | Add an address |
| GET | /api/users/addresses | List own addresses |
| GET | /api/users/addresses/{address_id} | Get one address |
| PUT | /api/users/addresses/{address_id} | Update an address |
| DELETE | /api/users/addresses/{address_id} | Delete an address |
| PATCH | /api/users/addresses/{address_id}/default | Set default address |

### Sample bodies

Create profile:

```json
{
  "full_name": "Alice User",
  "phone_number": "9876543210",
  "date_of_birth": "2000-05-14",
  "gender": "female"
}
```

Gender accepts `male`, `female`, `other`, `prefer_not_to_say` (case-insensitive). Phone numbers need 10 to 15 digits and may start with `+`. Date of birth cannot be in the future.

Add address:

```json
{
  "address_type": "Home",
  "full_name": "Alice User",
  "phone_number": "9876543210",
  "address_line_1": "12 Gandhi Road",
  "address_line_2": "Near Park",
  "city": "Chennai",
  "state": "Tamil Nadu",
  "country": "India",
  "postal_code": "600001",
  "is_default": false
}
```

### Default address rules

- The first address a user adds becomes the default automatically.
- Adding or updating an address with `is_default: true`, or calling the default endpoint, removes the default from the previous address in the same transaction. The profile row is locked during the change so two requests cannot create two defaults.
- Deleting the default address promotes the user's oldest remaining address, so a user with addresses always has exactly one default.

### Status codes

| Code | Meaning |
|---|---|
| 200 / 201 | Success |
| 400 | Empty PATCH body, or deactivating an already deactivated profile (and the reverse) |
| 401 | Missing, invalid or expired token |
| 403 | Another user's address, deactivated profile, or inactive auth account (remote mode) |
| 404 | Profile or address does not exist |
| 409 | Profile already exists for this user |
| 422 | Validation error, including unknown fields such as `auth_user_id` |
| 500 | Database error (the transaction is rolled back) |
| 503 | Authentication Service unreachable (remote mode) |

## Alembic commands

```bash
alembic upgrade head
alembic current
alembic downgrade -1
alembic revision --autogenerate -m "message"
```

Verify the schema:

```bash
docker compose exec user-db mysql -u root -p shopease_user_db -e "SHOW TABLES; DESCRIBE user_profiles; DESCRIBE user_addresses;"
```

## Run with Docker Compose

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f user-service
```

The service container waits for the MySQL health check, runs `alembic upgrade head`, then starts Uvicorn.

- Swagger UI: http://localhost:8002/docs
- Health: http://localhost:8002/health
- MySQL from the host: port 3309

The Authentication Service runs from its own project on port 8001 and is needed to get tokens. Start it first (`docker compose up -d` in `shopease-auth-service`). Both projects must use the same `JWT_SECRET_KEY`.

Stop: `docker compose down`. Remove the database volume too: `docker compose down -v`.

## Run the API locally (database in Docker)

```bash
docker compose up -d user-db
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8002
```

Keep `MYSQL_HOST=localhost` and `MYSQL_PORT=3309` in `.env` for this mode.

## API testing

### Swagger UI

1. Open the Authentication Service Swagger at http://localhost:8001/docs, register and log in, and copy the `access_token`.
2. Open http://localhost:8002/docs, click Authorize, paste the token, and try the endpoints.
3. For the "another user" scenarios, register and log in a second user and authorize with that token.

### Postman

Import `postman/ShopEase_User_Service.postman_collection.json` and run the collection with both services running. It registers two users on the Authentication Service, stores both tokens, and runs 30 requests with status code checks, including the one-default-address check.

### Automated tests

```bash
pytest -v
```

### Results

| Scenario | Expected | Result |
|---|---|---|
| Profile API without token | 401 | Pass |
| Profile API with invalid token | 401 | Pass |
| Create profile with valid token | 201 | Pass |
| Create duplicate profile | 409 | Pass |
| Get authenticated user's profile | 200 | Pass |
| Update profile (PUT) | 200 | Pass |
| Partial update (PATCH) | 200 | Pass |
| Add multiple addresses | 201 | Pass |
| List all addresses | 200 | Pass |
| Update an address | 200 | Pass |
| Set default address | 200 | Pass |
| Only one default address exists | 1 default | Pass |
| Delete an address | 200 | Pass |
| Access another user's profile | own data only / 404 | Pass |
| Access another user's address | 403 | Pass |
| Database records checked after operations | consistent | Pass |

The pytest suite (46 tests) passes. The scenarios above were also run end to end against MySQL 8 with both services running together, using real tokens from the Authentication Service. Add your own Swagger and Postman screenshots here before submitting.

## GitHub

Repository name: `shopease-user-service`

```bash
git init
git add .
git commit -m "Add user management microservice"
git branch -M main
git remote add origin https://github.com/<your-username>/shopease-user-service.git
git push -u origin main
```

Run `git status` first and confirm `.env` is not listed.
