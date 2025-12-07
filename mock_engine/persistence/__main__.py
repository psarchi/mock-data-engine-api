from __future__ import annotations

import sys


def main():
    """Dispatch to watcher, batch_sync, or metrics_collector based on command."""
    if len(sys.argv) < 2:
        print("Usage: python -m mock_engine.persistence [watcher|batch_sync|metrics_collector]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "watcher":
        from mock_engine.persistence.watcher import main as watcher_main
        import asyncio
        asyncio.run(watcher_main())
    elif command == "batch_sync":
        from mock_engine.persistence.batch_sync import main as batch_sync_main
        import asyncio
        asyncio.run(batch_sync_main())
    elif command == "metrics_collector":
        from mock_engine.persistence.metrics_collector import main as metrics_collector_main
        import asyncio
        asyncio.run(metrics_collector_main())
    else:
        print(f"Unknown command: {command}")
        print("Available commands: watcher, batch_sync, metrics_collector")
        sys.exit(1)


if __name__ == "__main__":
    main()
