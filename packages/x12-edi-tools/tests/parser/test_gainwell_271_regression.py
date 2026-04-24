"""Cross-layer regression gate for the Gainwell 271 fixture.

Locks the fix for the April 22, 2026 Gainwell 271 response so silent row loss
cannot recur. Fails if `parsed_result_count < source_transaction_count` on the
redacted fixture, or if any of the structural constructs covered by Phase P1
regress (composite EB03, 2120C NM1/PER, supplemental EB01, AAA 71/73/75).
"""

from __future__ import annotations

from pathlib import Path

from x12_edi_tools import parse
from x12_edi_tools.models.transactions import Transaction271

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE_PATH = FIXTURES / "gainwell_271_redacted.edi"

EXPECTED_TRANSACTIONS = 153
EXPECTED_AAA_71 = 4
EXPECTED_AAA_73 = 8
EXPECTED_AAA_75 = 1
EXPECTED_SUPPLEMENTAL_CODES = {"R", "L", "MC", "B"}


def _fixture_text() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _transactions() -> list[Transaction271]:
    result = parse(_fixture_text(), on_error="collect")
    assert result.errors == []
    transactions = [
        transaction
        for group in result.interchange.functional_groups
        for transaction in group.transactions
        if isinstance(transaction, Transaction271)
    ]
    return transactions


def test_parsed_result_count_matches_source_transaction_count() -> None:
    raw = _fixture_text()
    source = raw.count("ST*271*")

    result = parse(raw, on_error="collect")
    parsed = sum(
        1
        for group in result.interchange.functional_groups
        for transaction in group.transactions
        if isinstance(transaction, Transaction271)
    )

    assert source == EXPECTED_TRANSACTIONS
    assert parsed == source
    assert result.errors == []


def test_composite_eb03_is_split_on_repetition_separator() -> None:
    transactions = _transactions()
    eligibility_loop = transactions[0].loop_2000a.loop_2000b[0].loop_2000c[0].loop_2110c[0]
    eb_segment = eligibility_loop.eb_segments[0]

    assert len(eb_segment.service_type_codes) == 10
    assert eb_segment.service_type_code == eb_segment.service_type_codes[0]


def test_2120c_entity_and_per_contacts_are_attached() -> None:
    transactions = _transactions()
    eligibility_loop = transactions[0].loop_2000a.loop_2000b[0].loop_2000c[0].loop_2110c[0]
    entity_loop = eligibility_loop.loop_2120c[0]

    assert entity_loop.nm1.entity_identifier_code == "P5"
    assert entity_loop.ls.loop_identifier_code == "2120"
    assert entity_loop.le.loop_identifier_code == "2120"
    assert [per.communication_number_qualifier_1 for per in entity_loop.per_segments] == [
        "TE",
        "TE",
    ]


def test_supplemental_eb01_codes_survive_parse() -> None:
    transactions = _transactions()
    eb01_values = {
        transaction.loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
        .eb_segments[0]
        .eligibility_or_benefit_information
        for transaction in transactions
        if transaction.loop_2000a.loop_2000b[0].loop_2000c[0].loop_2110c
        and transaction.loop_2000a.loop_2000b[0].loop_2000c[0].loop_2110c[0].eb_segments
    }

    assert EXPECTED_SUPPLEMENTAL_CODES <= eb01_values


def test_aaa_rejection_codes_are_preserved_by_reject_reason_count() -> None:
    transactions = _transactions()
    counts: dict[str, int] = {}
    for transaction in transactions:
        subscriber = transaction.loop_2000a.loop_2000b[0].loop_2000c[0]
        aaa_segments = [
            *(subscriber.aaa_segments or []),
            *(getattr(subscriber.loop_2100c, "aaa_segments", None) or []),
        ]
        for aaa in aaa_segments:
            code = getattr(aaa, "reject_reason_code", None)
            if code is None:
                continue
            counts[str(code)] = counts.get(str(code), 0) + 1

    assert counts.get("71", 0) == EXPECTED_AAA_71
    assert counts.get("73", 0) == EXPECTED_AAA_73
    assert counts.get("75", 0) == EXPECTED_AAA_75
