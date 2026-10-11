# SmartLedger Backend

SmartLedger Backend is a Django REST API that powers authentication, expenses, vehicle/order workflows, transactions, reporting, and PDF/Excel exports for Smart Ledger.

## Repository

- Backend repo: `SmartLedger-Backend`
- Paired frontend repo: `Smart-Ledger`

## Tech Stack

- Python 3
- Django 4.2
- Django REST Framework
- DRF Token Authentication
- SQLite (default)
- ReportLab (PDF generation)
- OpenPyXL (Excel import/export)
- django-cors-headers

## Apps Overview

- `apps.account`: user model, login/logout, profile management.
- `apps.expense`: expense categories, expenses, restaurants, spare parts/shops, receipt and expense PDF exports.
- `apps.revenue`: cars and categories, orders and order items, customers/salers, auctions, company accounts, transactions, invoices, reports, and translation endpoints.

## Authentication

- Token-based authentication (`Authorization: Token <token>`)
- Login endpoint returns token and user info.
- Protected endpoints require authenticated user context and return user-scoped data.

## Base API Routes

- `/api/account/`
- `/api/`
- `/api/revenue/`

## Key Endpoints

### Account

- `POST /api/account/login/`
- `POST /api/account/logout/`
- `GET/PATCH /api/account/profile/`

### Expense

- `GET/POST /api/categories/`
- `GET /api/categories/all/`
- `GET/POST /api/expenses/`
- `GET /api/expenses/search_titles/`
- `GET /api/expenses/available_transactions/`
- `GET /api/expenses/{id}/generate_receipt/`
- `GET /api/expenses/export_pdf/`
- `POST /api/expenses/bulk-import-xls-expenses/`
- `POST /api/expenses/bulk-import/` (expense + transaction import, see below)
- `GET /api/expenses/bulk-import/` (status of the latest import)
- `GET /api/expenses/bulk-import/template/`
- `GET/POST /api/restaurants/`
- `GET/POST /api/spare-parts/`

### Revenue

- `GET/POST /api/revenue/categories/`
- `GET /api/revenue/categories/all/`
- `POST /api/revenue/categories/bulk-import/`
- `GET/POST /api/revenue/cars/`
- `GET/POST /api/revenue/orders/`
- `POST /api/revenue/orders/create_with_items/`
- `POST /api/revenue/orders/{id}/update_with_items/`
- `GET /api/revenue/orders/dashboard/`
- `GET /api/revenue/orders/{id}/generate_invoice/`
- `GET /api/revenue/orders/reports/`
- `GET /api/revenue/orders/financial_report/`
- `GET/POST /api/revenue/customers/`
- `GET/POST /api/revenue/salers/`
- `GET/POST /api/revenue/company-accounts/`
- `GET/POST /api/revenue/auctions/`
- `POST /api/revenue/auctions/bulk-import/`
- `GET/POST /api/revenue/transactions/`
- `POST /api/revenue/transactions/bulk_import/`
- `POST /api/revenue/translate/`
- `POST /api/revenue/translate-batch/`

## Local Development Setup

### Prerequisites

- Python 3.10+ recommended
- `pip`

### Install & Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Default API URL: `http://127.0.0.1:8000`

## Bulk Expense + Transaction Import

`POST /api/expenses/bulk-import/` takes a multipart form with `file` (.xlsx) and `company_account`.

Required columns (any order, header case ignored): Date, Transaction ID, Withdraw Amount, Deposit Amount,
Description, Notes, Title, Category, Tax Way, Tax Rate.

- Every row needs Date, Transaction ID, Description, Notes and exactly one of Withdraw / Deposit.
- Withdraw rows also need Title, Category, Tax Way (`inclusive` / `exclusive`, any case) and Tax Rate
  (`10`, `10%`). They create a transaction and an expense; tax is calculated like a manual expense.
- Deposit rows create a transaction only. Their expense columns may be blank.
- Unknown categories are created.

The whole file is validated first. If anything is wrong the response is `400` with `row_errors` and
nothing is saved. Otherwise the response is `202` and a Celery task writes everything in one database
transaction: the import is complete or it leaves nothing behind. Rows are matched one-to-one on
date + transaction id + amounts, so uploading the same file again creates nothing.

Only one import per user can be active; a second upload returns `409`. Poll `GET /api/expenses/bulk-import/`
for `status` (`pending`, `running`, `completed`, `failed`), `percent`, `result` and `error`.

### Background worker

The import needs Redis and a Celery worker. `docker compose up` starts both. Locally:

```bash
redis-server
celery -A project worker --loglevel=info --pool=solo   # --pool=solo is only needed on Windows
```

Or set `CELERY_TASK_ALWAYS_EAGER=True` in `.env` to run imports inline with no Redis or worker.

## Create Users (Custom Commands)

```bash
python manage.py createuser <username> <email> <password>
python manage.py createsuperuser_custom <username> <email> <password>
```

## Important Notes

- Default DB is SQLite (`db.sqlite3`).
- CORS and trusted origins are configured in `project/settings.py`.
- Global pagination uses custom page size with `pageSize` query param.

License
This project is open-source under the MIT License, unless specified otherwise.

Contact
For any questions or suggestions, feel free to reach out:

Email: huzaifanasirbutt@gmail.com
LinkedIn: Huzaifa Nasir
