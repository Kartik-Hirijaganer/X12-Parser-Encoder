from __future__ import annotations

from fastapi.testclient import TestClient


def test_parse_271_ranks_medicaid_plan_when_medicare_is_primary(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/parse",
        files={
            "file": (
                "medicare_primary_medicaid_gainwell.x12",
                _medicare_primary_medicaid_gainwell_271().encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]

    assert [segment["insuranceTypeCode"] for segment in result["eligibilitySegments"]] == [
        "MB",
        "MC",
    ]
    assert result["defaultPlanOptionIndex"] == 1
    assert [option["payerCode"] for option in result["planOptions"]] == ["ON-FILE", "853Q"]
    assert result["planOptions"][0]["label"] == "Medicare"
    assert result["planOptions"][0]["primaryReturned"] is True
    assert result["planOptions"][1]["label"] == "Medicaid/Gainwell"
    assert result["planOptions"][1]["agencyPreferred"] is True


def _medicare_primary_medicaid_gainwell_271() -> str:
    return (
        "ISA*00*          *00*          *ZZ*ACMEHOMEHLTH   *ZZ*DCMEDICAID     "
        "*260506*1200*^*00501*000000001*0*T*:~\n"
        "GS*HS*ACMEHOMEHLTH*DCMEDICAID*20260506*1200*1*X*005010X279A1~\n"
        "ST*271*0001*005010X279A1~\n"
        "BHT*0022*11*TRACECASE*20260506*1200~\n"
        "HL*1**20*1~\n"
        "NM1*PR*2*GAINWELL TEST PAYER*****PI*GWTEST~\n"
        "HL*2*1*21*1~\n"
        "NM1*1P*2*TEST PROVIDER*****XX*1234567893~\n"
        "HL*3*2*22*0~\n"
        "TRN*2*TRACE000001*9876543210~\n"
        "NM1*IL*1*MEMBER*TEST****MI*SUB000001~\n"
        "DMG*D8*19800101*M~\n"
        "EB*1**30*MB*MEDICARE PRIMARY | ON-FILE | MEDICARE~\n"
        "EB*1**30*MC*DC MEDICAID FFS | 853Q | BUY-IN~\n"
        "DTP*291*D8*20260506~\n"
        "SE*15*0001~\n"
        "GE*1*1~\n"
        "IEA*1*000000001~"
    )
