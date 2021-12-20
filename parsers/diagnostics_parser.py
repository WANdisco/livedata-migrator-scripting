#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © WANDisco 2021
#
# Author: Colm Dougan, Mark Mc Keown
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

import argparse
import gzip
import json
import sys

def diagnosticSortByTimeStamp(diagnostic):
    return ['timeStamp']


def process_file(in_file, args):
    if in_file.endswith('.gz'):
        return process_file_gz(in_file, args)

    diagnostics = []
    with open(in_file) as file:
        for line in file:
            diagnostics.append(json.loads(line.split()[2]))
    return diagnostics


def process_file_gz(in_file, args):
    diagnostics = []
    with gzip.open(in_file) as file:
        for line in file:
            diagnostics.append(json.loads(line.split()[2]))
    return diagnostics


def init_argparse():
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description="Pretty Diagnostics logs as JSON.",
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version="{parser.prog} version 1.0.0"
    )
    parser.add_argument(
        "-k", "--kind", action="store",
        help='filter Diagnostics by kind, eg --kind NetworkStatus or --kind NetworkStatus/connectionTotals/10.69.102.183'
    )

    parser.add_argument("files", nargs="*")
    return parser


def diagnostics_print_by_kind(diagnostics, args):
    matches = []
    for diagnostic in diagnostics:
       matches.extend(filter_by_kind(diagnostic['diagnostics'], args.kind))
    print(json.dumps(matches, indent=4))


def filter_by_diagnostic_path(diagnostic_type, path, matches, timeStamp):
    if not path:
        return

    if path[0] not in diagnostic_type:
        return

    if len(path) == 1:
       if isinstance(diagnostic_type[path[0]], dict):
          diagnostic_type[path[0]]['timeStamp'] = timeStamp
          matches.append(diagnostic_type[path[0]])
       else:
          matches.append(diagnostic_type[path[0]])
       return

    key = path.pop(0)
    filter_by_diagnostic_path(diagnostic_type[key], path, matches, timeStamp)


def filter_by_kind_diagnostic_entry(diagnostic_type, kind, matches, timeStamp):
    if "/" not in kind:
        if diagnostic_type['kind'] == kind:
            matches.append(diagnostic_type)
        return

    path = kind.split("/")
    if diagnostic_type['kind'] == path[0]:
          path.pop(0)
          filter_by_diagnostic_path(diagnostic_type, path, matches, timeStamp)
    

def filter_by_kind(diagnostic, kind):
    matches = []
    for diagnostic_entry in diagnostic:
        filter_by_kind_diagnostic_entry(diagnostic_entry, kind, matches, diagnostic_entry['timeStamp'])

    return matches


def diagnostics_print(diagnostics):
    print(json.dumps(diagnostics, indent=4))


def main():
    parser = init_argparse()
    args = parser.parse_args()
    diagnostics = []
    for in_file in args.files:
        diagnostics.extend(process_file(in_file, args))
    diagnostics.sort(key=diagnosticSortByTimeStamp)
    if args.kind:
        diagnostics_print_by_kind(diagnostics, args)
    else:
        diagnostics_print(diagnostics)


if __name__ == "__main__":
    sys.exit(main())
