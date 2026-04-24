from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import fixture_text


def test_parse_271_projects_2120c_benefit_entity_contacts(client: TestClient) -> None:
    edi = fixture_text("271_active_response.x12").replace(
        "EB*1**30~\nDTP*291*D8*20260412~",
        (
            "EB*1**30~\n"
            "LS*2120~\n"
            "NM1*P5*2*PLAN SPONSOR~\n"
            "PER*IC*PROVIDER RELATIONS*TE*8665550001*EM*support@example.test~\n"
            "PER*IC*EDI HELPDESK*TE*8775550001~\n"
            "LE*2120~\n"
            "DTP*291*D8*20260412~"
        ),
    )

    response = client.post(
        "/api/v1/parse",
        files={"file": ("271.x12", edi.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    entity = payload["results"][0]["benefitEntities"][0]
    assert entity["entityIdentifierCode"] == "P5"
    assert entity["name"] == "PLAN SPONSOR"
    assert entity["contacts"] == [
        "PROVIDER RELATIONS (TE:8665550001, EM:support@example.test)",
        "EDI HELPDESK (TE:8775550001)",
    ]
    assert payload["results"][0]["statusReason"] == "Coverage on file"
    assert payload["results"][0]["stControlNumber"] == "0001"
    assert payload["results"][0]["traceNumber"] == "TRACE0001"
