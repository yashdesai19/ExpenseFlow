# ExpenseFlow Pro - Production Backend Architecture

A production-grade, enterprise-ready Expense Management API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Alembic**, **Pydantic v2**, and **JWT Authentication**.

---

## 🏗️ Clean Layered Architecture

```text
backend/
├── app/
│   ├── main.py               # FastAPI initialization, security headers, CORS, error handlers
│   ├── core/                 # Config (BaseSettings), Database engine, Security (Bcrypt & JWT)
│   ├── models/               # SQLAlchemy 2.0 ORM Declarative Models
│   ├── schemas/              # Pydantic v2 validation & response serialization contracts
│   ├── repositories/         # Data Access Layer (SQL queries, eager loading, aggregations)
│   ├── services/             # Business logic layer (Rules, calculations, audit logging)
│   ├── routers/              # RESTful API Endpoints organized by domain
│   ├── dependencies/         # Dependency Injection (get_db, get_current_user, get_current_active_user)
│   └── utils/                # Date formatting and helper utilities
│
├── alembic/                  # Database migration management & version history
├── tests/                    # Comprehensive automated pytest test suite (100% pass)
├── Dockerfile                # Production non-root Docker container image
├── docker-compose.yml        # Orchestration with PostgreSQL 16
├── requirements.txt          # Pinned Python package dependencies
├── .env.example              # Environment variables template
└── README.md                 # Engineering documentation & API handbook
```

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+
- PostgreSQL 15+ running locally (or Docker)

### 2. Environment Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Run Database Migrations
```powershell
.\.venv\Scripts\alembic upgrade head
```

### 4. Start Development Server
```powershell
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

- **Interactive API Docs (Swagger UI):** [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc)
- **Health Check Endpoint:** [http://127.0.0.1:8080/api/v1/health](http://127.0.0.1:8080/api/v1/health)

---

## 🧪 Running Automated Tests

Run the full pytest test suite:
```powershell
.\.venv\Scripts\pytest -v
```

---

## 🐳 Docker Deployment

Run the complete multi-container stack (FastAPI + PostgreSQL) with a single command:

```powershell
docker compose up --build -d
```

To stop:
```powershell
docker compose down
```

---

## 📚 RESTful API Summary

| Domain | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Health** | `GET` | `/api/v1/health` | Service uptime and version probe |
| **Auth** | `POST` | `/api/v1/auth/register` | Register new user + auto-seed categories |
| **Auth** | `POST` | `/api/v1/auth/login` | Authenticate and receive JWT token |
| **Auth** | `POST` | `/api/v1/auth/token` | OAuth2 form-data login for Swagger UI |
| **Auth** | `GET` | `/api/v1/auth/me` | Get authenticated user profile |
| **Categories** | `GET` | `/api/v1/categories` | List user custom + default categories |
| **Categories** | `POST` | `/api/v1/categories` | Create custom category |
| **Categories** | `PATCH`| `/api/v1/categories/{id}` | Update category |
| **Categories** | `DELETE`| `/api/v1/categories/{id}`| Delete category (protected if in use) |
| **Expenses** | `GET` | `/api/v1/expenses` | Paginated search, filter & sort expenses |
| **Expenses** | `POST` | `/api/v1/expenses` | Create new expense |
| **Expenses** | `GET` | `/api/v1/expenses/{id}` | Get single expense |
| **Expenses** | `PATCH`| `/api/v1/expenses/{id}` | Update expense |
| **Expenses** | `DELETE`| `/api/v1/expenses/{id}`| Delete expense |
| **Budgets** | `GET` | `/api/v1/budgets` | List budgets with real-time % utilization |
| **Budgets** | `POST` | `/api/v1/budgets` | Set monthly category spending limit |
| **Dashboard** | `GET` | `/api/v1/dashboard/summary` | Consolidated KPIs, charts & breakdowns |
| **Reports** | `GET` | `/api/v1/reports/spending` | Custom date-range financial report |
| **Reports** | `GET` | `/api/v1/reports/monthly-trends` | 6/12-month spending trend series |
| **Recurring** | `GET` | `/api/v1/recurring` | List active subscriptions/schedules |
| **Recurring** | `POST` | `/api/v1/recurring` | Create recurring expense schedule |
| **Recurring** | `POST` | `/api/v1/recurring/process` | Batch generate due expenses |
| **Audit Logs**| `GET` | `/api/v1/audit-logs` | Chronological immutable compliance log |
| **Settings** | `GET` | `/api/v1/settings` | Get user currency & theme preferences |
| **Settings** | `PATCH`| `/api/v1/settings` | Update preferences |
