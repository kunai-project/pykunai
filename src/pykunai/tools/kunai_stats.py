import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

STDIN_INPUT = "-"


def format_bytes(size: float) -> str:
    # Define the units and their corresponding sizes
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]

    # Loop through each unit
    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} YB"


@dataclass
class Stats:
    counts: Dict[Tuple[int, str], int] = field(default_factory=dict)
    sizes: Dict[Tuple[int, str], int] = field(default_factory=dict)
    count: int = 0
    size: int = 0
    first: Optional[datetime] = None
    last: Optional[datetime] = None

    def add(self, line: bytes) -> None:
        event = json.loads(line)
        timestamp = datetime.fromisoformat(event["info"]["utc_time"])
        key = (event["info"]["event"]["id"], event["info"]["event"]["name"])

        self.counts[key] = self.counts.get(key, 0) + 1
        self.sizes[key] = self.sizes.get(key, 0) + len(line)
        self.count += 1
        self.size += len(line)

        if self.first is None:
            self.first = timestamp
        self.last = timestamp

    def duration(self) -> timedelta:
        if self.first is None or self.last is None:
            return timedelta(0)
        return self.last - self.first


def print_stats(stats: Stats) -> None:
    duration = stats.duration()
    seconds = duration.total_seconds()
    # a single event (or identical timestamps) gives no duration to compute rates on
    has_duration = seconds > 0

    for key in sorted(stats.counts, key=lambda k: k[0]):
        count = stats.counts[key]
        size = stats.sizes[key]
        eps = f"{count / seconds:.2f} e/s" if has_duration else "n/a e/s"
        print(f"{key[1]}:".ljust(20), end=" ")
        print(f"{count} ->".rjust(10), end=" ")
        print(eps.rjust(12), end=" ")
        print(format_bytes(size).rjust(12), end=" ")
        print(f"(avg {format_bytes(size / count)})")

    tot_eps = f"{stats.count / seconds:.2f} e/s" if has_duration else "n/a e/s"
    tot_bps = f"{format_bytes(stats.size / seconds)}/s" if has_duration else "n/a B/s"
    print()
    print("Totals")
    print("Events:".ljust(20), end=" ")
    print(f"{stats.count} ->".rjust(10), end=" ")
    print(tot_eps.rjust(12))
    # size in bytes
    print("Bytes:".ljust(20), end=" ")
    print(f"{format_bytes(stats.size)} ->".rjust(10), end=" ")
    print(tot_bps.rjust(12))
    # time
    print("Sample Duration:".ljust(20), end=" ")
    print(f"{duration}".rjust(10))


def main() -> None:
    parser = argparse.ArgumentParser(description="Makes statistics about kunai logs")
    parser.add_argument(
        "-r",
        "--refresh",
        default=300,
        type=int,
        help="Refresh rate in numbers of events (only when reading from stdin)",
    )
    parser.add_argument(
        "kunai_json_input", help="Input file in json line format or stdin with -"
    )

    args = parser.parse_args()

    is_live = args.kunai_json_input == STDIN_INPUT
    # binary mode so that sizes are measured in bytes, newline included
    if is_live:
        input_file = sys.stdin.buffer
    else:
        input_file = open(args.kunai_json_input, "rb")

    stats = Stats()
    with input_file:
        for line in input_file:
            stats.add(line)
            if is_live and stats.count % args.refresh == 0:
                os.system("clear")
                print_stats(stats)

    if is_live:
        os.system("clear")
    print_stats(stats)


if __name__ == "__main__":
    main()
