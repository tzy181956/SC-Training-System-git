from app.core.database import SessionLocal
from app.services.demo_history_service import seed_training_demo_history
from app.services.seed_service import seed_demo_data


def main() -> None:
    with SessionLocal() as db:
        seed_demo_data(db)
        seed_training_demo_history(db)
        db.commit()
    print("Demo data seeded.")


if __name__ == "__main__":
    main()
