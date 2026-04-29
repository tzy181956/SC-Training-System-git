from __future__ import annotations

import hashlib


DEFAULT_TEST_DEFINITION_CATALOG = [
    {
        "name": "基础身体",
        "code": "basic-body",
        "notes": None,
        "metrics": [
            {"name": "身高", "code": "height", "default_unit": "cm", "notes": None, "is_lower_better": False},
            {"name": "体重", "code": "weight", "default_unit": "kg", "notes": None, "is_lower_better": False},
            {"name": "体脂率", "code": "body-fat-percentage", "default_unit": "%", "notes": None, "is_lower_better": False},
            {"name": "臂展", "code": "wingspan", "default_unit": "cm", "notes": None, "is_lower_better": False},
            {"name": "站摸", "code": "standing-reach", "default_unit": "cm", "notes": None, "is_lower_better": False},
        ],
    },
    {
        "name": "力量测试",
        "code": "strength-test",
        "notes": None,
        "metrics": [
            {"name": "卧推", "code": "bench-press", "default_unit": "kg", "notes": None, "is_lower_better": False},
            {"name": "卧拉", "code": "bench-pull", "default_unit": "kg", "notes": None, "is_lower_better": False},
            {"name": "深蹲", "code": "back-squat", "default_unit": "kg", "notes": None, "is_lower_better": False},
            {"name": "挺举", "code": "clean-and-jerk", "default_unit": "kg", "notes": None, "is_lower_better": False},
            {"name": "臀桥", "code": "hip-thrust", "default_unit": "kg", "notes": None, "is_lower_better": False},
            {"name": "引体向上", "code": "pull-up", "default_unit": "次", "notes": None, "is_lower_better": False},
        ],
    },
    {
        "name": "体能测试",
        "code": "power-test",
        "notes": None,
        "metrics": [
            {"name": "反向跳", "code": "countermovement-jump", "default_unit": "cm", "notes": None, "is_lower_better": False},
            {"name": "静蹲跳", "code": "squat-jump", "default_unit": "cm", "notes": None, "is_lower_better": False},
            {"name": "直腿跳", "code": "stiff-leg-jump", "default_unit": "RSI", "notes": None, "is_lower_better": False},
            {"name": "助跑摸高", "code": "approach-vertical-jump", "default_unit": "cm", "notes": None, "is_lower_better": False},
            {"name": "原地摸高", "code": "standing-vertical-jump", "default_unit": "cm", "notes": None, "is_lower_better": False},
        ],
    },
    {
        "name": "速度测试",
        "code": "speed-test",
        "notes": None,
        "metrics": [
            {"name": "30m跑10m", "code": "30m-sprint-10m", "default_unit": "s", "notes": None, "is_lower_better": True},
            {"name": "30m跑30m", "code": "30m-sprint-30m", "default_unit": "s", "notes": None, "is_lower_better": True},
            {"name": "505变向-左腿", "code": "505-change-of-direction-left", "default_unit": "s", "notes": None, "is_lower_better": True},
            {"name": "505变向-右腿", "code": "505-change-of-direction-right", "default_unit": "s", "notes": None, "is_lower_better": True},
            {"name": "505变向-总用时", "code": "505-change-of-direction-total", "default_unit": "s", "notes": None, "is_lower_better": True},
            {"name": "限制区移动", "code": "lane-agility", "default_unit": "s", "notes": None, "is_lower_better": True},
        ],
    },
    {
        "name": "耐力测试",
        "code": "endurance-test",
        "notes": None,
        "metrics": [
            {"name": "3000m", "code": "3000m", "default_unit": "s", "notes": None, "is_lower_better": True},
            {"name": "17折返", "code": "17-shuttle-run", "default_unit": "s", "notes": None, "is_lower_better": True},
            {"name": "17折返4", "code": "17-shuttle-run-x4", "default_unit": "s", "notes": None, "is_lower_better": True},
        ],
    },
]

DEFAULT_LOWER_BETTER_TEST_METRIC_CODES = tuple(
    metric["code"]
    for definition in DEFAULT_TEST_DEFINITION_CATALOG
    for metric in definition["metrics"]
    if metric.get("is_lower_better")
)


def build_auto_test_type_code(name: str) -> str:
    normalized = (name or "").strip()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"test-type-{digest}"


def build_auto_test_metric_code(test_type_name: str, metric_name: str) -> str:
    normalized = f"{(test_type_name or '').strip()}::{(metric_name or '').strip()}"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"test-metric-{digest}"
