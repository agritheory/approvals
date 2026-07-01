#!/usr/bin/env python3
"""Run a single SQL statement against MariaDB (used when mysql CLI is unavailable, e.g. act)."""

import os
import sys

import pymysql


def main() -> None:
	if len(sys.argv) != 2:
		raise SystemExit(f"usage: {sys.argv[0]} '<sql>'")

	conn = pymysql.connect(
		host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
		port=int(os.environ.get("MYSQL_PORT", "3306")),
		user="root",
		password=os.environ.get("MYSQL_PWD", ""),
		autocommit=True,
	)
	try:
		with conn.cursor() as cur:
			cur.execute(sys.argv[1])
	finally:
		conn.close()


if __name__ == "__main__":
	main()
