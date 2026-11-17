from fastapi import FastAPI

from expense_tracker.api.exception_handlers import register_exception_handlers
from expense_tracker.api.lifespan import lifespan
from expense_tracker.api.middleware.auth import AuthMiddleware
from expense_tracker.api.middleware.csrf import CSRFMiddleware
from expense_tracker.api.paths import API_PREFIX
from expense_tracker.api.routes import (
    accounts,
    auth,
    budgets,
    categories,
    csv_imports,
    health,
    recurring_transactions,
    reports,
    tags,
    transactions,
)

app = FastAPI(lifespan=lifespan)

app.add_middleware(AuthMiddleware)
app.add_middleware(CSRFMiddleware)

register_exception_handlers(app)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(accounts.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(tags.router, prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(csv_imports.router, prefix=API_PREFIX)
app.include_router(budgets.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(recurring_transactions.router, prefix=API_PREFIX)
