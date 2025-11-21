"""Async throughput probe against the schema generate endpoint.

Runs concurrent requests for a fixed duration, discarding response bodies to
gauge max request rate. Chaos stays on (default config).
"""
from __future__ import annotations

import asyncio
import time
import urllib.parse

import aiohttp

# Tweak these for your target
BASE_URL = "http://127.0.0.1:8000/v1/schemas/ga4/generate"
COUNT = 1
SEED = 123
DURATION_SEC = 60
CONCURRENCY = 32


async def worker(session: aiohttp.ClientSession, url: str, deadline: float, stats: dict) -> None:
    while time.monotonic() < deadline:
        t0 = time.monotonic()
        try:
            async with session.get(url) as resp:
                body = await resp.read()
            stats["hits"] += 1
            stats["bytes"] += len(body)
            stats["latencies"].append(time.monotonic() - t0)
        except Exception as exc:  # noqa: BLE001
            stats["errors"] += 1
            await asyncio.sleep(0.05)


async def main_async() -> int:
    params = {"count": COUNT, "seed": SEED}
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    deadline = time.monotonic() + DURATION_SEC
    stats = {"hits": 0, "errors": 0, "bytes": 0, "latencies": []}

    print(f"Benchmarking {url} for {DURATION_SEC}s with concurrency={CONCURRENCY} ...")
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(worker(session, url, deadline, stats)) for _ in range(CONCURRENCY)]
        await asyncio.gather(*tasks)

    elapsed = DURATION_SEC
    rps = stats["hits"] / elapsed if elapsed else 0.0
    latencies = stats["latencies"]
    avg = (sum(latencies) / len(latencies) * 1000) if latencies else 0.0
    p50 = sorted(latencies)[len(latencies) // 2] * 1000 if latencies else 0.0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] * 1000 if latencies else 0.0
    print(
        f"\nelapsed={elapsed:.2f}s hits={stats['hits']} errors={stats['errors']} "
        f"rps={rps:.2f} bytes={stats['bytes']}"
    )
    print(f"latency_ms avg={avg:.2f} p50={p50:.2f} p95={p95:.2f}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
