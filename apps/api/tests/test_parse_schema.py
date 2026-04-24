from __future__ import annotations

from app.schemas.parse import ParseResponse


def test_parse_response_transaction_count_is_runtime_deprecated() -> None:
    field = ParseResponse.model_fields["transaction_count"]
    schema = ParseResponse.model_json_schema()

    assert field.deprecated == "Use source_transaction_count"
    assert schema["properties"]["transaction_count"]["deprecated"] is True
