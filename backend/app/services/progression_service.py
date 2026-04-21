from dataclasses import dataclass


@dataclass
class ProgressionSuggestion:
    suggestion_weight: float | None
    decision_hint: str
    reason_code: str
    reason_text: str
    should_deload: bool = False
    should_stop_progression: bool = False


DEFAULT_INCREMENT = 2.5


def resolve_increment(default_increment: float | None) -> float:
    if default_increment and default_increment > 0:
        return default_increment
    return DEFAULT_INCREMENT


def compute_next_weight(
    *,
    current_weight: float,
    target_reps: int,
    actual_reps: int,
    actual_rir: int,
    default_increment: float | None,
    previous_rirs: list[int],
) -> ProgressionSuggestion:
    step = resolve_increment(default_increment)
    hard_streak = len(previous_rirs) >= 1 and previous_rirs[-1] <= 1 and actual_rir <= 1
    if actual_reps < target_reps:
        return ProgressionSuggestion(
            suggestion_weight=max(0, current_weight - step),
            decision_hint="reduce",
            reason_code="missed_reps",
            reason_text="未完成目标次数，建议下一组降重。",
            should_deload=True,
        )
    if hard_streak:
        return ProgressionSuggestion(
            suggestion_weight=max(0, current_weight - step),
            decision_hint="backoff",
            reason_code="hard_streak",
            reason_text="连续两组明显吃力，建议停止加重并进入回退组。",
            should_deload=True,
            should_stop_progression=True,
        )
    if actual_rir >= 3:
        return ProgressionSuggestion(
            suggestion_weight=current_weight + step,
            decision_hint="increase",
            reason_code="high_rir",
            reason_text="完成目标且 RIR 较高，建议下一组加重。",
        )
    if actual_rir == 2:
        return ProgressionSuggestion(
            suggestion_weight=current_weight,
            decision_hint="hold",
            reason_code="steady_rir",
            reason_text="完成目标且 RIR 合适，建议维持当前重量。",
        )
    return ProgressionSuggestion(
        suggestion_weight=max(0, current_weight - (step / 2 if step > 2.5 else step)),
        decision_hint="hold_or_reduce",
        reason_code="low_rir",
        reason_text="完成目标但主观吃力，建议维持或小幅降重。",
    )
