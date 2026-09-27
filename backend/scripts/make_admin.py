"""Grant or withdraw administrator rights from the command line.

There is no way to promote yourself through the UI, so the first administrator
is created here.

    docker-compose exec api python scripts/make_admin.py you@example.com
    docker-compose exec api python scripts/make_admin.py you@example.com --remove
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--remove"]
    remove = "--remove" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 2

    email = args[0].strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No account found for {email}.")
            return 1

        if remove:
            others = db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.is_admin.is_(True), User.id != user.id)
            )
            if not others:
                print("Refusing: that would leave no administrators.")
                return 1

        user.is_admin = not remove
        db.commit()

    print(f"{email} is {'no longer an administrator' if remove else 'now an administrator'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
