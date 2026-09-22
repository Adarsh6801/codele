"""Create the first Codele super-admin account from the command line."""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select

from app.auth.service import hash_password
from app.db.models import User, UserRole
from app.db.session import SessionLocal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Codele super-admin account.")
    parser.add_argument("--email", required=True, help="Admin sign-in email address")
    parser.add_argument("--display-name", required=True, help="Unique public display name")
    parser.add_argument("--password", required=True, help="Password (at least 12 characters)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    email = args.email.strip().lower()
    display_name = args.display_name.strip()

    if "@" not in email:
        print("Error: provide a valid email address.", file=sys.stderr)
        return 2
    if not 3 <= len(display_name) <= 80:
        print("Error: display name must contain 3 to 80 characters.", file=sys.stderr)
        return 2
    if len(args.password) < 12:
        print("Error: password must contain at least 12 characters.", file=sys.stderr)
        return 2

    with SessionLocal() as session:
        existing = session.scalar(
            select(User).where(
                (func.lower(User.email) == email)
                | (func.lower(User.display_name) == display_name.lower())
            )
        )
        if existing is not None:
            print(
                "Error: an account already uses that email address or display name. "
                "Use different values or ask a super-admin to change its role.",
                file=sys.stderr,
            )
            return 1

        admin = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(args.password),
            role=UserRole.SUPER_ADMIN,
        )
        session.add(admin)
        session.commit()

    print(f"Created super-admin account for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
