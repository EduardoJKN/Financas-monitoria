from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router_v1
from app.core.config import frontend_url
from app.core.erros import registrar_handlers_erro
from app.core.timing import TimingMiddleware

app = FastAPI(
    title="Economia UaU — API",
    description=(
        "API REST para o App Finanças. Reaproveita a camada de negócio de "
        "finance_app/src — não duplica regras financeiras."
    ),
    version="1.0.0",
)

# CORS: só a origem do frontend configurado — nunca "*" com rotas
# autenticadas (Parte 39).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TimingMiddleware)

registrar_handlers_erro(app)

app.include_router(router_v1)


@app.get("/health", tags=["Infraestrutura"])
def health() -> dict:
    return {"status": "ok"}
