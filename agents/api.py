"""
FastAPI REST API Server for Mipi Mantle Cell Calculator.
"""
import hmac
import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Mipi Mantle Cell Calculator API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "mipi-mantle-cell-calculator", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


def require_legacy_token(x_audit_token: str | None = Header(default=None)):
    """Do not expose mock supervisor workflows or audit metadata unauthenticated."""
    expected = os.getenv("AUDIT_API_TOKEN")
    if not expected or not x_audit_token or not hmac.compare_digest(x_audit_token, expected):
        raise HTTPException(status_code=403, detail="Legacy supervisor API requires X-Audit-Token")


@app.post("/api/audit", dependencies=[Depends(require_legacy_token)])
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat", dependencies=[Depends(require_legacy_token)])
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs", dependencies=[Depends(require_legacy_token)])
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}


# Clinical prognostic scoring is separate from the legacy diagnostic supervisor.
class MIPIRequest(BaseModel):
    age: float
    ecog: int
    wbc: float  # 10^9/L
    ldh: float | None = None
    ldh_uln: float | None = None
    ldh_ratio: float | None = None
    ki67: float | None = None


@app.post("/api/mipi")
def api_mipi(request: MIPIRequest):
    from mipi_calc import calculate_metrics
    try:
        return calculate_metrics(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
