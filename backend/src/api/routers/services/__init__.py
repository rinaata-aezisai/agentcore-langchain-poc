"""Service Routers

AgentCoreの9サービスに対応したAPIルーター。
"""

from fastapi import APIRouter

from . import runtime
from . import memory
from . import gateway
from . import identity
from . import code_interpreter
from . import browser
from . import observability
from . import evaluations
from . import policy

# 統合ルーター
services_router = APIRouter(prefix="/services", tags=["Services"])

services_router.include_router(runtime.router)
services_router.include_router(memory.router)
services_router.include_router(gateway.router)
services_router.include_router(identity.router)
services_router.include_router(code_interpreter.router)
services_router.include_router(browser.router)
services_router.include_router(observability.router)
services_router.include_router(evaluations.router)
services_router.include_router(policy.router)

__all__ = [
    "services_router",
    "runtime",
    "memory",
    "gateway",
    "identity",
    "code_interpreter",
    "browser",
    "observability",
    "evaluations",
    "policy",
]

