#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © Cirata 2024
#
# Author: Marc Norris
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
import os.path

if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse


def get_datetime_details_collected():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


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


def get_instance_uuid(host_config):
    resp = doHttp("GET", host_config, "/info/nodeID")
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    inst_uuid = resp.read()
    return inst_uuid.decode('utf-8')


def get_license_information(host_config):
    resp = doHttp("GET", host_config, "/license")
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    return json.loads(resp.read())


def create_output_header(args):
    header = ("LM2 ID,License Type,Data Limit in Bytes,Data Used in Bytes,Data Remaining in Bytes,Expiry Date,"
              "Collection Time")
    if args.debug:
        header += ", Config Host ID"
    return header


def create_row(node_uuid, ldm_license, component, collection_time):
    row_details = ""
    if 'migratedDataLimit' in component:
        row_details = "{},{},{},{},{},{},{}".format(node_uuid, component['licenseType'],
                                                    component['migratedDataLimit'], component['migratedDataSize'],
                                                    component['migratedDataRemaining'], ldm_license['expiryDate'],
                                                    collection_time)
    elif 'consumption' in component:
        row_details = "{},{},{},{},{},{},{}".format(node_uuid, component['licenseType'], '', '', '', '',
                                                    collection_time)
    return row_details


def write_output(args, header, rows):
    print(header)
    for row in rows:
        print(row)
    if args.filename:
        with open(args.filename, 'w') as f:
            f.write(header)
            f.write('\n')
            for row in rows:
                f.write(row)
                f.write('\n')


def license_information(config, args):
    rows = []
    header = create_output_header(args)

    for k, v in config.items():
        host_config = v
        node_uuid = get_instance_uuid(host_config)
        collection_time = get_datetime_details_collected()
        ldm_license = get_license_information(host_config)
        for component in ldm_license['components']:
            row_details = create_row(node_uuid, ldm_license, component, collection_time)

            if row_details:
                if args.debug:
                    row_details = row_details + "," + k
                rows.append(row_details)

    write_output(args, header, rows)


def main():
    parser = argparse.ArgumentParser(
         usage="%(prog)s [OPTION] ...",
         description="Retrieve license information in CSV format from LiveData Migrator.",
    )
    parser.add_argument('--config', action = 'store', required=True,  help='Configuration file of format: {"api_endpoint" : "http://localhost:18080", "username" : "foo", "password" : "bar"}')
    parser.add_argument('--filename', action='store', help='Output file name and location')
    parser.add_argument('--debug', action='store_true', help='Enable HTTP Debug.')
    args = parser.parse_args()

    if os.path.isfile(args.config):
        with open(args.config, 'r') as f:
            try:
                config = json.load(f)
            except Exception as error:
                print("The config file, {0}, is not in the correct format.".format(args.config))
                print(error)
                sys.exit(1)
    else:
        print("{0} does not exist.".format(args.config))
        sys.exit(1)

    if args.debug:
        HTTPConnection.debuglevel = 1
        logging.basicConfig(level=logging.DEBUG)

    return license_information(config, args)

if __name__ == "__main__":
    sys.exit(main())
