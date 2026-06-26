# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import frappe
from frappe.utils import get_bench_path


def probe_host_port(host: str, port: int, timeout: float = 2.0) -> dict:
	result = {"host": host, "port": port, "dns_resolved": False, "tcp_reachable": False}
	try:
		addrinfo = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
		result["dns_resolved"] = True
		result["resolved_addresses"] = [item[4][0] for item in addrinfo]
	except socket.gaierror as error:
		result["dns_error"] = str(error)
		return result

	try:
		with socket.create_connection((host, port), timeout=timeout):
			result["tcp_reachable"] = True
	except OSError as error:
		result["tcp_error"] = str(error)
	return result


_url_state: dict = {}


def bench_connection_target(site_config: dict, get_url: str) -> dict:
	parsed = urlparse(get_url)
	scheme = parsed.scheme or "http"
	site_host = parsed.hostname or ""

	host_name = site_config.get("host_name")
	if host_name:
		host_parsed = urlparse(host_name if "://" in host_name else f"http://{host_name}")
		if host_parsed.hostname:
			site_host = host_parsed.hostname

	bench_port = site_config.get("webserver_port")
	if bench_port is not None:
		bench_port = int(bench_port)
	elif parsed.port:
		bench_port = parsed.port
	elif host_name:
		host_parsed = urlparse(host_name if "://" in host_name else f"http://{host_name}")
		bench_port = host_parsed.port
	if bench_port is None:
		bench_port = 443 if scheme == "https" else 80

	return {
		"scheme": scheme,
		"site_host": site_host,
		"bench_port": bench_port,
		"canonical_url": get_url.rstrip("/"),
	}


def wait_for_bench_http(port: int, timeout: float = 120.0):
	ping_url = f"http://127.0.0.1:{port}/api/method/ping"
	deadline = time.time() + timeout
	last_error = None
	while time.time() < deadline:
		try:
			with urllib.request.urlopen(ping_url, timeout=2) as response:
				if response.status == 200:
					return
		except (urllib.error.URLError, OSError) as error:
			last_error = error
		time.sleep(2)
	raise RuntimeError(f"bench web not ready at {ping_url}: {last_error}")


def start_bench_web_server(port: int):
	bench_path = get_bench_path()
	start_command = f"nohup bench serve --port {port} >> bench_run_logs.txt 2>&1 &"
	if os.environ.get("ACT") == "true" and os.getuid() == 0:
		subprocess.run(
			[
				"runuser",
				"-u",
				"ubuntu",
				"--",
				"env",
				"HOME=/home/ubuntu",
				"bash",
				"-lc",
				f"cd {bench_path} && {start_command}",
			],
			check=True,
		)
	else:
		subprocess.Popen(
			["bash", "-lc", start_command],
			cwd=bench_path,
			start_new_session=True,
		)


def ensure_bench_web_running(timeout: float = 120.0):
	target = bench_connection_target(frappe.get_site_config(), frappe.utils.get_url())
	port = target["bench_port"]
	if probe_host_port("127.0.0.1", port, timeout=1.0).get("tcp_reachable"):
		try:
			wait_for_bench_http(port, timeout=5.0)
			return
		except RuntimeError:
			pass

	helper_script = (
		Path(get_bench_path()) / "apps" / "approvals" / ".github" / "helper" / "ensure_bench_web.sh"
	)
	if helper_script.is_file():
		env = {**os.environ, "BENCH_ROOT": get_bench_path(), "BENCH_PORT": str(port)}
		subprocess.run(["bash", str(helper_script)], check=True, env=env)
		return

	start_bench_web_server(port)
	wait_for_bench_http(port, timeout=timeout)


def init_playwright_url_state(base_url: str | None = None) -> dict:
	"""
	Resolve how Playwright should reach the bench.

	The site hostname (e.g. ``test_site``) may resolve for Python via ``/etc/hosts``
	but Chromium still needs ``--host-resolver-rules`` to map the canonical hostname
	to ``127.0.0.1`` while preserving the HTTP ``Host`` header.
	"""
	global _url_state
	site_config = frappe.get_site_config()
	target = bench_connection_target(site_config, frappe.utils.get_url())
	site_host = target["site_host"]
	bench_port = target["bench_port"]
	canonical_url = target["canonical_url"]
	localhost_probe = probe_host_port("127.0.0.1", bench_port)
	hostname_probe = probe_host_port(site_host, bench_port) if site_host else {}
	non_localhost = bool(site_host and site_host not in ("127.0.0.1", "localhost"))

	if non_localhost and localhost_probe.get("tcp_reachable"):
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": site_host,
			"playwright_resolution": "host_resolver_map",
		}
	elif site_host and hostname_probe.get("dns_resolved") and hostname_probe.get("tcp_reachable"):
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": None,
			"playwright_resolution": "canonical",
		}
	elif localhost_probe.get("tcp_reachable"):
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": site_host if non_localhost else None,
			"playwright_resolution": "host_resolver_map" if non_localhost else "localhost",
		}
	else:
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": site_host if non_localhost else None,
			"playwright_resolution": "canonical_unreachable",
		}

	if base_url:
		_url_state["playwright_base_url"] = base_url.rstrip("/")
		_url_state["playwright_resolver_map_host"] = None
		_url_state["playwright_resolution"] = "pytest_base_url"

	return _url_state


def get_playwright_base_url() -> str:
	if _url_state.get("playwright_base_url"):
		return _url_state["playwright_base_url"]
	return frappe.utils.get_url().rstrip("/")
