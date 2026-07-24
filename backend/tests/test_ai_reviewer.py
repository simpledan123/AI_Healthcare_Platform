from app.config import Settings
from app.services.ai_reviewer import deterministic_review, review_pose


SNAPSHOT = {
    "overall_similarity": 74.0,
    "data_quality": 0.9,
    "severity": 3,
    "pain_description": "",
    "worst_segments": [
        {
            "start_percent": 40,
            "end_percent": 45,
            "joint": "right_wrist_extension",
            "joint_label": "오른쪽 손목",
            "difference": 18.4,
            "unit": "deg",
        }
    ],
}


def test_deterministic_review_keeps_measured_evidence():
    review = deterministic_review(SNAPSHOT)

    assert review.verdict == "RETRY"
    assert review.corrections[0].joint == "right_wrist_extension"
    assert "18.4" in review.corrections[0].evidence


def test_live_mode_without_key_uses_auditable_fallback():
    settings = Settings(ai_review_mode="live", anthropic_api_key="")
    result = review_pose(SNAPSHOT, settings)

    assert result.fallback_used is True
    assert result.provider == "policy-engine"
    assert result.validation_status == "FALLBACK_VALIDATED"

