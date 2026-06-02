from __future__ import annotations

try:
    from fastapi import Depends, FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - dependency guard for environments without FastAPI
    Depends = FastAPI = HTTPException = BaseModel = Field = HTMLResponse = None  # type: ignore[assignment]

from PoC1.app.psi_service import PsiQueryService
from PoC1.app.ui import render_homepage


if BaseModel is not None:
    class QueryRequest(BaseModel):
        question: str = Field(..., min_length=1, description="Korean natural-language PSI question")

else:  # pragma: no cover
    class QueryRequest:  # type: ignore[no-redef]
        pass


def create_app(service: PsiQueryService | None = None):
    if FastAPI is None:
        raise RuntimeError("fastapi package is required")

    app = FastAPI(
        title="PSI Chatbot PoC API",
        description="Natural-language query API for GSCM PSI data converted to DuckDB long-form tables.",
        version="0.1.0",
    )
    query_service = service or PsiQueryService()

    def get_service() -> PsiQueryService:
        return query_service

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return render_homepage()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/schema")
    def schema(current_service: PsiQueryService = Depends(get_service)):
        try:
            return current_service.schema_summary()
        except Exception as exc:  # pragma: no cover - API error mapping
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/query")
    def query(request: QueryRequest, current_service: PsiQueryService = Depends(get_service)):
        try:
            return current_service.query(request.question).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - API error mapping
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


app = create_app()
