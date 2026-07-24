from app.services.demo_data import reference_wrist_sequence, user_wrist_sequence
from app.services.dtw import compare_sequences


def test_dtw_aligns_different_sequence_lengths():
    result = compare_sequences(user_wrist_sequence(), reference_wrist_sequence())

    assert 0 < result.similarity < 100
    assert result.speed_ratio > 1
    assert len(result.path) >= len(reference_wrist_sequence())
    assert result.worst_segments
    assert all("joint" in item and "difference" in item for item in result.worst_segments)


def test_identical_sequences_score_near_one_hundred():
    sequence = reference_wrist_sequence()
    result = compare_sequences(sequence, sequence)

    assert result.similarity > 99.9
    assert result.distance == 0

