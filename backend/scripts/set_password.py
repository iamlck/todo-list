"""Set a user's password from the command line.

There is no self-service password reset yet, so this is the way back in if you
forget one.

    docker-compose exec api python scripts/set_password.py you@example.com
    # or, running the backend locally:
    ./.venv/bin/python scripts/set_password.py you@example.com
"""

import getpass
import sys
from pathlib import Path

# Run from anywhere: make the backend package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    email = sys.argv[1].strip().lower()
    password = getpass.getpass("New password (min 8 characters): ")
    if len(password) < 8:
        print("Too short: passwords must be at least 8 characters.")
        return 1
    if password != getpass.getpass("Repeat: "):
        print("Those did not match.")
        return 1

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No account found for {email}.")
            return 1
        user.password_hash = hash_password(password)
        db.commit()

    print(f"Password updated for {email}. Your plan and progress are unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
