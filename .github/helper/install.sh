#!/bin/bash

export PIP_ROOT_USER_ACTION=ignore

set -e

DB="${DB:-mariadb}"

# act runs workflow steps as root; bench refuses root. Re-run this script as ubuntu.
if [[ "${ACT:-}" == "true" && "$(id -u)" -eq 0 ]]; then
	mkdir -p /home/ubuntu
	chown ubuntu:ubuntu /home/ubuntu
	exec runuser -u ubuntu -- env \
		HOME=/home/ubuntu \
		ACT=true \
		BRANCH_NAME="${BRANCH_NAME:-}" \
		GITHUB_WORKSPACE="${GITHUB_WORKSPACE}" \
		MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}" \
		MYSQL_PORT="${MYSQL_PORT:-3306}" \
		MYSQL_PWD="${MYSQL_PWD:-}" \
		PIP_ROOT_USER_ACTION=ignore \
		PATH="${PATH}" \
		bash "$0"
fi

if [ "${ACT}" = "true" ]; then
	export PATH="${HOME}/.local/bin:${PATH}"
fi

# Check for merge conflicts before proceeding
if [ "${ACT}" != "true" ]; then
	python -m compileall -f -x '/(\.git|node_modules|\.venv)/' "${GITHUB_WORKSPACE}"
fi
if grep -lr --exclude-dir=node_modules "^<<<<<<< " "${GITHUB_WORKSPACE}"
	then echo "Found merge conflicts"
	exit 1
fi

cd ~ || exit

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"

mysql_exec() {
	if command -v mysql >/dev/null 2>&1; then
		mysql --host "${MYSQL_HOST}" --port "${MYSQL_PORT}" -u root -e "$1"
	else
		python3 "${GITHUB_WORKSPACE}/.github/helper/mysql_exec.py" "$1"
	fi
}

wait_for_redis() {
	local port="${REDIS_PORT:-6379}"
	for _ in $(seq 1 60); do
		if (echo > /dev/tcp/127.0.0.1/"$port") 2>/dev/null; then
			return 0
		fi
		sleep 1
	done
	echo "Redis service did not become reachable on port ${port}" >&2
	return 1
}

pip install --upgrade pip
pip install frappe-bench

mysql_exec "SET GLOBAL character_set_server = 'utf8mb4'"
mysql_exec "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

mysql_exec "CREATE OR REPLACE DATABASE test_site"
mysql_exec "CREATE OR REPLACE USER 'test_site'@'localhost' IDENTIFIED BY 'test_site'"
mysql_exec "CREATE OR REPLACE USER 'test_site'@'%' IDENTIFIED BY 'test_site'"
mysql_exec "GRANT ALL PRIVILEGES ON \`test_site\`.* TO 'test_site'@'localhost'"
mysql_exec "GRANT ALL PRIVILEGES ON \`test_site\`.* TO 'test_site'@'%'"

mysql_exec "ALTER USER 'root'@'localhost' IDENTIFIED BY 'root'"  # match site_config
mysql_exec "FLUSH PRIVILEGES"

echo BRANCH_NAME: "${BRANCH_NAME}"
git clone https://github.com/frappe/frappe --branch ${BRANCH_NAME}
bench init frappe-bench --frappe-path ~/frappe --python "$(which python)" --skip-assets --ignore-exist --no-backups

cp "${GITHUB_WORKSPACE}/.github/helper/common_site_config.json" ~/frappe-bench/sites/common_site_config.json

mkdir ~/frappe-bench/sites/test_site
if [ "$DB" == "postgres" ]; then
  cp "${GITHUB_WORKSPACE}/.github/helper/site_config_postgres.json" ~/frappe-bench/sites/test_site/site_config.json
  echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE DATABASE test_site" -U postgres
  echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE USER test_site WITH PASSWORD 'test_site'" -U postgres
  echo "travis" | psql -h 127.0.0.1 -p 5432 -c "GRANT ALL PRIVILEGES ON DATABASE test_site TO test_site" -U postgres
else
  cp "${GITHUB_WORKSPACE}/.github/helper/site_config.json" ~/frappe-bench/sites/test_site/site_config.json
fi


cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile
sed -i 's/^redis_cache:/# redis_cache:/g' Procfile
sed -i 's/^redis_queue:/# redis_queue:/g' Procfile
sed -i 's/^worker:/# worker:/g' Procfile

bench get-app erpnext https://github.com/frappe/erpnext --branch ${BRANCH_NAME} --resolve-deps --skip-assets
bench get-app hrms https://github.com/frappe/hrms --branch ${BRANCH_NAME} --skip-assets
bench get-app approvals "${GITHUB_WORKSPACE}" --skip-assets

printf '%s\n' 'frappe' 'erpnext' 'hrms' 'approvals' > ~/frappe-bench/sites/apps.txt
bench setup requirements --python
bench use test_site
bench set-config -g server_script_enabled 1

wait_for_redis
bench --site test_site reinstall --yes --admin-password admin

bench --site test_site migrate

bench build --app approvals
cd apps/approvals
yarn --prefer-offline
yarn build
cd ../..

bench setup requirements --dev

echo "BENCH VERSION NUMBERS:"
bench version
echo "SITE LIST-APPS:"
bench list-apps

wait_for_redis
bench execute 'approvals.tests.setup.before_test'
