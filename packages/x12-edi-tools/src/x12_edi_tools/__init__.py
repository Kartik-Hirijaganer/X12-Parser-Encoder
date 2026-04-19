"""Public package surface for the X12 library."""

from typing import TYPE_CHECKING

from x12_edi_tools import payers
from x12_edi_tools.__about__ import __version__
from x12_edi_tools.common import Delimiters
from x12_edi_tools.config import SubmitterConfig
from x12_edi_tools.convenience import (
    AAAError,
    BenefitEntity,
    Correction,
    EligibilityResult,
    EligibilityResultSet,
    EligibilitySegment,
    ImportResult,
    PatientRecord,
    RowError,
    WarningMessage,
    build_270,
    from_csv,
    from_excel,
    read_271,
)
from x12_edi_tools.encoder import encode
from x12_edi_tools.exceptions import (
    ConfigurationError,
    TransactionParseError,
    X12EncodeError,
    X12Error,
    X12ParseError,
    X12ValidationError,
)
from x12_edi_tools.models import (
    FunctionalGroup,
    GenericSegment,
    Interchange,
    Transaction270,
    Transaction271,
)
from x12_edi_tools.parser import ParseResult, parse
from x12_edi_tools.validator import SnipLevel, ValidationError, ValidationResult, validate

# Phase 0 reservation \u2014 the public surface for 837I/837P/835 lands in Phase 7.
# These names are imported under TYPE_CHECKING only so static analysis stays in
# sync as downstream phases land each contract. They are intentionally excluded
# from ``__all__`` until Phase 7 flips them to runtime imports.
if TYPE_CHECKING:  # pragma: no cover - import guard
    from x12_edi_tools.config import (  # noqa: F401  (Phase 7 export)
        ClaimBuildOptions,
        PartitioningStrategy,
    )
    from x12_edi_tools.exceptions import (  # noqa: F401  (Phase 7 export)
        ClaimValidationError,
        RemittanceParseError,
    )
    from x12_edi_tools.validator.context import (  # noqa: F401  (Phase 4/7 export)
        MemberRegistryLookup,
        ProviderRegistryLookup,
        ValidationContext,
    )

__all__ = [
    "AAAError",
    "BenefitEntity",
    "ConfigurationError",
    "Correction",
    "Delimiters",
    "EligibilityResult",
    "EligibilityResultSet",
    "EligibilitySegment",
    "FunctionalGroup",
    "GenericSegment",
    "ImportResult",
    "Interchange",
    "ParseResult",
    "PatientRecord",
    "RowError",
    "SubmitterConfig",
    "SnipLevel",
    "Transaction270",
    "Transaction271",
    "TransactionParseError",
    "ValidationError",
    "ValidationResult",
    "WarningMessage",
    "X12EncodeError",
    "X12Error",
    "X12ParseError",
    "X12ValidationError",
    "__version__",
    "build_270",
    "encode",
    "from_csv",
    "from_excel",
    "payers",
    "parse",
    "read_271",
    "validate",
]
