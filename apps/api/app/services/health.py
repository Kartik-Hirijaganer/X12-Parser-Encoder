"""Deep health-check services."""

from __future__ import annotations

from x12_edi_tools import parse
from x12_edi_tools.payers import list_profiles

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import metrics_available
from app.schemas.health import HealthChecks, HealthResponse

PARSER_SMOKE_PAYLOAD = (
    "ISA*00*          *00*          *ZZ*ACMEHOMEHLTH   *ZZ*DCMEDICAID     *260412*1200*^"
    "*00501*000000001*0*T*:~"
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
    "IEA*1*000000001~"
)
logger = get_logger(__name__)


def deep_health(*, correlation_id: str | None = None) -> HealthResponse:
    """Run the phase-8 deep health checks."""

    details: list[str] = []

    try:
        import x12_edi_tools  # noqa: F401

        library_import = True
    except Exception as exc:
        library_import = False
        details.append(f"library_import_failed:{exc}")

    parser_smoke = False
    try:
        parse(PARSER_SMOKE_PAYLOAD, correlation_id=correlation_id)
        parser_smoke = True
    except Exception as exc:
        details.append(f"parser_smoke_failed:{exc}")

    try:
        profiles_loaded = list_profiles()
    except Exception as exc:
        profiles_loaded = []
        details.append(f"profile_registry_failed:{exc}")

    try:
        prometheus_metrics = metrics_available()
    except Exception as exc:
        prometheus_metrics = False
        details.append(f"metrics_registry_failed:{exc}")

    status_value = (
        "ok"
        if library_import and parser_smoke and profiles_loaded and prometheus_metrics
        else "degraded"
    )
    response = HealthResponse(
        status=status_value,
        version=settings.app_version,
        checks=HealthChecks(
            library_import=library_import,
            parser_smoke=parser_smoke,
            prometheus_metrics=prometheus_metrics,
            profiles_loaded=profiles_loaded,
            details=details,
        ),
    )
    logger.info(
        "deep_health_completed",
        extra={
            "correlation_id": correlation_id,
            "status": response.status,
            "profiles_loaded": len(profiles_loaded),
            "prometheus_metrics": prometheus_metrics,
        },
    )
    return response
