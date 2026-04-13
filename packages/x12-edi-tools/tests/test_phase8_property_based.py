from __future__ import annotations

import logging
import string

import pytest
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from test_phase1_models import build_interchange, build_transaction_270
from x12_edi_tools import Delimiters, encode, parse
from x12_edi_tools.common.enums import ServiceTypeCode
from x12_edi_tools.common.types import SegmentToken
from x12_edi_tools.parser.isa_parser import detect_delimiters
from x12_edi_tools.parser.tokenizer import tokenize

_DELIMITER_POOL = ["*", "|", "!", "~", "^", ":", ";", "%", "+"]
_ELEMENT_TEXT = string.ascii_uppercase + string.digits
_NAME_TEXT = string.ascii_uppercase


@st.composite
def delimiter_strategy(draw) -> Delimiters:
    chosen = draw(st.lists(st.sampled_from(_DELIMITER_POOL), min_size=4, max_size=4, unique=True))
    return Delimiters(
        element=chosen[0],
        segment=chosen[1],
        sub_element=chosen[2],
        repetition=chosen[3],
    )


@st.composite
def segment_tokens_strategy(draw) -> list[SegmentToken]:
    token_count = draw(st.integers(min_value=1, max_value=8))
    tokens: list[SegmentToken] = []
    for index in range(token_count):
        segment_id = draw(st.text(alphabet=string.ascii_uppercase, min_size=2, max_size=3))
        elements = draw(
            st.lists(
                st.text(alphabet=_ELEMENT_TEXT, min_size=0, max_size=6),
                min_size=0,
                max_size=5,
            )
        )
        tokens.append(
            SegmentToken(
                segment_id=segment_id,
                elements=tuple(elements),
                position=index,
            )
        )
    return tokens


@st.composite
def interchange_strategy(draw: st.DrawFn):
    transaction_count = draw(st.integers(min_value=1, max_value=3))
    delimiters = draw(delimiter_strategy())
    isa_control_number = draw(st.integers(min_value=1, max_value=999_999_999))
    group_control_number = draw(st.integers(min_value=1, max_value=999_999))
    service_type_code = draw(st.sampled_from(["1", "30", "47", "98"]))

    transactions = []
    for index in range(1, transaction_count + 1):
        base_transaction = build_transaction_270()
        subscriber_loop = base_transaction.loop_2000a.loop_2000b[0].loop_2000c[0]
        subscriber_name = draw(st.text(alphabet=_NAME_TEXT, min_size=3, max_size=10))
        first_name = draw(st.text(alphabet=_NAME_TEXT, min_size=3, max_size=10))
        member_id = draw(st.text(alphabet=string.digits, min_size=8, max_size=12))
        date_of_birth = draw(st.dates()).strftime("%Y%m%d")
        service_date = draw(st.dates()).strftime("%Y%m%d")

        updated_subscriber = subscriber_loop.model_copy(
            update={
                "trn": subscriber_loop.trn.model_copy(
                    update={"reference_identification_1": f"TRACE{index:04d}"}
                ),
                "loop_2100c": subscriber_loop.loop_2100c.model_copy(
                    update={
                        "nm1": subscriber_loop.loop_2100c.nm1.model_copy(
                            update={
                                "last_name": subscriber_name,
                                "first_name": first_name,
                                "id_code": member_id,
                            }
                        ),
                        "dmg": subscriber_loop.loop_2100c.dmg.model_copy(
                            update={"date_time_period": date_of_birth}
                        ),
                    }
                ),
                "loop_2110c": [
                    subscriber_loop.loop_2110c[0].model_copy(
                        update={
                            "dtp_segments": [
                                subscriber_loop.loop_2110c[0]
                                .dtp_segments[0]
                                .model_copy(update={"date_time_period": service_date})
                            ],
                            "eq_segments": [
                                subscriber_loop.loop_2110c[0]
                                .eq_segments[0]
                                .model_copy(
                                    update={"service_type_code": ServiceTypeCode(service_type_code)}
                                )
                            ],
                        }
                    )
                ],
            }
        )
        updated_receiver = base_transaction.loop_2000a.loop_2000b[0].model_copy(
            update={"loop_2000c": [updated_subscriber]}
        )
        transactions.append(
            base_transaction.model_copy(
                update={
                    "st": base_transaction.st.model_copy(
                        update={"transaction_set_control_number": f"{index:04d}"}
                    ),
                    "bht": base_transaction.bht.model_copy(
                        update={
                            "reference_identification": f"{10_000_000 + index}",
                            "date": service_date,
                        }
                    ),
                    "loop_2000a": base_transaction.loop_2000a.model_copy(
                        update={"loop_2000b": [updated_receiver]}
                    ),
                    "se": base_transaction.se.model_copy(
                        update={
                            "number_of_included_segments": 13,
                            "transaction_set_control_number": f"{index:04d}",
                        }
                    ),
                }
            )
        )

    base_interchange = build_interchange()
    functional_group = base_interchange.functional_groups[0].model_copy(
        update={
            "gs": base_interchange.functional_groups[0].gs.model_copy(
                update={"group_control_number": str(group_control_number)}
            ),
            "transactions": transactions,
            "ge": base_interchange.functional_groups[0].ge.model_copy(
                update={
                    "number_of_transaction_sets_included": len(transactions),
                    "group_control_number": str(group_control_number),
                }
            ),
        }
    )
    return base_interchange.model_copy(
        update={
            "isa": base_interchange.isa.model_copy(
                update={
                    "interchange_control_number": f"{isa_control_number:09d}",
                    "repetition_separator": delimiters.repetition,
                    "component_element_separator": delimiters.sub_element,
                }
            ),
            "functional_groups": [functional_group],
            "iea": base_interchange.iea.model_copy(
                update={
                    "number_of_included_functional_groups": 1,
                    "interchange_control_number": f"{isa_control_number:09d}",
                }
            ),
            "delimiters": delimiters,
        }
    )


