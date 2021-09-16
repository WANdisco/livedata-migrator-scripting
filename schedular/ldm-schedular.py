#!/usr/bin/env python

# Copyright © WANDisco 2021
#
# Author: Colm Dougan
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
import base64
import datetime
import json
import sys

if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse

API_ENDPOINT = "http://localhost:18080"

HEADERS = {}
QUEUED_STATE = 'NONSCHEDULED'
RUNNING_STATES = ['RUNNING', 'SCHEDULED']
COMPLETED_STATES = ['LIVE', 'COMPLETED']


class Migration(object):
    def __init__(self, migrationId=None, internalId=None, path=None, state=None, migrationStartTime=None, **kwargs):
        self.migrationId = migrationId
        self.internalId = internalId
        self.path = path
        self.state = state
        self.migrationStartTime = migrationStartTime

    def __repr__(self):
        return "Migration(" + str(self.__dict__) + ")"


def build_auth_header(username, password):
    credentials = ('%s:%s' % (username, password))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))
    return 'Basic %s' % encoded_credentials.decode("ascii")


def get_http_connection(endpoint):
    url = urlparse(endpoint)
    if url.scheme == 'https':
        print("making https connecting to %s" % url.netloc)
        return HTTPSConnection(url.netloc)

    print("making http connecting to %s" % url.netloc)
    return HTTPConnection(url.netloc)


def doHttp(verb, path):
    conn = get_http_connection(API_ENDPOINT)
    conn.request(verb, path, None, HEADERS)
    return conn.getresponse()


def list_migrations():
    resp = doHttp("GET", "/migrations")
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    listJson = resp.read()
    items = json.loads(listJson)

    migrations = []
    for row in sorted(items, key=lambda x: x['migrationStartTime']):
        migrations.append(Migration(**row))

    return migrations


def start_migration(mig):
    resp = doHttp("POST", "/migrations/" + mig.internalId + "/start")
    if resp.status == 200:
        print("SUBMITTED %s" % (mig,))
    else:
        raise ValueError(resp.status, resp.reason)


def priority_for_path(path, priorities, fallback):
    try:
        return priorities.index(path)
    except ValueError:
        return fallback


def scheduler(require_n_running, priorities):
    running_count = 0
    completed_count = 0
    candidate_to_run = []

    migrations = list_migrations()
    default_priority = len(priorities) + 1

    for mig in migrations:
        if mig.state == QUEUED_STATE:
            priority = priority_for_path(mig.path, priorities, default_priority)
            # print("path %s has priority %d" % (mig.path, priority))

            # derive a sorting key based on the priority and then the
            # migrationStartTime so we can process these in the desired
            # order
            sort_key = (priority, mig.migrationStartTime)
            candidate_to_run.append((sort_key, mig))
        elif mig.state in RUNNING_STATES:
            running_count += 1
        elif mig.state in COMPLETED_STATES:
            completed_count += 1
        else:
            print("OTHER", mig)

    print("==================================================")
    print(" now:        %s" % datetime.datetime.now())
    print(" running:    %d" % running_count)
    print(" completed:  %d" % completed_count)
    print(" queued:     %d" % len(candidate_to_run))
    print(" priorities: %r" % priorities)
    print("==================================================")

    will_start = []
    if running_count < require_n_running:
        n_to_start = min(require_n_running - running_count, len(candidate_to_run))
        will_start = [m for _, m in sorted(candidate_to_run)[:n_to_start]]

    print(" require_running: %d" % require_n_running)
    print(" will_start: %d" % len(will_start))

    for mig in will_start:
        print("######### starting", mig, "...")
        start_migration(mig)

    return 0


def usage(text):
    print("usage: %s" % text)
    return sys.exit(1)


def main():
    global API_ENDPOINT
    global HEADERS

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--howmany', type=int, required=True, help='''Ensure that HOWMANY migrations are running at once. If there are queued
migrations (those created without --auto-start) this script will "run"
them to a max of HOWMANY.
''')
    parser.add_argument('--priority-list', help='''Optional filename of paths which define a custom priority for migration
run order.  The file ordering defines the priority.  If no priority list is
supplied or if a particular path is missing from the file the priority will be
dictated by the creation time

The file format is one path per line. example:

cat << EOF > priorities.txt
/repl3
/repl1
/src
EOF
''')
    parser.add_argument('--username', help='Username for basic authentication (if enabled)')
    parser.add_argument('--password', help='Password for bsaic authentication (if enabled)')
    parser.add_argument('--endpoint', default=API_ENDPOINT, help='''Override API endpoint (e.g. for https or custom port)
(default: %s)

''' % API_ENDPOINT)
    parser.add_argument('--debug', action='store_true')

    # parse the args and call whatever function was selected                                                      
    args = parser.parse_args()
    # print("ARGS", args)

    priorities = []
    if args.priority_list:
        with open(args.priority_list, 'r') as f:
            priorities = [line.rstrip() for line in f]

    if args.username:
        HEADERS['Authorization'] = build_auth_header(args.username, args.password)

    if args.debug:
        HTTPConnection.debuglevel = 1

    API_ENDPOINT = args.endpoint

    return scheduler(args.howmany, priorities)


if __name__ == "__main__":
    sys.exit(main())
