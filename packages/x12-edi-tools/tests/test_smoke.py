from pathlib import Path

from x12_edi_tools import SubmitterConfig, __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_submitter_config_instantiates() -> None:
    config = SubmitterConfig(
        organization_name="ACME HOME HEALTH",
        provider_npi="1234567893",
        trading_partner_id="ACMETP01",
        payer_name="DC MEDICAID",
        payer_id="DCMEDICAID",
        interchange_receiver_id="DCMEDICAID",
    )

    assert config.max_batch_size == 5000
    assert config.usage_indicator == "T"


def test_synthetic_fixture_is_present() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "270_realtime_single.x12"
    fixture_text = fixture_path.read_text(encoding="utf-8")

    assert fixture_text.startswith("ISA*")
    assert "ACME HOME HEALTH" in fixture_text
