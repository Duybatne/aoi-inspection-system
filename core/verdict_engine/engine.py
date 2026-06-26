import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

from core.verdict_engine import rules

logger = logging.getLogger("VerdictEngine")


@dataclass
class VerdictResult:
    verdict: str            # "PASS", "FAIL", "WARNING"
    severity: str           # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    reason: str             # Human-readable explanation
    defect_count: int = 0
    flagged_defects: List[Dict] = field(default_factory=list)


class VerdictEngine:
    """
    Rule-based verdict engine for PCB inspection results.

    Evaluation order (first matching rule wins):
        1. No defects                             → PASS
        2. Any defect with HIGH confidence        → FAIL (immediate)
        3. Total defect count > MAX_DEFECT_COUNT  → FAIL
        4. Highest severity mapping               → FAIL or WARNING
        5. All defects below WARNING threshold    → WARNING (uncertain)
        6. Default                                → PASS
    """

    def evaluate(
        self,
        defects: List[Dict[str, Any]],
        high_conf_threshold: float = rules.HIGH_CONF_THRESHOLD,
        max_defect_count: int = rules.MAX_DEFECT_COUNT,
        warning_conf_threshold: float = rules.WARNING_CONF_THRESHOLD,
    ) -> VerdictResult:

        if not defects:
            logger.info("VerdictEngine: no defects → PASS")
            return VerdictResult(verdict="PASS", severity="NONE", reason="No defects detected.")

        defect_count = len(defects)

        # Rule 1: High-confidence defect → immediate FAIL
        high_conf = [d for d in defects if d.get("confidence", 0) >= high_conf_threshold]
        if high_conf:
            worst = max(high_conf, key=lambda d: d.get("confidence", 0))
            severity = rules.DEFECT_SEVERITY.get(worst.get("class_name", ""), rules.DEFAULT_SEVERITY)
            reason = (
                f"High-confidence defect detected: '{worst.get('class_name')}' "
                f"(confidence={worst.get('confidence', 0):.2f})."
            )
            logger.info(f"VerdictEngine: FAIL (high-conf rule) — {reason}")
            return VerdictResult(
                verdict="FAIL",
                severity=severity,
                reason=reason,
                defect_count=defect_count,
                flagged_defects=high_conf,
            )

        # Rule 2: Too many defects
        if defect_count > max_defect_count:
            reason = f"Too many defects: {defect_count} > max {max_defect_count}."
            logger.info(f"VerdictEngine: FAIL (count rule) — {reason}")
            return VerdictResult(
                verdict="FAIL",
                severity="HIGH",
                reason=reason,
                defect_count=defect_count,
                flagged_defects=defects,
            )

        # Rule 3: Severity-based verdict
        severities = [
            rules.DEFECT_SEVERITY.get(d.get("class_name", ""), rules.DEFAULT_SEVERITY)
            for d in defects
        ]
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        worst_severity = min(severities, key=lambda s: severity_order.index(s) if s in severity_order else 99)
        verdict_from_severity = rules.SEVERITY_VERDICT_MAP.get(worst_severity, "WARNING")

        if verdict_from_severity == "FAIL":
            reason = f"Defect of severity '{worst_severity}' detected."
            logger.info(f"VerdictEngine: FAIL (severity rule) — {reason}")
            return VerdictResult(
                verdict="FAIL",
                severity=worst_severity,
                reason=reason,
                defect_count=defect_count,
                flagged_defects=defects,
            )

        # Rule 4: All defects uncertain (low confidence) → WARNING
        uncertain = [d for d in defects if d.get("confidence", 0) < warning_conf_threshold]
        if len(uncertain) == defect_count:
            reason = "All detected anomalies have low confidence — operator review recommended."
            logger.info(f"VerdictEngine: WARNING (low-conf rule)")
            return VerdictResult(
                verdict="WARNING",
                severity="LOW",
                reason=reason,
                defect_count=defect_count,
                flagged_defects=defects,
            )

        # Rule 5: Medium severity → WARNING
        reason = f"Possible defects of severity '{worst_severity}' — requires operator review."
        logger.info(f"VerdictEngine: WARNING (medium-severity rule)")
        return VerdictResult(
            verdict="WARNING",
            severity=worst_severity,
            reason=reason,
            defect_count=defect_count,
            flagged_defects=defects,
        )
