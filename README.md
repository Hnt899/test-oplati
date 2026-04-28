# test-oplati

Django backend for selling catalog items through **Stripe Checkout** and **Payment Intents**, with multi-currency Stripe accounts (RUB / EUR), orders composed of multiple line items, discounts, taxes, Docker tooling, pytest coverage, and GitHub Actions CI.

## Features

- Models: `Item`, `Order` (M2M via `OrderItem` with `quantity`), `Discount` (percent or fixed minor units), `Tax` (percent, exclusive).
- `Order.total_price()` sums line totals, applies discount, then tax on the discounted base (integer minor units).
- Endpoints:
  - `GET /item/<id>/` — HTML product page + Stripe.js redirect to Checkout.
  - `GET /buy/<id>/` — JSON `{ "session_id": "cs_..." }`.
  - `GET /buy-intent/<id>/` — JSON `{ "client_secret": "pi_..." }`.
  - `POST /create-order/` — JSON body `{"items":[{"id":1,"quantity":2}], "discount_id": optional, "tax_id": optional}` → `{ "session_id": "cs_..." }`.
- Stripe logic lives in `apps/products/services.py` (API keys chosen by item/order currency).
- Admin UI for all models under `/admin/`.

## Prerequisites

- Python **3.11+**
- Optional: Docker / Docker Compose for Postgres-backed setup

## Local development (SQLite)

```powershell
cd test-oplati
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`: set `SECRET_KEY`, both Stripe **publishable/secret** pairs (`STRIPE_*` for RUB account, `STRIPE_*_EUR` for EUR account). Leave `DATABASE_URL` unset to use SQLite (`db.sqlite3`).

```powershell
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
python manage.py runserver
```

Open `http://localhost:8000/item/1/` (IDs depend on seed output). Click **Купить** — the browser requests `/buy/<id>/`, receives a Checkout `session_id`, and Stripe.js redirects to the hosted test payment page.

## Docker Compose (PostgreSQL)

Create `.env` from `.env.example` and fill Stripe keys and `SECRET_KEY`.

```powershell
docker compose up --build -d
```

- Web: `http://localhost:8000`
- Postgres: `localhost:5432` (user/password/db `oplati` — see `docker-compose.yml`)

Compose runs migrations, `seed_data`, and `runserver` with `DEBUG=True` so Django serves static files without extra setup.

## Tests

```powershell
pip install -r requirements.txt
pytest -v --cov=apps --cov=config --cov-report=term-missing --cov-fail-under=85
```

Configuration lives in `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`).

## Lint & types

```powershell
ruff check apps config
mypy apps/products
```

## Deploying on Render

1. Create a **PostgreSQL** instance on Render and note its internal URL.
2. Create a **Web Service** from this repo; build command can be `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`.
3. Start command (example): `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` (add **WhiteNoise** or serve static via CDN for production assets).
4. Set environment variables in the Render dashboard:
   - `SECRET_KEY`, `DEBUG=False`
   - `ALLOWED_HOSTS` including your Render hostname and `*.onrender.com` if applicable
   - `DATABASE_URL` from Render Postgres
   - `SITE_URL=https://<your-service>.onrender.com`
   - All four Stripe keys (`STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY_EUR`, `STRIPE_SECRET_KEY_EUR`)

Never commit real secrets; use Render **environment groups** or **secret files**.

## GitHub Actions

Workflow `.github/workflows/ci.yml` runs on pushes to `main` / `develop` and on PRs targeting `main`:

- **test** matrix on Python 3.11 and 3.12 against Postgres, migrations, pytest + coverage artifact.
- **lint** — `ruff` + `mypy`.
- **build-and-push** — on pushes to `main`, builds the Docker image and pushes to **GHCR** (`ghcr.io/<owner>/test-oplati`). Requires `GITHUB_TOKEN` permissions (`packages: write`).

## Security notes

- Stripe **secret** keys must only appear in environment variables / hosting secrets.
- Rotate any keys that were exposed in chat or tickets.
- Use strong `SECRET_KEY` and `DEBUG=False` in production.

## Команды для первого push в GitHub

Из корня проекта (после копирования файлов):

```powershell
git init
git add .
git commit -m "Initial Django Stripe commerce backend"
git branch -M main
git remote add origin https://github.com/Hnt899/test-oplati.git
git push -u origin main
```

Если репозиторий уже существует и не пустой, может понадобиться `git pull origin main --allow-unrelated-histories` перед первым push.
