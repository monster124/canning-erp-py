"""Canning ERP - async FastAPI backend for canned-food production.

Layered (Clean Architecture):

- ``domain``         - entities, business rules, ports (zero external imports)
- ``application``    - use-cases, depends only on domain + ports
- ``infrastructure`` - SQLAlchemy/asyncpg, Redis, JWT, argon2, export adapters
- ``interfaces``     - FastAPI routers, middleware, DTOs
"""

__version__ = "0.1.0"
