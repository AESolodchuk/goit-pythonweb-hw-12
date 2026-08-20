# Storing and Managing Contacts

## Setup Instructions

### 1. Install Dependencies

Run the following command to install all dependencies:

```shell
poetry install
```

### 2. Create .env File

Create a .env file in the project root directory and add the necessary credentials:

```
DB_URL=postgresql+asyncpg://<db_user>:<db_password>@localhost:5432/<db_name>
JWT_SECRET=<your_jwt_secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_SECONDS=3600
PASSWORD_RESET_EXPIRATION_SECONDS=900
REDIS_URL=redis://localhost:6379/0
MAIL_USERNAME=<your_mail_username>
MAIL_PASSWORD=<your_mail_password>
MAIL_FROM=<your_mail_from>
MAIL_FROM_NAME=<your_mail_from_name>
MAIL_PORT=<your_mail_port>
MAIL_SERVER=<your_mail_server>

# Cloudinary
CLD_NAME=<your_cloudinary_name>
CLD_API_KEY=<your_cloudinary_api_key>
CLD_API_SECRET=<your_cloudinary_api_secret>

```

Replace the placeholders (e.g., <db_user>, <db_password>, <db_name>, etc.) with your actual credentials.

### 3. Run all services with Docker Compose

Run the following command to start the API, PostgreSQL, and Redis services:

```shell
docker compose up --build
```

The API container waits for PostgreSQL and Redis, applies the latest Alembic migrations, and starts FastAPI on port `8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

### 4. Database migrations

Create a migration after changing the SQLAlchemy models:

```
alembic revision --autogenerate -m "Initial migration"
```

Apply migrations locally with:

```
alembic upgrade head
```

When using Docker Compose, the API container runs `alembic upgrade head` automatically before starting the application.

### 5. Start the Application locally

Run the following command to start the FastAPI application:

```
python main.py
```

The application should now be running and accessible at http://localhost:8000.

## API features

| Method | Route | Purpose | Access |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register` | Register a user | Public |
| `POST` | `/api/auth/login` | Obtain a bearer token | Public |
| `POST` | `/api/auth/request_password_reset` | Request a reset email | Public |
| `POST` | `/api/auth/reset_password` | Set a new password | Public |
| `GET` | `/api/users/me` | Read the current profile | Authenticated |
| `PATCH` | `/api/users/avatar` | Upload a custom avatar | Admin only |
| `GET/POST/PUT/DELETE` | `/api/contacts/` | Manage contacts | Authenticated |

### Password reset and roles

Request `POST /api/auth/request_password_reset` with an email address. The
application sends a short-lived reset token by email; submit that token and a
new password in the JSON body to `POST /api/auth/reset_password`. Reset tokens
expire after `PASSWORD_RESET_EXPIRATION_SECONDS` and are scoped to this purpose.

New accounts receive the `user` role. Set `role=admin` for trusted accounts in
the database. Only users with the `admin` role can call `PATCH /api/users/avatar`.
User identities are cached in Redis for the lifetime of the access token and
are invalidated when the password or avatar changes.

### Tests and documentation

Run the unit and integration test suite with the configured coverage threshold:

```shell
poetry run pytest
```

The project requires total coverage of at least 75%. Run a specific group with
`poetry run pytest tests/unit` or `poetry run pytest tests/integration`.

Build the Sphinx documentation with:

```shell
poetry run sphinx-build -b html docs docs/_build/html
```

Open the generated documentation at `docs/_build/html/index.html`.

## Security notes

- Keep `.env` out of version control. Use `.env.example` as a template and
  replace every placeholder with a secret stored outside the repository.
- Use a long, randomly generated `JWT_SECRET` in production.
- Assign the `admin` role only to trusted accounts.
- Password reset tokens are short-lived and valid only for the reset-password
	purpose.

Ensure Docker is installed and running before executing Docker commands.
