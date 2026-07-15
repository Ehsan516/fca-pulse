import pytest
from pydantic import ValidationError

from fca_pulse.classify.schema import ClassificationResult


def valid_payload(**overrides):
    payload = {
        "document_type": "Policy Statement",
        "regulation_areas": ["Consumer Duty"],
        "affected_firm_types": ["Banks"],
        "summary": "A short plain-English summary.",
        "key_deadlines": [{"date": "2026-12-01", "description": "Implementation deadline"}],
        "impact_level": "action-required",
    }
    payload.update(overrides)
    return payload


def test_valid_payload_parses():
    result = ClassificationResult.model_validate(valid_payload())
    assert result.document_type == "Policy Statement"
    assert result.key_deadlines[0].date == "2026-12-01"


def test_invalid_document_type_rejected():
    with pytest.raises(ValidationError):
        ClassificationResult.model_validate(valid_payload(document_type="Not A Real Type"))


def test_invalid_regulation_area_rejected():
    with pytest.raises(ValidationError):
        ClassificationResult.model_validate(valid_payload(regulation_areas=["Made Up Category"]))


def test_invalid_affected_firm_type_rejected():
    with pytest.raises(ValidationError):
        ClassificationResult.model_validate(valid_payload(affected_firm_types=["Space Firms"]))


def test_invalid_impact_level_rejected():
    with pytest.raises(ValidationError):
        ClassificationResult.model_validate(valid_payload(impact_level="urgent"))


def test_ambiguous_deadline_date_rejected():
    with pytest.raises(ValidationError):
        ClassificationResult.model_validate(
            valid_payload(key_deadlines=[{"date": "sometime in Q3", "description": "vague"}])
        )


def test_summary_over_80_words_is_trimmed_not_rejected():
    long_summary = " ".join(["word"] * 120)
    result = ClassificationResult.model_validate(valid_payload(summary=long_summary))
    assert len(result.summary.split()) == 80
