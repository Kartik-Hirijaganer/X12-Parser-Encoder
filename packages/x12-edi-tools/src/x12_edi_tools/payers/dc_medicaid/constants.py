"""DC Medicaid profile constants derived from the implementation plan."""

from __future__ import annotations

PROFILE_NAME = "dc_medicaid"
PAYER_ID = "DCMEDICAID"
PAYER_NAME = "DC MEDICAID"
ISA_RECEIVER_ID = "DCMEDICAID"
RECEIVER_ID_QUALIFIER = "ZZ"
DEFAULT_SERVICE_TYPE_CODE = "30"
MAX_BATCH_TRANSACTIONS = 5000

VALID_SERVICE_TYPE_CODES = frozenset(
    {
        "1",
        "30",
        "33",
        "35",
        "47",
        "48",
        "50",
        "86",
        "88",
        "98",
        "AL",
        "MH",
        "UC",
    }
)

AAA_REASON_MESSAGES = {
    "51": "Provider not on file",
    "71": "DOB mismatch",
    "72": "Invalid member ID",
    "73": "Invalid name",
    "75": "Subscriber not found",
}

AAA_REASON_SUGGESTIONS = {
    "51": "Confirm the billing or servicing provider is registered with DC Medicaid.",
    "71": "Verify the subscriber date of birth before resubmitting the inquiry.",
    "72": "Verify the Medicaid member ID before resubmitting the inquiry.",
    "73": "Verify the subscriber name spelling before resubmitting the inquiry.",
    "75": "Confirm the subscriber demographics and coverage before resubmitting.",
}
