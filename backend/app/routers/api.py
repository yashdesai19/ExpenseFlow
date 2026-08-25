from fastapi import APIRouter
from app.routers import (
    health,
    auth,
    categories,
    expenses,
    budgets,
    dashboard,
    reports,
    recurring,
    audit,
    settings,
    groups,
)

api_router = APIRouter()

# Register core feature routers
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(expenses.router)
api_router.include_router(budgets.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(recurring.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(groups.router)
