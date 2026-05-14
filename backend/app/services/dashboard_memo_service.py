from sqlalchemy.orm import Session

from app.models import DashboardMemo


def get_memo_for_user(db: Session, user_id: int) -> DashboardMemo | None:
    return db.query(DashboardMemo).filter(DashboardMemo.user_id == user_id).first()


def upsert_memo_for_user(db: Session, user_id: int, content: str) -> DashboardMemo:
    memo = get_memo_for_user(db, user_id)

    if memo is None:
        memo = DashboardMemo(user_id=user_id, content=content)
        db.add(memo)
    else:
        memo.content = content

    db.commit()
    db.refresh(memo)
    return memo
