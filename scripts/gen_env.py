from __future__ import annotations

import argparse
import pathlib
from typing import Any

import yaml

META_KEYS = {"description", "type", "choices"}


def flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested config dict into a flat env mapping."""
    env: dict[str, Any] = {}
    if isinstance(node, dict):
        if "value" in node:
            env[prefix] = node["value"]
            return env
        if "list" in node and isinstance(node["list"], list):
            env[prefix] = ",".join(str(v) for v in node["list"])
        for key, val in node.items():
            if key in META_KEYS or key in {"value", "list"}:
                continue
            child_prefix = f"{prefix}_{key}" if prefix else key
            env.update(flatten(val, child_prefix))
    return env


def to_env_line(key: str, value: Any) -> str:
    """Format a single env line."""
    env_key = key.upper()
    if isinstance(value, bool):
        value = "true" if value else "false"
    return f"{env_key}={value}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate .env from server config")
    parser.add_argument("--config", default="config/default/server.yaml")
    parser.add_argument("--output", default=".env")
    args = parser.parse_args()

    cfg_path = pathlib.Path(args.config)
    env_path = pathlib.Path(args.output)

    data = yaml.safe_load(cfg_path.read_text()) or {}
    flat = flatten(data.get("server", {}))

    lines = [to_env_line(k, v) for k, v in flat.items()]
    env_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {env_path} with {len(lines)} entries from {cfg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
