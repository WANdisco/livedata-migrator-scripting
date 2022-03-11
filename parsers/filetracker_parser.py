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
import json
import sys
import gzip


def print_column_header():
    print('%40s %12s %8s %12s %12s %8s %12s %8s' % ('Path', 'Time Start', 'Offset', 'Bytes/s', 'File Size', 'Time(s)', 'Transferred', 'Attempt'))


def trackerSortByStart(tracker):
    return tracker['StartTime']


def process_file(in_file, args):
    if in_file.endswith('.gz'):
        return process_file_gz(in_file, args)

    trackers = []
    with open(in_file) as file:
        for line in file:
            trackers.append(json.loads(line.split(maxsplit=4)[4]))
    return trackers

def process_file_gz(in_file, args):
    trackers = []
    with gzip.open(in_file) as file:
        for line in file:
            trackers.append(json.loads(line.split(maxsplit=4)[4]))
    return trackers


def process_trackers_column(trackers, args):
    print_column_header()
    if not trackers:
       return
    firstStartTime = trackers[0]['StartTime']
    for tracker in trackers:
        process_tracker_column(firstStartTime, tracker, args)


def process_tracker_column(firstStartTime, tracker, args):
    up_to_last_40_slice = slice(-40, None)
    print('%40s %12d %8d %12d %12d %8d %12s %8d' % (tracker['Path'][up_to_last_40_slice], tracker['StartTime']/1000,  (tracker['StartTime'] - firstStartTime)/1000, tracker['BytesPerSecond'], tracker['FileLength'], (tracker['CompleteTime'] - tracker['StartTime']) / 1000, tracker['IsSuccessful'], tracker['AttemptCount'] ))


def process_trackers_json(trackers, args):
    print(json.dumps(trackers, indent=4, sort_keys=True))


def init_argparse():
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description="Pretty print LiveData Migrator FileTracker logs.",
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version="{parser.prog} version 1.0.0"
    )
    parser.add_argument('-c',
                       '--column',
                       action='store_true',
                       help='display FileTacker in column format.')
    parser.add_argument("files", nargs="*")
    return parser


def main():
    parser = init_argparse()
    args = parser.parse_args()
    trackers = []
    for in_file in args.files:
        trackers.extend(process_file(in_file, args))
    trackers.sort(key=trackerSortByStart)
    if args.column:
       process_trackers_column(trackers, args)
    else:
       process_trackers_json(trackers, args)


if __name__ == "__main__":
    sys.exit(main())
