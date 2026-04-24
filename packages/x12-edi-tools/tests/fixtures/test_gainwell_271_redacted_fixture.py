from __future__ import annotations

from pathlib import Path

FIXTURE = Path(__file__).with_name("gainwell_271_redacted.edi")


def test_gainwell_271_redacted_fixture_contract() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line]

    assert lines[0].startswith("ISA*00*")
    assert lines[1].startswith("GS*HS*")
    assert lines[-2] == "GE*153*901~"
    assert lines[-1] == "IEA*1*000000901~"
    assert sum(1 for line in lines if line.startswith("ST*271*")) == 153

    assert "EB*1**30^1^35^47^48^50^86^88^AL^MH*MC*" in text
    assert "LS*2120~" in text
    assert "NM1*P5*2*" in text
    assert "PER*IC*" in text
    assert "LE*2120~" in text

    assert "AAA*N**71*C~" in text
    assert "AAA*N**73*C~" in text
    assert "AAA*N**75*C~" in text

    for code in ("R", "L", "MC", "B"):
        assert f"EB*{code}*" in text