@hypothesis_settings(deadline=None, max_examples=40)
@given(delimiters=delimiter_strategy(), tokens=segment_tokens_strategy())
def test_property_tokenize_preserves_segment_boundaries_and_empty_elements(
    delimiters: Delimiters,
    tokens: list[SegmentToken],
) -> None:
    raw = "".join(
        delimiters.element.join([token.segment_id, *token.elements]) + delimiters.segment
        for token in tokens
    )

    parsed = tokenize(raw, delimiters)

    assert [(token.segment_id, token.elements) for token in parsed] == [
        (token.segment_id, token.elements) for token in tokens
    ]


@hypothesis_settings(deadline=None, max_examples=25)
@given(delimiters=delimiter_strategy())
def test_property_detect_delimiters_preserves_encoded_choices(delimiters: Delimiters) -> None:
    interchange = build_interchange().model_copy(update={"delimiters": delimiters})

    encoded = encode(interchange, delimiters=delimiters)

    assert detect_delimiters(encoded) == delimiters


@hypothesis_settings(deadline=None, max_examples=25)
@given(interchange=interchange_strategy())
def test_property_parse_encode_roundtrip_matches_arbitrary_interchange(interchange) -> None:
    encoded = encode(interchange)
    reparsed = parse(encoded)

    assert reparsed.interchange == interchange
    assert reparsed.interchange.delimiters == interchange.delimiters


@hypothesis_settings(deadline=None, max_examples=25)
@given(interchange=interchange_strategy())
def test_property_control_counts_survive_encode_parse_cycle(interchange) -> None:
    encoded = encode(interchange)
    reparsed = parse(encoded).interchange

    original_group = interchange.functional_groups[0]
    reparsed_group = reparsed.functional_groups[0]

    assert reparsed.iea.number_of_included_functional_groups == len(reparsed.functional_groups)
    assert reparsed.iea.interchange_control_number == interchange.iea.interchange_control_number
    assert reparsed_group.ge.number_of_transaction_sets_included == len(reparsed_group.transactions)
    assert reparsed_group.ge.group_control_number == original_group.ge.group_control_number
    assert [
        transaction.se.number_of_included_segments for transaction in reparsed_group.transactions
    ] == [transaction.se.number_of_included_segments for transaction in original_group.transactions]


def test_parse_logs_correlation_id(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    parse(
        "ISA*00*          *00*          *ZZ*ACMEHOMEHLTH   *ZZ*DCMEDICAID     "
        "*260412*1200*^*00501*000000001*0*T*:~"
        "GS*HS*ACMEHOMEHLTH*DCMEDICAID*20260412*1200*1*X*005010X279A1~"
        "ST*270*0001*005010X279A1~"
        "BHT*0022*13*10001234*20260412*1200~"
        "HL*1**20*1~"
        "NM1*PR*2*DC MEDICAID*****PI*DCMEDICAID~"
        "HL*2*1*21*1~"
        "NM1*1P*2*ACME HOME HEALTH*****XX*1234567893~"
        "HL*3*2*22*0~"
        "TRN*1*TRACE0001*9877281234~"
        "NM1*IL*1*DOE*PATIENT****MI*000123450~"
        "DMG*D8*19900101*F~"
        "DTP*291*D8*20260412~"
        "EQ*30~"
        "SE*13*0001~"
        "GE*1*1~"
        "IEA*1*000000001~",
        correlation_id="phase8-library-correlation",
    )

    assert any(
        record.getMessage() == "x12_parse_completed"
        and getattr(record, "correlation_id", None) == "phase8-library-correlation"
        for record in caplog.records
    )
