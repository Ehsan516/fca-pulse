from datetime import date as date_cls

from pydantic import BaseModel, Field, field_validator

from fca_pulse.config import load_vocab

_VOCAB = load_vocab()


class Deadline(BaseModel):
    date: str  # YYYY-MM-DD
    description: str

    @field_validator("date")
    @classmethod
    def date_is_iso(cls, v):
        date_cls.fromisoformat(v)  # blows up if it's not a real ISO date
        return v


class ClassificationResult(BaseModel):
    document_type: str
    regulation_areas: list[str] = Field(default_factory=list)
    affected_firm_types: list[str] = Field(default_factory=list)
    summary: str
    key_deadlines: list[Deadline] = Field(default_factory=list)
    impact_level: str

    @field_validator("document_type")
    @classmethod
    def document_type_in_vocab(cls, v):
        if v not in _VOCAB["document_types"]:
            raise ValueError(f"document_type {v!r} is not in the controlled vocabulary")
        return v

    @field_validator("regulation_areas")
    @classmethod
    def regulation_areas_in_vocab(cls, v):
        for area in v:
            if area not in _VOCAB["regulation_areas"]:
                raise ValueError(f"regulation_areas contains invalid values: {v}")
        return v

    @field_validator("affected_firm_types")
    @classmethod
    def firm_types_in_vocab(cls, v):
        invalid = set(v) - set(_VOCAB["affected_firm_types"])
        if invalid:
            raise ValueError(f"affected_firm_types contains invalid values: {sorted(invalid)}")
        return v

    @field_validator("impact_level")
    @classmethod
    def impact_level_in_vocab(cls, v):
        if v not in _VOCAB["impact_levels"]:
            raise ValueError(f"impact_level {v!r} is not in the controlled vocabulary")
        return v

    @field_validator("summary")
    @classmethod
    def summary_at_most_80_words(cls, v):
        words = v.split()
        if len(words) > 80:
            v = " ".join(words[:80])
        return v
