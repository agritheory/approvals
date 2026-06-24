#!/bin/bash

# Check for merge conflicts before proceeding
if [ "${ACT}" != "true" ]; then
  python -m compileall -f -x '/(\.git|node_modules|\.venv)/' "${GITHUB_WORKSPACE}"
fi
if grep -lr --exclude-dir=node_modules "^<<<<<<< " "${GITHUB_WORKSPACE}"
    then echo "Found merge conflicts"
    exit 1
fi

if [ "${ACT}" = "true" ]; then
  pip install pymysql
  mkdir -p "${HOME}/.local/bin"
  cat > "${HOME}/.local/bin/redis-server" << 'EOF'
#!/bin/sh
if [ "$1" = "--version" ]; then
  echo "redis-server 7.0.0"
  exit 0
fi
echo "act stub: redis runs as a service container on 127.0.0.1:6379" >&2
exit 1
EOF
  chmod +x "${HOME}/.local/bin/redis-server"
  cat > "${HOME}/.local/bin/mariadb" << EOF
#!/bin/sh
exec python3 "${GITHUB_WORKSPACE}/.github/helper/mariadb_cli.py" "\$@"
EOF
  chmod +x "${HOME}/.local/bin/mariadb"
fi

if [ "${ACT}" != "true" ]; then
  sudo apt update -y && sudo apt install redis-server libcups2-dev mariadb-client -y
fi
