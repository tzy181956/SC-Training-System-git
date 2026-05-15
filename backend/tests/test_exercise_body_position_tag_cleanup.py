from __future__ import annotations

from app.services.exercise_library_import import _remove_not_applicable_tags
from app.services.exercise_service import _build_tag_summary, _remove_not_applicable_tag_values
from scripts.data_cleanup.remove_other_body_position_tag import (
    build_tag_text,
    clean_search_keywords,
    remove_target_tag,
)


def test_body_position_other_is_removed_from_exercise_payloads() -> None:
    cleaned = _remove_not_applicable_tag_values(
        {
            "bodyPosition": ["其他", "站姿", "站姿"],
            "equipment": ["杠铃"],
            "usageScene": ["不适用", "训练现场"],
        }
    )

    assert cleaned["bodyPosition"] == ["站姿"]
    assert cleaned["equipment"] == ["杠铃"]
    assert cleaned["usageScene"] == ["训练现场"]
    assert "其他" not in _build_tag_summary(cleaned, limit=12)


def test_body_position_other_is_removed_from_excel_import_tags() -> None:
    cleaned = _remove_not_applicable_tags(
        {
            "bodyPosition": ["其他", "俯卧"],
            "equipment": ["不适用", "哑铃"],
        }
    )

    assert cleaned["bodyPosition"] == ["俯卧"]
    assert cleaned["equipment"] == ["哑铃"]


def test_cleanup_script_rebuilds_tag_text_and_keywords_without_other() -> None:
    cleaned, changed = remove_target_tag(
        {
            "bodyPosition": ["其他", "坐姿"],
            "equipment": ["弹力带"],
        }
    )

    assert changed is True
    assert cleaned["bodyPosition"] == ["坐姿"]

    tag_text = build_tag_text(cleaned)
    keywords = clean_search_keywords(
        ["动作名", "体位:其他；器械:弹力带", "其他"],
        tag_text,
    )

    assert "体位:其他；器械:弹力带" not in keywords
    assert "其他" not in keywords
    assert tag_text in keywords
