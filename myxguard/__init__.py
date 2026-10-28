"""MyxGuard: a small, dependency-free prompt-injection scanner.

The public API is intentionally tiny::

    from myxguard import scan, scan_file

    result = scan(text, content_type="auto", languages=None)
    result.risk_score   # int, 0..100
    result.risk_level   # "none" | "low" | "medium" | "high" | "critical"
    result.findings     # list of Finding

``languages=None`` checks every language pack that ships with MyxGuard.
Pass ``config=ScanConfig(...)`` to change weights or the intent window.
The default call stays the same as in 0.1.
"""

from myxguard.models import Finding, ScanResult
from myxguard.scanner import scan, scan_file
from myxguard.scoring import ScanConfig

__version__ = "0.4.0"

__all__ = [
    "Finding",
    "ScanConfig",
    "ScanResult",
    "scan",
    "scan_file",
    "__version__",
]
