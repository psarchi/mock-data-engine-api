.PHONY: up down logs restart env
.ONESHELL:

# Paths
ENV_FILE ?= .env
CONFIG ?= config/default/server.yaml
PY ?= python

env:
	@printf '%s\n' \
		'import pathlib' \
		'import yaml' \
		'' \
		'cfg_path = pathlib.Path("$(CONFIG)")' \
		'env_path = pathlib.Path("$(ENV_FILE)")' \
		'data = yaml.safe_load(cfg_path.read_text()) or {}' \
		'' \
		'meta_keys = {"description", "type", "choices"}' \
		'' \
		'def flatten(node, prefix=""):' \
		'    env = {}' \
		'    if isinstance(node, dict):' \
		'        if "value" in node:' \
		'            env[prefix] = node["value"]' \
		'            return env' \
		'        if "list" in node and isinstance(node["list"], list):' \
		'            env[prefix] = ",".join(str(v) for v in node["list"])' \
		'        for k, v in node.items():' \
		'            if k in meta_keys or k in {"value", "list"}:' \
		'                continue' \
		'            child_prefix = f"{prefix}_{k}" if prefix else k' \
		'            env.update(flatten(v, child_prefix))' \
		'    return env' \
		'' \
		'flat = flatten(data.get("server", {}))' \
		'' \
		'def to_env(k, v):' \
		'    key = k.upper()' \
		'    if isinstance(v, bool):' \
		'        v = "true" if v else "false"' \
		'    return f"{key}={v}"' \
		'' \
		'lines = [to_env(k, v) for k, v in flat.items()]' \
		'env_path.write_text("\n".join(lines) + "\n")' \
		'print(f"Wrote {env_path} with {len(lines)} entries from {cfg_path}")' \
	| $(PY)

up: env
	docker-compose up -d

down:
	docker-compose down

logs:
	@services="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ -n "$$services" ]; then \
		docker-compose logs -f $$services; \
	else \
		docker-compose logs -f; \
	fi

restart:
	@services="$(filter-out $@,$(MAKECMDGOALS))"; \
	if [ -n "$$services" ]; then \
		docker-compose restart $$services; \
	else \
		docker-compose restart; \
	fi

# Allow `make logs api` style invocation without errors for the extra arg.
%:
	@:
