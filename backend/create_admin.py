"""Create the first WGTK Admin user in an already-migrated database.

Unlike seed.py (which drops and recreates every table — dev only, never run
it against a real database), this is idempotent and safe to run in
production: it does nothing if a user with the given email already exists.

Usage:
    cd backend
    FLASK_ENV=production python create_admin.py admin@wgtk.co.uk "Wendy" "Admin"

Prompts for a password interactively so it never ends up in shell history.
"""

import getpass
import sys

from app import create_app
from app.extensions import bcrypt, db
from app.models.user import User, UserRole


def run(email, first_name, last_name):
    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(email=email.lower()).first()
        if existing:
            print(f"User {email} already exists (role={existing.role.value}) — nothing to do.")
            return

        password = getpass.getpass("Password for the new WGTK Admin: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords did not match.", file=sys.stderr)
            sys.exit(1)

        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.WGTK_ADMIN,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        )
        db.session.add(user)
        db.session.commit()
        print(f"Created WGTK Admin {email}.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <email> <first_name> <last_name>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])
