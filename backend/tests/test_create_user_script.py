from scripts.create_user import build_parser


def test_create_user_script_uses_current_sport_scope_options() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--username",
            "coach",
            "--display-name",
            "Coach",
            "--role-code",
            "coach",
            "--sport-id",
            "1",
        ]
    )

    assert args.sport_id == 1
    assert args.allow_sportless_role is False


def test_create_user_script_allows_explicit_sportless_coach_setup() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--username",
            "coach",
            "--display-name",
            "Coach",
            "--role-code",
            "coach",
            "--allow-sportless-role",
        ]
    )

    assert args.sport_id is None
    assert args.allow_sportless_role is True
