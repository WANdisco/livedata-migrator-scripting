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
import base64
import sys
import json
import datetime
import logging

if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
    from urllib import urlencode
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse, urlencode

# A day in seconds.
DAY = 24 * 60 * 60
# Cannot generate daily usage older than 59 days, we can collect for 
# NO_DAYS_TO_TRACK + 1 days, but since we get total migrated
# we need to subtract the previous days total to get the 
# amount migrated for a day.
NO_DAYS_TO_TRACK = 59
# Default number of days to report
DEFAULT_NO_DAYS_TO_REPORT = 29

# Workaround for Python 2.7 not having datetime.timezone
class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)

# Use utc in place of datetime.timezone.utc
utc = UTC()


def yesterday_timestamp():
    # The first full day we can calculate usage for is yesterday, we work
    # against epcoh time.
    epoch = datetime.datetime(1970,1,1,tzinfo=utc)
    today = datetime.date.today()
    today_epoch = (datetime.datetime(today.year, today.month, today.day, tzinfo=utc)  - epoch).total_seconds()
    return int(today_epoch) - DAY


def generate_days_epochs(args):
    # Starting from yesterday we move back in time to generate
    # a list of days we can generate usage for.
    days = []
    for i in range(0, args.days + 1):
         days.append(yesterday_timestamp() - (i * DAY))
    return days


def timestamp_to_date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, utc).date()


def get_stats_for_day(day, migration_stats):
    # The list if migration_stats has the total amount of data migrated for a migration up to
    # the timestamp. As we move through the series of migration_stats we are moving back in time.
    # We move back through the stats until we find the first entry for the day we are interested in
    # and use the total there as the value for data migrated up to that day. 
    # Note some days will have no entry, this indicates no data was transferred for that day - so if
    # we move past a day we use the next previous entry for that day.
    day_end = day + DAY - 1;
    for migration_stat in migration_stats:
         timestamp = migration_stats_get_timestamp(migration_stat)
         if timestamp > day_end:
              # Have not found the day that matches this stats entry, continue to move back in time.
              continue
         if timestamp < day_end and timestamp >= day:
              # Found the first stats entry in the list for the day - the last recorded
              # value for that day.
              # This can be used as the value for the day.
              return migration_stats_get_bytes(migration_stat)
         if timestamp < day:
              # We have moved past the day we are interested in.
              # No stats recoded for this day, no increase in the total migrated for this day
              # over previous days. 
              # We can use migration_stat value we have reached for this day, even though
              # it is for a previous day - the total has not increased since then. 
              # Essentially it is the latest entry before the day we are interested 
              # in.
              return migration_stats_get_bytes(migration_stat)  
    return 0  

def process_stats(days, migration_stats, args):
    # Generate a dict with which maps the day to the amount migrated up to that day.
    # The migration_stats are a serious of total amount of data transferred taken at
    # different times - this needs to be broken down into totals for days.
    daily_totals = {}
    for day in days:
        daily_totals[day] = get_stats_for_day(day, migration_stats)
    return daily_totals


def migration_stats_get_timestamp(migration_stats):
    # Timestamps in the migration_stats are in ms since the epoch.
    return int((migration_stats['timeStamp'])/1000)


def migration_stats_get_bytes(migration_stats):
    return migration_stats['migrationStats']['successfulBytesMigrated']


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


def daily_totals_to_usage(days, daily_totals, args):
    daily_usage = {}
    # To get the daily usage we subtract the total data migrated for previous day.
    for day in range(0, args.days):
        daily_usage[days[day]] = daily_totals[days[day]] - daily_totals[days[day + 1]]
    return daily_usage 


def process_migration_stats(days, migration_id, migration_state, migration_stats, args):
    daily_totals = process_stats(days, migration_stats, args)
    daily_usage = daily_totals_to_usage(days, daily_totals, args)
    stats_string = migration_id + ", " + migration_state + ", "
    if args.date:
        for day in days:
             if str(datetime.datetime.fromtimestamp(day, utc).date()) == args.date:
                 stats_string = stats_string + str(daily_usage[day])
                 break
        return stats_string 

    for day in range(0, args.days):
        stats_string = stats_string + str(daily_usage[days[day]]) + ", "
    # Remove the last extra comma
    return stats_string[:-2]
    

def get_migration_stats(days, migration_id, config):
    endpoint = "/stats/" + migration_id
    resp = doHttp("GET", config, endpoint)
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)
  
    migration_stats_json = resp.read()
    return json.loads(migration_stats_json)


def daily_usage(config, args):
    migrations = get_migrations(config)
    # If search is limited to one migration then filter out the unwanted migrations here - 
    # if the migration provided does not exist then there will be empty output.
    if args.migration: 
        filtered = filter(lambda migration: migration['migrationId'] == args.migration, migrations)
        migrations = filtered
  
    days = generate_days_epochs(args)
    # Create a header - we ignore the last day as we cannot create a usage for it, we only have the total
    # amount migrated up to that day.
    header = "Migration, State, " + ", ".join([str(datetime.datetime.fromtimestamp(day, utc).date()) for day in days[:-1]])
    if args.date:
        header = "Migration, State, " + args.date 
    print(header)
    # For each migration retrieve its stats and print.
    for migration in migrations:
        migration_id = migration['migrationId']
        migration_state = migration['state']
        migration_stats = get_migration_stats(days, migration_id, config) 
        stats_string = process_migration_stats(days, migration_id, migration_state, migration_stats, args)
        print(stats_string)


def main():
    parser = argparse.ArgumentParser(
         usage="%(prog)s [OPTION] ...",
         description="Generate Daily Usage Statistics in CSV format from LiveData Migrator.",
    )
    parser.add_argument('--config', action = 'store', required=True,  help='Configuration file of format: {"api_endpoint" : "http://localhost:18080", "username" : "foo", "password" : "bar"}')
    parser.add_argument('--migration', action = 'store',  help='Migration to retrieve daily usage for.')
    parser.add_argument('--debug', action='store_true', help='Enable HTTP Debug.')
    parser.add_argument('--days', action='store', default=DEFAULT_NO_DAYS_TO_REPORT, type=int, help='Number of days to display, default is ' + str(DEFAULT_NO_DAYS_TO_REPORT) + '. Limited to ' + str(NO_DAYS_TO_TRACK), choices=range(1, NO_DAYS_TO_TRACK+1))
    parser.add_argument('--date', action='store', help='Limit display to single date, must be in format 2021-11-24. If the date is not available then there will be a blank entry.')
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = json.load(f)

    if args.debug:
        HTTPConnection.debuglevel = 1
        config['debug'] = True
        logging.basicConfig(level=logging.DEBUG)

    return daily_usage(config, args)


if __name__ == "__main__":
    sys.exit(main())
