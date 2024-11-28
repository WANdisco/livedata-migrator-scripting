#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © Cirata 2024
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
import duckdb
import json
import os
import sys

def process_state(args, state):
    relation1 = duckdb.sql("SELECT * EXCLUDE (timestamp) FROM read_ndjson_auto('" + state['first_discrepancy'] + "')").set_alias("relation1")
    relation2 = duckdb.sql("SELECT * EXCLUDE (timestamp) FROM read_ndjson_auto('" + state['second_discrepancy'] + "')").set_alias("relation2")
    print("First Set of Discrepancies: %s" % (relation1.aggregate('count()').fetchone()))
    if args.debug:
       print("%s" % (relation1.order('sourcePath').sql_query()))
    relation1.order('sourcePath').show()

    print("Second Set of Discrepancies: %s" % (relation2.aggregate('count()').fetchone()))
    if args.debug:
       print("%s" % (relation2.order('sourcePath').sql_query()))
    relation2.order('sourcePath').show()

    print("Unresolved Discrepancies: %s" % (relation1.intersect(relation2).aggregate('count()').fetchone()))
    if args.debug:
       print("%s" % (relation1.intersect(relation2).order('sourcePath').sql_query()))
    relation1.intersect(relation2).order('sourcePath').show()
    if args.output is not None:
        file = args.output + ".unresolved.csv"
        relation1.intersect(relation2).order('sourcePath').write_csv(file)

    print("Discrepancies Resolved: %s" % (relation1.except_(relation2).aggregate('count()').fetchone()))
    if args.debug:
       print("%s" % (relation1.except_(relation2).order('sourcePath').sql_query()))
    relation1.except_(relation2).order('sourcePath').show()
    if args.output is not None:
        file = args.output + ".resolved.csv"
        relation1.except_(relation2).order('sourcePath').write_csv(file)

    print("New Discrepancies: %s" % (relation2.except_(relation1).aggregate('count()').fetchone()))
    if args.debug:
       print("%s" % (relation2.except_(relation1).order('sourcePath').sql_query()))
    relation2.except_(relation1).order('sourcePath').show()
    if args.output is not None:
        file = args.output + ".new.csv"
        relation2.except_(relation1).order('sourcePath').write_csv(file)
        


def do_delta(args):
    if args.debug:
       print("Doing delta %s" % args)
    state = dict()
    summary = os.path.join(args.first, 'summary.json')
    with open(summary, 'r') as file:
       state['first_summary'] = json.load(file)
    state['first_discrepancy'] = os.path.join(args.first, 'verification-discrepancy.jsonl.gz') 
    summary = os.path.join(args.second, 'summary.json')
    with open(summary, 'r') as file:
       state['second_summary'] = json.load(file)
    state['second_discrepancy'] = os.path.join(args.second, 'verification-discrepancy.jsonl.gz') 
    process_state(args, state)

def check_is_verification(path):
    if not os.path.isdir(path):
       raise Exception("Path %s does not exist or is not a dirctory." % (path))
    summary = os.path.join(path, 'summary.json')
    if not os.path.isfile(summary):
       raise Exception("Verification summary file %s does not exist." % (summary))
    discrepancy = os.path.join(path, 'verification-discrepancy.jsonl.gz')
    if not os.path.isfile(discrepancy):
       raise Exception("Verification discrepancy file %s does not exist." % (discrepancy))

def check_args(args):
    if args.debug:
       print("Checking args %s" % (args))
    check_is_verification(args.first)
    check_is_verification(args.second)

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument(
       '--output',
       dest='output',
       action='store',
       help='Store the output into csv files.'
    )
    parser.add_argument(
        '--first',
        required=True,
        dest='first',
        action='store', 
        help='First verification report to check against.'
    )
    parser.add_argument(
        '--second',
        required=True,
        dest='second',
        action='store', 
        help='Second verification report to check against.'
    )
    args = parser.parse_args()
    check_args(args)
    do_delta(args)

if __name__ == "__main__":
    sys.exit(main())
