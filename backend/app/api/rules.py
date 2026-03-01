"""Rules CRUD API."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rule import Rule, RuleCondition
from app.models.setting import Setting
from app.schemas.rule import (
    PreviewEvalRequest,
    PreviewResponse,
    PreviewTorrent,
    RuleCreate,
    RulePatch,
    RuleSchema,
)
from app.services.deluge import DelugeClient
from app.services.engine import evaluate_rule

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rules", tags=["rules"])

_RPC_TIMEOUT = 5.0


async def _settings_dict(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(select(Setting))
    return {s.key: s.value for s in result.scalars().all()}


async def _connect_and_get_torrents(settings: dict[str, str]) -> list:  # type: ignore[type-arg]
    host = settings.get("deluge_host", "")
    if not host:
        raise HTTPException(status_code=503, detail="Deluge host not configured.")
    port_str = settings.get("deluge_port", "58846")
    try:
        port = int(port_str)
    except ValueError as err:
        raise HTTPException(
            status_code=503, detail=f"Invalid port: {port_str!r}"
        ) from err
    client = DelugeClient(
        host=host,
        port=port,
        username=settings.get("deluge_username", ""),
        password=settings.get("deluge_password", ""),
    )
    try:
        await asyncio.wait_for(client.connect(), timeout=_RPC_TIMEOUT)
        torrents = await client.get_torrents()
        await client.disconnect()
        return torrents
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc)
        password = settings.get("deluge_password", "")
        if password:
            msg = msg.replace(password, "***")
        raise HTTPException(status_code=503, detail=msg) from exc


def _rule_to_schema(rule: Rule) -> RuleSchema:
    return RuleSchema.model_validate(rule)


async def _get_rule_or_404(rule_id: int, db: AsyncSession) -> Rule:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found.")
    return rule


@router.get("", response_model=list[RuleSchema])
async def list_rules(db: AsyncSession = Depends(get_db)) -> list[RuleSchema]:
    """Return all rules ordered by priority ascending."""
    result = await db.execute(select(Rule).order_by(Rule.priority, Rule.id))
    rules = result.scalars().all()
    return [_rule_to_schema(r) for r in rules]


@router.post("", response_model=RuleSchema, status_code=201)
async def create_rule(
    body: RuleCreate, db: AsyncSession = Depends(get_db)
) -> RuleSchema:
    rule = Rule(
        name=body.name,
        priority=body.priority,
        enabled=body.enabled,
        dry_run=body.dry_run,
        require_complete=body.require_complete,
        destination=body.destination.rstrip("/"),
    )
    db.add(rule)
    await db.flush()  # populate rule.id before adding conditions
    for cond in body.conditions:
        db.add(
            RuleCondition(
                rule_id=rule.id,
                condition_type=cond.condition_type,
                value=cond.value,
            )
        )
    await db.commit()
    await db.refresh(rule)
    logger.info("Created rule %r (id=%s)", rule.name, rule.id)
    return _rule_to_schema(rule)


@router.patch("/{rule_id}", response_model=RuleSchema)
async def update_rule(
    rule_id: int, body: RulePatch, db: AsyncSession = Depends(get_db)
) -> RuleSchema:
    rule = await _get_rule_or_404(rule_id, db)
    if body.name is not None:
        rule.name = body.name
    if body.priority is not None:
        rule.priority = body.priority
    if body.enabled is not None:
        rule.enabled = body.enabled
    if body.dry_run is not None:
        rule.dry_run = body.dry_run
    if body.require_complete is not None:
        rule.require_complete = body.require_complete
    if body.destination is not None:
        rule.destination = body.destination.rstrip("/")
    if body.conditions is not None:
        # Replace all conditions
        for existing in list(rule.conditions):
            await db.delete(existing)
        for new_cond in body.conditions:
            db.add(
                RuleCondition(
                    rule_id=rule.id,
                    condition_type=new_cond.condition_type,
                    value=new_cond.value,
                )
            )
    await db.commit()
    await db.refresh(rule)
    logger.info("Updated rule %s", rule_id)
    return _rule_to_schema(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    rule = await _get_rule_or_404(rule_id, db)
    await db.delete(rule)
    await db.commit()
    logger.info("Deleted rule %s", rule_id)


# ── Preview endpoints ────────────────────────────────────────────────────────
# POST /rules/preview must be defined before GET /rules/{rule_id}/preview
# to prevent "preview" being parsed as a rule_id.


@router.post("/preview", response_model=PreviewResponse)
async def preview_eval(
    body: PreviewEvalRequest, db: AsyncSession = Depends(get_db)
) -> PreviewResponse:
    """Evaluate ad-hoc conditions against live Deluge torrents."""
    settings = await _settings_dict(db)
    torrents = await _connect_and_get_torrents(settings)

    # Build a temporary in-memory rule to reuse evaluate_rule()
    temp_rule = Rule(id=0, name="", priority=0, enabled=True, destination="")
    temp_rule.conditions = [
        RuleCondition(condition_type=c.condition_type, value=c.value)
        for c in body.conditions
    ]

    matched = [
        PreviewTorrent(hash=t.hash, name=t.name, save_path=t.save_path)
        for t in torrents
        if evaluate_rule(temp_rule, t)
    ]
    return PreviewResponse(total_torrents=len(torrents), matched=matched)


@router.get("/{rule_id}/preview", response_model=PreviewResponse)
async def preview_rule(
    rule_id: int, db: AsyncSession = Depends(get_db)
) -> PreviewResponse:
    """Preview which live torrents the saved rule would match."""
    rule = await _get_rule_or_404(rule_id, db)
    settings = await _settings_dict(db)
    torrents = await _connect_and_get_torrents(settings)

    matched = [
        PreviewTorrent(hash=t.hash, name=t.name, save_path=t.save_path)
        for t in torrents
        if t.save_path.rstrip("/") != rule.destination.rstrip("/")
        and evaluate_rule(rule, t)
    ]
    return PreviewResponse(total_torrents=len(torrents), matched=matched)
