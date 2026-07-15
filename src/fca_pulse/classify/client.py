"""ai-powered classification client"""

import logging

import anthropic
from pydantic import ValidationError

from fca_pulse.classify.schema import ClassificationResult
from fca_pulse.config import load_prompt_template, load_vocab

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_RAW_TEXT_CHARS = 12000

TOOL_SCHEMA = {
    "name": "classify_publication",
    "description": "Classify a UK FCA/PRA regulatory publication into the structured schema.",
    "input_schema": {
        "type": "object",
        "properties": {

            "document_type": {"type": "string"},
            "regulation_areas": {"type": "array", "items": {"type": "string"}},
            "affected_firm_types": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
            "key_deadlines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                        "description": {"type": "string"},
                    },
                    "required": ["date", "description"],
                },
            },
            "impact_level": {
                "type": "string",
                "enum": ["informational", "action-recommended", "action-required"],
            },
        },
        "required": [
            "document_type",
            "regulation_areas",
            "affected_firm_types",
            "summary",
            "key_deadlines",
            "impact_level",

        ],

    },
}

_FAILED_RESULT_TEMPLATE = {
    "document_type": None,
    "regulation_areas": [],
    "affected_firm_types": [],
    "summary": None,
    "key_deadlines": [],
    "impact_level": None,
}


def build_prompt(item: dict) -> str:
    vocab = load_vocab()
    template = load_prompt_template("classify.md")
    return template.format(
        document_types=", ".join(vocab["document_types"]),
        regulation_areas=", ".join(vocab["regulation_areas"]),
        affected_firm_types=", ".join(vocab["affected_firm_types"]),
        title=item["title"],
        source=item["source"],
        url=item["url"],
        published_date=item.get("published_date") or "unknown",
        raw_text=(item.get("raw_text") or "")[:MAX_RAW_TEXT_CHARS],
    )


def _call_claude(client: anthropic.Anthropic, prompt: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "classify_publication"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "classify_publication":
            return block.input
    raise ValueError("Claude response did not include a classify_publication tool call")


def classify_item(client: anthropic.Anthropic, item: dict) -> dict:
    """classify an ingested item against the schema.
    On success returns validated classification fields. If the model's
    output fails schema validation, it retries. If it still fails, returns
    a `classification_failed=True` record instead of raising so the item is
    stored"""
    prompt = build_prompt(item)
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            raw = _call_claude(client, prompt)
            result = ClassificationResult.model_validate(raw)
            data = result.model_dump()
            data["classification_failed"] = False
            data["classification_error"] = None
            return data
        except (ValidationError, ValueError, anthropic.APIError) as exc:
            last_error = exc
            logger.warning(
                "Classification attempt %d failed for %s: %s", attempt + 1, item["url"], exc
            )

    logger.error("Classification failed for %s after retry: %s", item["url"], last_error)
    return {
        **_FAILED_RESULT_TEMPLATE,
        "classification_failed": True,
        "classification_error": str(last_error),
    }
