import os

import argparse
import toml
import urllib3

from pymisp import PyMISP
from pykunai.event import Query
from pykunai.utils import decode_events, sha256_file

from pykunai.misp.export import KunaiMispEvent


def main() -> None:
    default_config = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "config.toml")
    )

    parser = argparse.ArgumentParser(description="Push Kunai analysis to MISP")
    parser.add_argument(
        "-c",
        "--config",
        default=default_config,
        type=str,
        help=f"Configuration file. Default: {default_config}",
    )
    parser.add_argument(
        "--no-recurse",
        action="store_false",
        help="Does a recursive search (goes to child processes as well)",
    )
    parser.add_argument(
        "-s", "--silent", action="store_true", help="Silent HTTPS warnings"
    )
    parser.add_argument("-H", "--hashes", type=str, help="Search by hash (comma split)")
    parser.add_argument("-F", "--file", type=str, help="Hash file and search by hash")
    parser.add_argument(
        "-G", "--guuid", type=str, help="Search by task guuid (comma split)"
    )
    parser.add_argument(
        "KUNAI_JSON_INPUT",
        default="-",
        help="Input file in json line format or stdin with -",
    )

    args = parser.parse_args()

    # silent https warnings
    if args.silent:
        urllib3.disable_warnings()

    if not os.path.isfile(args.config):
        parser.error(f"no such file or directory: {args.config}")

    config = toml.load(open(args.config, encoding="utf-8"))

    misp_config = config["misp"]

    misp = PyMISP(
        url=misp_config["url"], key=misp_config["key"], ssl=misp_config["ssl"]
    )

    query = Query(args.no_recurse)

    if args.file is not None:
        query.add_hashes([sha256_file(args.file)])
    if args.guuid is not None:
        query.add_guids(args.guuid.split(","))

    # we need to have a starting point for analysis
    # to prevent misp event from containing junk
    if query.is_empty():
        parser.error("one of --guuid|--file|--hashes is required")

    trace = [e for e in decode_events(args.KUNAI_JSON_INPUT) if query.match(e)]

    kunai_analysis_event = KunaiMispEvent(trace, misp)

    if args.file is not None:
        kunai_analysis_event.with_sample(args.file)

    misp.add_event(kunai_analysis_event.into_misp_event())


if __name__ == "__main__":
    main()
