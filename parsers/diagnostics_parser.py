#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © WANDisco 2021-2022
#
# Author: Colm Dougan, Mark Mc Keown, Robert Clarke
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function, with_statement

import argparse
import gzip
import json
import csv
import os
import sys
import time
import datetime
import re
import signal
from multiprocessing import Pool
from operator import itemgetter

if sys.version_info.major == 2:
    from io import BytesIO as StringIO
else:
    from io import StringIO

SIMPLE_TYPES = [str, int, float, complex, bool]
if sys.version_info.major == 2:
    SIMPLE_TYPES.append(unicode)


def process_file(in_file):
    if in_file.endswith('.gz'):
        with gzip.open(in_file) as file:
            return decode_file(file, in_file)

    with open(in_file) as file:
        return decode_file(file, in_file)


def decode_file(file, filename):
    diagnostics = []
    for i, line in enumerate(file):
        try:
            diagnostics.append(json.loads(line.split()[2]))
        except ValueError:
            print("Failed to decode line", i, "of file:", filename, file=sys.stderr)
    return diagnostics


def init_argparse():
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description="Pretty Diagnostics logs as JSON or CSV.",
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version= "WANdisco %(prog)s version 1.1.0"
    )
    parser.add_argument(
        "-k", "--kind", action="store",
        help='filter Diagnostics by kind, eg --kind NetworkStatus or --kind NetworkStatus/connectionTotals/10.69.102.183'
    )

    parser.add_argument(
        "-o", "--output", action="store",
        help='Output format (Default json)',
        choices=["json", "csv"],
        default="json",
    )

    parser.add_argument(
        "-n", action="store",
        help='Number of threads to spawn. By default this will equal the core count of the host machine',
        default=None,
        type=int,
    )

    parser.add_argument("files", nargs="*")
    return parser


def filter_by_diagnostic_path(diagnostic_type, path, matches, timestamp):
    if not path:
        return

    if path[0] not in diagnostic_type:
        return

    if len(path) == 1:
        if isinstance(diagnostic_type[path[0]], dict):
            diagnostic_type[path[0]]['timeStamp'] = timestamp
            matches.append(diagnostic_type[path[0]])
        else:
            matches.append(diagnostic_type[path[0]])
        return

    key = path.pop(0)
    filter_by_diagnostic_path(diagnostic_type[key], path, matches, timestamp)


def filter_by_kind_diagnostic_entry(diagnostic_type, kind, matches, timestamp):
    if "/" not in kind:
        if diagnostic_type['kind'] == kind:
            matches.append(diagnostic_type)
        return

    path = kind.split("/")
    if diagnostic_type['kind'] == path[0]:
        path.pop(0)
        filter_by_diagnostic_path(diagnostic_type, path, matches, timestamp)


def filter_by_kind(diagnostic, kind):
    matches = []
    for diagnostic_entry in diagnostic:
        filter_by_kind_diagnostic_entry(diagnostic_entry, kind, matches, diagnostic_entry['timeStamp'])

    return matches


def diagnostics_format_by_kind(diagnostics, args, first):
    matches = []
    for diagnostic in diagnostics:
        matches.extend(filter_by_kind(diagnostic['diagnostics'], args.kind))
    return diagnostics_format(matches, args, first)


def diagnostics_format(diagnostics, args, first):
    if args.output == "json":
        return diagnostics_format_json(diagnostics, first)

    elif args.output == "csv":
        return diagnostics_format_csv(diagnostics, first)


def diagnostics_format_json(diagnostics, first):
    indent = 4

    with StringIO() as sio:
        for i, d in enumerate(diagnostics):
            if not first or i > 0:
                sio.write(",")
            sio.write("".join([" " * indent + line + "\n" for line in json.dumps(d, indent=indent).split("\n")]))

        return sio.getvalue()


def diagnostics_format_csv(diagnostics, first):
    with StringIO() as sio:
        timestamp_key = "timeStamp"

        field_names = []

        for key, val in diagnostics[0].items():
            if type(val) in SIMPLE_TYPES:
                field_names.append(key)

        field_names.remove(timestamp_key)
        field_names = [timestamp_key] + field_names  # Put timestamp first

        writer = csv.DictWriter(sio, field_names, extrasaction='ignore')
        if first:
            writer.writeheader()

        for d in diagnostics:
            d[timestamp_key] = datetime.datetime.fromtimestamp(d[timestamp_key] / 1000.0).isoformat()
            writer.writerow(d)

        return sio.getvalue().rstrip("\n")


def format_file(arg):
    in_file, args, n = arg

    diagnostics = process_file(in_file)
    diagnostics.sort(key=itemgetter("timeStamp"))

    if args.kind is not None:
        return diagnostics_format_by_kind(diagnostics, args, n == 0)
    else:
        return diagnostics_format(diagnostics, args, n == 0)


def log_file_sort_key(filename):

    if filename.endswith("diagnostics.log"):
        return float("inf")

    date_pattern = "([0-9]{4}-[0-9]{2}-[0-9]{2})\\.([0-9]+)"

    try:
        gs = next(re.finditer(date_pattern, filename)).groups()
    except StopIteration:
        # File name has been mangled and no longer contains date, try file modified time (which may not be correct)
        return os.stat(filename).st_mtime * 10000

    return time.mktime(time.strptime(gs[0], "%Y-%m-%d")) * 10000 + int(gs[1])


def main():
    parser = init_argparse()
    args = parser.parse_args()

    if args.output == "csv" and args.kind is None:
        raise ValueError("Must specify diagnostic kind for CSV output.")

    in_files = sorted(args.files, key=log_file_sort_key)

    if args.output == "json":
        print("[")

    if sys.version_info.major == 2:
        # Work around SIGINT multiprocessing bug in Python 2
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    p = Pool(args.n)

    if sys.version_info.major == 2:
        signal.signal(signal.SIGINT, original_sigint_handler)

    try:
        for string in p.imap(format_file,
                             ((in_file, args, n) for n, in_file in enumerate(in_files))):
            print(string)
    finally:
        p.close()

    if args.output == "json":
        print("]")


if __name__ == "__main__":
    sys.exit(main())
