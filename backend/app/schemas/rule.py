from __future__ import annotations

from pydantic import BaseModel, Field


class RuleConditionSchema(BaseModel):
    id: int
    condition_type: str
    value: str

    model_config = {"from_attributes": True}


class RuleConditionCreate(BaseModel):
    condition_type: str = Field(..., pattern="^(extension|tracker)$")
    value: str = Field(..., min_length=1)


class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1)
    priority: int = Field(default=100, ge=1)
    enabled: bool = True
    dry_run: bool = False
    require_complete: bool = False
    destination: str = Field(..., min_length=1)
    conditions: list[RuleConditionCreate] = Field(default_factory=list)


class RulePatch(BaseModel):
    name: str | None = None
    priority: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    dry_run: bool | None = None
    require_complete: bool | None = None
    destination: str | None = None
    conditions: list[RuleConditionCreate] | None = None


class RuleSchema(BaseModel):
    id: int
    name: str
    priority: int
    enabled: bool
    dry_run: bool
    require_complete: bool
    destination: str
    conditions: list[RuleConditionSchema]

    model_config = {"from_attributes": True}


class PreviewTorrent(BaseModel):
    hash: str
    name: str
    save_path: str


class PreviewResponse(BaseModel):
    total_torrents: int
    matched: list[PreviewTorrent]


class PreviewEvalRequest(BaseModel):
    conditions: list[RuleConditionCreate] = Field(default_factory=list)
