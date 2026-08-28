"""Audit log endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit_log import AuditLog


router = APIRouter()


@router.get("/audit-logs")
async def get_audit_logs(
    db: Session = Depends(get_db),
) -> List[dict]:
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return [
        {
            "id": log.id,
            "agent_name": log.agent_name,
            "action": log.action,
            "input_payload": log.input_payload,
            "output_payload": log.output_payload,
            "human_verified": log.human_verified,
            "verified_by": log.verified_by,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]