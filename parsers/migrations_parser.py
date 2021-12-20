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

def init_argparse():
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description="Parse Migration JSON.",
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version="{parser.prog} version 1.0.0"
    )
    parser.add_argument("files", nargs="*")
    return parser

def parse_file(in_file):
    with open(in_file) as json_file:
        data = json.load(json_file)
        return data

def process_data(data):
    for entry in data:
        print("%16s, %20s, %16d, %16d" % (entry['migrationId'], entry['path'], entry['scannerSummary']['progressSummary']['bytesScanned'], entry['clientActivitySummary']['byteCount']))


def main():
    parser = init_argparse()
    args = parser.parse_args()
    for in_file in args.files:
        data = parse_file(in_file)
        process_data(data)


if __name__ == "__main__":
    sys.exit(main())
