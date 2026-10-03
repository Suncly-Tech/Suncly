"""Run one mock agent on its own: ``python -m suncly.mock_agents honest --port 8701``."""

from __future__ import annotations

import argparse
import sys
import time

from suncly.mock_agents.behaviours import BEHAVIOURS
from suncly.mock_agents.server import MockAgentServer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve a bundled mock A2A agent as a local sandbox."
    )
    parser.add_argument("behaviour", choices=sorted(BEHAVIOURS), help="which mock agent to serve")
    parser.add_argument(
        "--port", type=int, default=0, help="port to listen on (default: any free port)"
    )
    args = parser.parse_args(argv)
    spec = BEHAVIOURS[args.behaviour]
    behaviour = spec.factory()
    with MockAgentServer(behaviour, port=args.port) as server:
        print(f"{args.behaviour} mock agent is running (expected result: {spec.expected})")
        print(f"Agent Card: {server.card_url}")
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
