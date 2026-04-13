from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
LIBRARY_SRC = REPO_ROOT / "packages" / "x12-edi-tools" / "src"
FIXTURES_DIR = REPO_ROOT / "packages" / "x12-edi-tools" / "tests" / "fixtures"

if str(LIBRARY_SRC) not in sys.path:
    sys.path.insert(0, str(LIBRARY_SRC))

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def config_payload() -> dict[str, object]:
    return {
        "organizationName": "Acme Home Health",
        "providerNpi": "1234567893",
        "providerEntityType": "2",
        "tradingPartnerId": "ACMEHOMEHLTH",
        "providerTaxonomyCode": "",
        "contactName": "Jane Doe",
        "contactPhone": "2025551234",
        "contactEmail": "jane@example.com",
        "payerName": "DC MEDICAID",
        "payerId": "DCMEDICAID",
        "interchangeReceiverId": "DCMEDICAID",
        "receiverIdQualifier": "ZZ",
        "senderIdQualifier": "ZZ",
        "usageIndicator": "T",
        "acknowledgmentRequested": "0",
        "defaultServiceTypeCode": "30",
        "defaultServiceDate": "20260412",
        "maxBatchSize": 5000,
    }


def fixture_text(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")
