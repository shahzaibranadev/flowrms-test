from fastapi import FastAPI
from app.core.database import engine, Base
from app.api.rest import api_router
from app.api.graphql.router import graphql_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Invoice Reconciliation API",
    description="Multi-tenant invoice reconciliation API with REST and GraphQL",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api")
app.include_router(graphql_router, prefix="/graphql")


@app.get("/")
def root():
    return {"message": "Invoice Reconciliation API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
