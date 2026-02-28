"""Rules CRUD API."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.rule import Rule, RuleCondition
from app.schemas.rule import RuleCreate, RulePatch, RuleSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rules", tags=["rules"])


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
        destination=body.destination,
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
    if body.destination is not None:
        rule.destination = body.destination
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
