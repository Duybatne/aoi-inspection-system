"""
Verdict Engine rule configuration.
Adjust thresholds here without touching business logic.
"""

# Defect class severity mapping
DEFECT_SEVERITY: dict[str, str] = {
    "missing":    "CRITICAL",
    "bridge":     "HIGH",
    "tombstone":  "HIGH",
    "misaligned": "MEDIUM",
    "scratch":    "LOW",
    "void":       "MEDIUM",
}

# Default severity for unknown class names
DEFAULT_SEVERITY = "MEDIUM"

# Confidence thresholds
HIGH_CONF_THRESHOLD = 0.85    # Any defect above this → immediate FAIL
WARNING_CONF_THRESHOLD = 0.50 # Defects below this are considered uncertain

# Count-based FAIL rule
MAX_DEFECT_COUNT = 3          # More than this many defects → FAIL regardless

# Severity → verdict mapping when count/threshold rules don't fire
SEVERITY_VERDICT_MAP: dict[str, str] = {
    "CRITICAL": "FAIL",
    "HIGH":     "FAIL",
    "MEDIUM":   "WARNING",
    "LOW":      "WARNING",
}
