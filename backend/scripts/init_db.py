from scripts.migrate_db import bootstrap_database


def main() -> None:
    bootstrap_database()
    print("Database migration bootstrap finished.")


if __name__ == "__main__":
    main()
