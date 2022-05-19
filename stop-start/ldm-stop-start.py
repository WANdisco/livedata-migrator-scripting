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

from __future__ import print_function
import argparse
import base64
import sys
import re
import json
import datetime
import logging

if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
    from urllib import urlencode, quote_plus
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse, urlencode, quote_plus


def urlencode_string(string):
    return quote_plus(string)


def get_http_connection(endpoint):
    url = urlparse(endpoint)
    if url.scheme == 'https':
        return HTTPSConnection(url.netloc)
    return HTTPConnection(url.netloc)


def build_auth_header(username, password):
    credentials = ('%s:%s' % (username, password))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))
    return 'Basic %s' % encoded_credentials.decode("ascii")


def doHttp(verb, config, path):
    conn = get_http_connection(config['api_endpoint'])
    headers = {}
    if config['username']:
        headers['Authorization'] = build_auth_header(config['username'], config['password'])
    conn.request(verb, path, None, headers)
    return conn.getresponse()


def get_migrations(config):
    resp = doHttp("GET", config, "/migrations")
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    return json.loads(resp.read())


def stop_migration(migration, config):
    encode_migration_id = urlencode_string(migration['migrationId'])
    resp = doHttp("POST", config, "/migrations/" + encode_migration_id + "/stop")
    if resp.status == 200:
        print("Migration [" + migration['migrationId'] + "][" + migration['path'] +"] stopped")
    else:
        error = json.loads(resp.read())
        print("Migration [" + migration['migrationId'] + "][" + migration['path'] +"] not stopped. " ,resp.status, error['message'])
    return 


def stop_migration_by_pattern(config, args):
    migrations = get_migrations(config)
    for migration in migrations:
      migration_id = migration['migrationId']
      if args.pattern and not re.search(args.pattern, migration_id):
           print("Skipping migration [" + migration['migrationId'] + "], does not match " + args.pattern)
           continue
      if migration['state'] == 'RUNNING' or migration['state'] == 'LIVE':
         stop_migration(migration, config)
      else:
         print("Not stopping Migration [" + migration['migrationId'] + "][" + migration['path'] +"] as current state is [" + migration['state']  + "]")

    return

def stop_migrations(config, args):
    if args.pattern:
       # Need to stop migrations individually
       stop_migration_by_pattern(config, args)
       return

    resp = doHttp("POST", config, "/migrations/stop")
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    print("Stopped migrations. Response code: ", resp.status )
    return


def start_migration(migration, config):
    encode_migration_id = urlencode_string(migration['migrationId'])
    resp = doHttp("POST", config, "/migrations/" + encode_migration_id + "/start")
    if resp.status == 200:
        print("Migration [" + migration['migrationId'] + "][" + migration['path'] +"] started")
    else:
        error = json.loads(resp.read())
        print("Migration [" + migration['migrationId'] + "][" + migration['path'] +"] not started. " ,resp.status, error['message'])
    return 


def start_migrations(config, args):
    migrations = get_migrations(config)
    for migration in migrations:
      migration_id = migration['migrationId']
      if args.pattern and not re.search(args.pattern, migration_id):
        print("Skipping migration " + migration['migrationId'] + ", does not match " + args.pattern)
        continue

      if migration['state'] != 'STOPPED':
        print("Not starting Migration [" + migration['migrationId'] + "][" + migration['path'] +"] as current state is [" + migration['state']  + "]")
      else:
        start_migration(migration, config)
    return


def main():
    parser = argparse.ArgumentParser(
         description="Start or Stop all Migrations.",
    )

    subparsers = parser.add_subparsers(dest='command',help='stop or start' )
    # parser for the "stop" command
    parser_list = subparsers.add_parser('stop')
    # parser for the "start" command
    parser_list = subparsers.add_parser('start')

    parser.add_argument('--config', action = 'store', required=True,  help='Configuration file of format: {"api_endpoint" : "http://localhost:18080", "username" : "foo", "password" : "bar"}')
    parser.add_argument('--pattern', action = 'store', required=False,  help='Pattern to filter and match Migrations.')
    parser.add_argument('--debug', action='store_true', help='Enable HTTP Debug.')
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = json.load(f)

    # Test compile the pattern, will throw exception
    if args.pattern:
        try:
           re.compile(args.pattern)
        except Exception as e:
           print('Bad pattern "' + args.pattern  +'": ', e)
           exit(1)

    if args.debug:
        HTTPConnection.debuglevel = 1
        config['debug'] = True
        logging.basicConfig(level=logging.DEBUG)

    if args.command == 'start':
       return start_migrations(config, args)
    elif args.command == 'stop':
       return stop_migrations(config, args)
    else:
       return


if __name__ == "__main__":
    sys.exit(main())
