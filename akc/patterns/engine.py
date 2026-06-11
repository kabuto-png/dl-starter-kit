from datetime import datetime, timezone

# ENG-01: Initial confidence — Beta(2,1) prior
INIT_CONFIDENCE = 0.67

# ENG-02
SUCCESS_DELTA = 0.05
FAILURE_DELTA = -0.10
MAX_CONFIDENCE = 0.95
MIN_CONFIDENCE = 0.0

# ENG-05
GOLD_EXIT_THRESHOLD = 3


def classify_tier(confidence: float) -> str:
    if confidence >= 0.85:
        return "gold"
    if confidence >= 0.70:
        return "production"
    if confidence >= 0.50:
        return "experimental"
    return "demoted"


# Invariant: confidence and tier must always agree — if tier is 'gold', confidence must be ≥ 0.85.
def apply_outcome(pattern: dict, outcome: str) -> dict:
    delta = SUCCESS_DELTA if outcome == "success" else FAILURE_DELTA
    new_conf = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, pattern["confidence"] + delta))

    if outcome == "success":
        new_consec = 0
    else:
        new_consec = pattern["consecutive_failures"] + 1

    # Step 1: ENG-04 — demotion lock
    if pattern["tier"] == "demoted":
        new_tier = "demoted"
    # Step 2: ENG-05 — Gold exit guardrail
    elif pattern["tier"] == "gold" and new_consec < GOLD_EXIT_THRESHOLD:
        new_tier = "gold"
        # Clamp confidence to Gold floor so tier and confidence stay in sync
        new_conf = max(new_conf, 0.85)
    # Step 3: ENG-03 — natural tier from confidence
    else:
        new_tier = classify_tier(new_conf)

    return {
        **pattern,
        "confidence": new_conf,
        "tier": new_tier,
        "consecutive_failures": new_consec,
        "times_applied": pattern["times_applied"] + 1,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
