from __future__ import annotations

from test_phase1_models import build_interchange, build_transaction_270
from x12_edi_tools import SnipLevel, validate
from x12_edi_tools.models.transactions import Interchange


def _build_three_transaction_interchange() -> Interchange:
    interchange = build_interchange()
    transactions = []
    for index in range(3):
        control_number = f"{index + 1:04d}"
        base_transaction = build_transaction_270()
        transaction = base_transaction.model_copy(
            update={
                "st": base_transaction.st.model_copy(
                    update={"transaction_set_control_number": control_number}
                ),
                "se": base_transaction.se.model_copy(
                    update={"transaction_set_control_number": control_number}
                ),
            }
        )
        transactions.append(transaction)

    transactions[1] = transactions[1].model_copy(update={"bht": None})
    interchange.functional_groups[0].transactions = transactions
    interchange.functional_groups[0].ge = interchange.functional_groups[0].ge.model_copy(
        update={"number_of_transaction_sets_included": len(transactions)}
    )
    return interchange


def _build_profile_issue_interchange() -> Interchange:
    interchange = build_interchange()
    transactions = []
    for index in range(2):
        control_number = f"{index + 1:04d}"
        base_transaction = build_transaction_270()
        transaction = base_transaction.model_copy(
            update={
                "st": base_transaction.st.model_copy(
                    update={"transaction_set_control_number": control_number}
                ),
                "se": base_transaction.se.model_copy(
                    update={"transaction_set_control_number": control_number}
                ),
            },
            deep=True,
        )
        transactions.append(transaction)

    bad_payer_nm1 = transactions[1].loop_2000a.loop_2100a.nm1.model_copy(
        update={"last_name": "WRONG PAYER"}
    )
    bad_loop_2100a = transactions[1].loop_2000a.loop_2100a.model_copy(update={"nm1": bad_payer_nm1})
    transactions[1] = transactions[1].model_copy(
        update={
            "loop_2000a": transactions[1].loop_2000a.model_copy(
                update={"loop_2100a": bad_loop_2100a}
            )
        }
    )

    interchange.functional_groups[0].transactions = transactions
    interchange.functional_groups[0].ge = interchange.functional_groups[0].ge.model_copy(
        update={"number_of_transaction_sets_included": len(transactions)}
    )
    return interchange


def test_validation_errors_include_transaction_index_and_st02() -> None:
    interchange = _build_three_transaction_interchange()

    result = validate(interchange, levels={SnipLevel.SNIP2})

    assert len(result.issues) == 1
    assert result.issues[0].code == "SNIP2_MISSING_BHT"
    assert result.issues[0].transaction_index == 1
    assert result.issues[0].transaction_control_number == "0002"


def test_profile_validation_errors_include_transaction_index_and_st02() -> None:
    interchange = _build_profile_issue_interchange()

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")
    payer_issue = next(issue for issue in result.issues if issue.code == "DCM_INVALID_PAYER_NAME")

    assert payer_issue.transaction_index == 1
    assert payer_issue.transaction_control_number == "0002"
