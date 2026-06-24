#!/usr/bin/env python3
"""Minimal mariadb/mysql CLI for piping SQL imports when the client is not installed (e.g. act)."""

import os
import sys

import pymysql


def parse_args(args: list[str]) -> tuple[str, int, str, str, str | None]:
	user = "root"
	password = os.environ.get("MYSQL_PWD", "")
	host = os.environ.get("MYSQL_HOST", "127.0.0.1")
	port = int(os.environ.get("MYSQL_PORT", "3306"))
	database = None
	skip_next = False

	for index, arg in enumerate(args):
		if skip_next:
			skip_next = False
			continue
		if arg.startswith("--user="):
			user = arg.split("=", 1)[1]
		elif arg == "--user":
			skip_next = True
			user = args[index + 1]
		elif arg.startswith("--password="):
			password = arg.split("=", 1)[1]
		elif arg == "--password":
			skip_next = True
			password = args[index + 1]
		elif arg.startswith("--host="):
			host = arg.split("=", 1)[1]
		elif arg == "--host":
			skip_next = True
			host = args[index + 1]
		elif arg.startswith("--port="):
			port = int(arg.split("=", 1)[1])
		elif arg == "--port":
			skip_next = True
			port = int(args[index + 1])
		elif arg.startswith("-"):
			continue
		elif database is None:
			database = arg

	if database is None:
		raise SystemExit("database name required")

	return host, port, user, password, database


def main() -> None:
	host, port, user, password, database = parse_args(sys.argv[1:])
	sql = sys.stdin.read()
	conn = pymysql.connect(
		host=host,
		port=port,
		user=user,
		password=password,
		database=database,
		charset="utf8mb4",
		client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS,
	)
	try:
		with conn.cursor() as cur:
			cur.execute(sql)
			while cur.nextset():
				pass
	finally:
		conn.close()


if __name__ == "__main__":
	main()
