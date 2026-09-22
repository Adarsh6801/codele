from app.scripts.question_learning_paths import LEARNING_PATHS, plain_trace


def test_every_library_question_has_a_plain_reusable_player_trace() -> None:
    for slug, path in LEARNING_PATHS.items():
        trace = plain_trace(slug, path)

        assert len(trace) >= 3
        for expected_step, step in enumerate(trace, start=1):
            assert step["step"] == expected_step
            assert isinstance(step["array"], list)
            assert isinstance(step["cursor"], int)
            assert step["cursor"] >= 0
            assert isinstance(step["note_en"], str) and len(step["note_en"]) > 30
            assert isinstance(step["note_ml"], str) and len(step["note_ml"]) > 10
