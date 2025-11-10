("""Utility to create a JWT test token using application settings.

Usage:
	python get_token.py --sub username --hours 1

Prints a signed JWT to stdout and a curl example.
""")

from __future__ import annotations
from datetime import datetime, timedelta
import argparse
from jose import jwt
from app.config import settings


def create_token(subject: str = "test-user", hours: int = 1) -> str:
	payload = {
		"sub": subject,
		"exp": datetime.utcnow() + timedelta(hours=hours)
	}
	token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
	return token


def main() -> None:
	parser = argparse.ArgumentParser(description="Create a signed JWT using app settings")
	parser.add_argument("--sub", default="test-user", help="Subject (sub) claim")
	parser.add_argument("--hours", type=int, default=1, help="Token lifetime in hours")
	args = parser.parse_args()

	token = create_token(args.sub, args.hours)
	print(token)
	print()
	print("Example Authorization header:")
	print(f"Authorization: Bearer {token}")


if __name__ == "__main__":
	main()

