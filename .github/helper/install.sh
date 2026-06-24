#!/bin/bash

export PIP_ROOT_USER_ACTION=ignore

set -e

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

pip install --upgrade pip
pip install frappe-bench

mysql_exec "SET GLOBAL character_set_server = 'utf8mb4'"
mysql_exec "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

mysql_exec "CREATE OR REPLACE DATABASE test_site"
mysql_exec "CREATE OR REPLACE USER 'test_site'@'localhost' IDENTIFIED BY 'test_site'"
mysql_exec "CREATE OR REPLACE USER 'test_site'@'%' IDENTIFIED BY 'test_site'"
mysql_exec "GRANT ALL PRIVILEGES ON \`test_site\`.* TO 'test_site'@'localhost'"
mysql_exec "GRANT ALL PRIVILEGES ON \`test_site\`.* TO 'test_site'@'%'"

mysql_exec "ALTER USER 'root'@'localhost' IDENTIFIED BY 'root'"  # match site_cofig
mysql_exec "FLUSH PRIVILEGES"

echo BRANCH_NAME: "${BRANCH_NAME}"
git clone https://github.com/frappe/frappe --branch ${BRANCH_NAME}
bench init frappe-bench --frappe-path ~/frappe --python "$(which python)" --skip-assets --ignore-exist --no-backups

mkdir ~/frappe-bench/sites/test_site
SITE_CONFIG="${SITE_CONFIG:-${GITHUB_WORKSPACE}/.github/helper/site_config.json}"
cp -r "${SITE_CONFIG}" ~/frappe-bench/sites/test_site/site_config.json

cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

bench get-app erpnext https://github.com/frappe/erpnext --branch ${BRANCH_NAME} --resolve-deps --skip-assets
bench get-app hrms https://github.com/frappe/hrms --branch ${BRANCH_NAME} --skip-assets
bench get-app approvals "${GITHUB_WORKSPACE}" --skip-assets 

printf '%s\n' 'frappe' 'erpnext' 'hrms' 'approvals' > ~/frappe-bench/sites/apps.txt
bench setup requirements --python
bench use test_site
if [ "${ACT}" = "true" ]; then
  bench set-config -g redis_cache "redis://127.0.0.1:6379"
  bench set-config -g redis_queue "redis://127.0.0.1:6379"
  bench set-config -g redis_socketio "redis://127.0.0.1:6379"
fi
bench set-config -g server_script_enabled 1

bench start &> bench_run_logs.txt &
CI=Yes &
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

bench start &> bench_run_logs.txt &
CI=Yes &
bench execute 'approvals.tests.setup.before_test'
