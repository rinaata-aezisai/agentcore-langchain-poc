"""FastAPI Main Application"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import agents, health, sessions
from api.routers.services import (
    browser,
    code_interpreter,
    evaluations,
    gateway,
    identity,
    memory,
    observability,
    policy,
    runtime,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    yield
    print("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent API",
        description="AgentCore / LangChain PoC API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Core routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
    app.include_router(agents.router, prefix="/agents", tags=["Agents"])

    # Service-specific routers
    app.include_router(
        runtime.router, prefix="/services/runtime", tags=["Services", "Runtime"]
    )
    app.include_router(
        memory.router, prefix="/services/memory", tags=["Services", "Memory"]
    )
    app.include_router(
        gateway.router, prefix="/services/gateway", tags=["Services", "Gateway"]
    )
    app.include_router(
        identity.router, prefix="/services/identity", tags=["Services", "Identity"]
    )
    app.include_router(
        code_interpreter.router,
        prefix="/services/code-interpreter",
        tags=["Services", "Code Interpreter"],
    )
    app.include_router(
        browser.router, prefix="/services/browser", tags=["Services", "Browser"]
    )
    app.include_router(
        observability.router,
        prefix="/services/observability",
        tags=["Services", "Observability"],
    )
    app.include_router(
        evaluations.router,
        prefix="/services/evaluations",
        tags=["Services", "Evaluations"],
    )
    app.include_router(
        policy.router, prefix="/services/policy", tags=["Services", "Policy"]
    )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)


