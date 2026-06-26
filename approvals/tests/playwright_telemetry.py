# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import socket
from urllib.parse import urlparse

import frappe


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


def init_playwright_url_state(base_url: str | None = None) -> dict:
	"""
	Resolve how Playwright should reach the bench.

	The site hostname (e.g. ``fraxinus``) may not resolve in DNS on the machine
	running the browser. When that happens but the bench is reachable on
	``127.0.0.1:<webserver_port>``, navigate to the canonical URL and map the
	hostname to localhost via Chromium's ``--host-resolver-rules`` so the HTTP
	``Host`` header stays correct (Chromium rejects manual Host header overrides).
	"""
	global _url_state
	site_config = frappe.get_site_config()
	target = bench_connection_target(site_config, frappe.utils.get_url())
	site_host = target["site_host"]
	bench_port = target["bench_port"]
	canonical_url = target["canonical_url"]
	probe = probe_host_port(site_host, bench_port) if site_host else {}

	if site_host and probe.get("dns_resolved") and probe.get("tcp_reachable"):
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": None,
			"playwright_resolution": "canonical",
		}
	elif probe_host_port("127.0.0.1", bench_port).get("tcp_reachable"):
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": site_host,
			"playwright_resolution": "host_resolver_map",
		}
	else:
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": None,
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
