#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import datetime
import json
import logging
import smtplib
import sys
import textwrap
from email.mime.text import MIMEText

if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse

NETWORK_FORMATTER = "%-20s %-15s %-15s %-15s"
MIGRATIONS_HEADER_FORMATTER = "%-40s %-44s %-14s %-15s"
MIGRATIONS_FORMATTER = "%-10s %-29s %25s %12s %14s %15s"
MIGRATIONS_FORMATTER_INLINE = "%-32s %-7s %19s %3s %10s %3s %14s %15s"


class ThroughputSummaryBucket(object):
    def __init__(self, totalBytes=None, totalFiles=None, peakBytes=None, peakFiles=None, **kwargs):
        self.totalBytes = totalBytes
        self.totalFiles = totalFiles
        self.peakBytes = peakBytes
        self.peakFiles = peakFiles


class ThroughputSummaryWrapper(object):
    def __init__(self, last10Secs=None, last60Secs=None, last300Secs=None, **kwargs):
        self.last10Secs = last10Secs
        self.last60Secs = last60Secs
        self.last300Secs = last300Secs

    def getMigratedInLast10Seconds(self):
        return ThroughputSummaryBucket(**self.last10Secs)

    def getMigratedInLast60Seconds(self):
        return ThroughputSummaryBucket(**self.last60Secs)

    def getMigratedInLast300Seconds(self):
        return ThroughputSummaryBucket(**self.last300Secs)


class EstimateWrapper(object):
    def __init__(self, inSeconds=None, asText=None, **kwargs):
        self.inSeconds = inSeconds
        self.asText = asText

    def getSeconds(self):
        return self.inSeconds


class MigrationInfo(object):
    def __init__(self, id=None, path=None, internalId=None, progress=None, **kwargs):
        self.id = id
        self.path = path
        self.internalId = internalId
        self.progress = progress

    def __repr__(self):
        return "MigrationInfo(" + str(self.__dict__) + ")"

    def getInternalId(self):
        return self.internalId

    def getPath(self):
        return self.path

    def getProgress(self):
        return MigrationProgress(**self.progress)


class MigrationProgress(object):
    def __init__(self, totalBytes=None,
                 excludedBytes=None,
                 duration=None,
                 etaEstimate=None,
                 migratedPercentage=None,
                 migrationTotalTransferredProgressBinaryValue=None,
                 migrationTotalTransferredReadableBinaryUnits=None,
                 totalMigratedBytes=None,
                 totalMigratedBytesBinaryUnitValue=None,
                 migrationTotalBinaryUnitValue=None,
                 migrationExcludedReadableBinaryValue=None,
                 migrationExcludedBinaryUnitValue=None,
                 migratedBytes=None,
                 migrationMigratedReadableBinaryUnits=None,
                 migrationTransferredProgressBinaryValue=None,
                 migrationClientBytesBinaryUnitValue=None,
                 migrationTotalTransferredReadableBinaryUnitValue=None,
                 migrationTotalReadableBinaryUnits=None,
                 migrationClientBytesBinaryUnits=None, 
                 **kwargs):
        self.totalBytes = totalBytes
        self.excludedBytes = excludedBytes
        self.duration = duration
        self.etaEstimate = etaEstimate
        self.migratedPercentage = migratedPercentage
        self.migrationTotalTransferredProgressBinaryValue = migrationTotalTransferredProgressBinaryValue
        self.migrationTotalTransferredReadableBinaryUnits = migrationTotalTransferredReadableBinaryUnits
        self.totalMigratedBytes = totalMigratedBytes
        self.totalMigratedBytesBinaryUnitValue = totalMigratedBytesBinaryUnitValue
        self.migrationTotalBinaryUnitValue = migrationTotalBinaryUnitValue
        self.migrationExcludedReadableBinaryValue = migrationExcludedReadableBinaryValue
        self.migrationExcludedBinaryUnitValue = migrationExcludedBinaryUnitValue
        self.migratedBytes = migratedBytes
        self.migrationMigratedReadableBinaryUnits = migrationMigratedReadableBinaryUnits
        self.migrationTransferredProgressBinaryValue = migrationTransferredProgressBinaryValue
        self.migrationClientBytesBinaryUnitValue = migrationClientBytesBinaryUnitValue
        self.migrationTotalTransferredReadableBinaryUnitValue = migrationTotalTransferredReadableBinaryUnitValue
        self.migrationTotalReadableBinaryUnits = migrationTotalReadableBinaryUnits
        self.migrationClientBytesBinaryUnits = migrationClientBytesBinaryUnits

    def __repr__(self):
        return "MigrationProgress(" + str(self.__dict__) + ")"

    def getTotalBytes(self):
        return self.totalBytes

    def getMigratedPercentage(self):
        return self.migratedPercentage

    def getMigrationTotalTransferredProgressBinaryValue(self):
        return self.migrationTotalTransferredProgressBinaryValue

    def getTotalMigratedBytes(self):
        return self.totalMigratedBytes

    def getMigrationTotalBinaryUnitValue(self):
        return self.migrationTotalBinaryUnitValue

    def getMigrationTotalTransferredReadableBinaryUnits(self):
        return self.migrationTotalTransferredReadableBinaryUnits

    def getTotalMigratedBytesBinaryUnitValue(self):
        return self.totalMigratedBytesBinaryUnitValue

    def getExcludedReadableTotal(self):
        return self.migrationExcludedReadableBinaryValue

    def getDuration(self):
        return EstimateWrapper(**self.duration)

    def getEtaEstimate(self):
        return EstimateWrapper(**self.etaEstimate)

    def getMigrationExcludedBinaryUnitValue(self):
        return self.migrationExcludedBinaryUnitValue


class EmailInformer():
    def __init__(self, config):
        self.config = config

    def send_message(self, status, config, **kwargs):
        server = self._connect(config)

        for to_addr in config['email_addresses']:
            # Set MIME type.
            msg = MIMEText(status)
            msg['From'] = config['sender_address']
            msg['To'] = to_addr
            # E-mail Subject Line.
            msg['Subject'] = 'WANDisco LiveData Migrator Status ' + str(datetime.datetime.now())

            data_dict = server.sendmail(config['sender_address'], to_addr, msg.as_string())
            logging.debug("sendmail: %r", data_dict)

        (code, response) = server.quit()
        logging.debug("quit: (%r) %r", code, response)

    def _connect(self, config):
        if config.get('smtp_ssl', False):
            server = smtplib.SMTP_SSL(config['smtp_host'], config['smtp_port'])
        else:
            server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])

        if config.get('debug'):
            server.set_debuglevel(1)

        server.ehlo()

        if config.get('smtp_starttls', False):
            if server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo()
            else:
                logging.error("Start_TLS not supported:")
                raise Exception("Start_TLS requested but not supported by server %r" % server)

        if config.get('smtp_username', ''):
            if server.has_extn('AUTH'):
                logging.debug("authenticating to mailserver, user: %s, pass: XXXXXX ", config['smtp_username'])
                server.login(config['smtp_username'], config['smtp_password'])
            else:
                logging.error("AUTH not supported:")

        return server


def padBytesUnit(val):
    return val


def formatTimeFromSeconds(seconds):
    elapsed = datetime.timedelta(seconds=seconds)
    return "%02d:%02d:%02d" % (elapsed.days,
                               elapsed.seconds // 3600,
                               (elapsed.seconds // 60) % 60)


def build_auth_header(username, password):
    credentials = ('%s:%s' % (username, password))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))
    return 'Basic %s' % encoded_credentials.decode("ascii")


def get_http_connection(endpoint):
    url = urlparse(endpoint)
    if url.scheme == 'https':
        return HTTPSConnection(url.netloc)

    return HTTPConnection(url.netloc)


def doHttp(verb, config, path):
    conn = get_http_connection(config['api_endpoint'])
    headers = {}
    if config['username']:
        headers['Authorization'] = build_auth_header(config['username'], config['password'])
    conn.request(verb, path, None, headers)
    return conn.getresponse()


def migration_summary(config):
    resp = doHttp("GET", config, "/stats/migrationSummary")
    if resp.status == 200:
        return json.loads(resp.read())
    else:
        raise ValueError(resp.status, resp.reason)


def throughput_summary(config):
    resp = doHttp("GET", config, "/stats/throughputSummary")
    if resp.status == 200:
        return json.loads(resp.read())
    else:
        raise ValueError(resp.status, resp.reason)


def formatMigrationRow(migrationInfo, includeTransferredProgress):
    output = []

    path_wrapped = textwrap.wrap(migrationInfo.getPath(), 106)
    if len(path_wrapped) > 1:
        output.extend([" " + x for x in path_wrapped])
        path = ""
    else:
        path = " " + path_wrapped[0]

    scannerTransferInComplete = migrationInfo.getProgress().getTotalBytes() > 0 \
                                and migrationInfo.getProgress().getMigratedPercentage() < 100
    transferredValue = migrationInfo.getProgress().getMigrationTotalTransferredProgressBinaryValue() \
        if includeTransferredProgress and scannerTransferInComplete \
        else migrationInfo.getProgress().getMigrationTotalTransferredReadableBinaryUnits()

    transferredValueUnit = padBytesUnit(migrationInfo.getProgress().getTotalMigratedBytesBinaryUnitValue()) \
        if migrationInfo.getProgress().getTotalMigratedBytes() >= migrationInfo.getProgress().getTotalBytes() \
        else padBytesUnit(migrationInfo.getProgress().getMigrationTotalBinaryUnitValue())

    id = migrationInfo.getInternalId()[:6]
    remaining = formatTimeFromSeconds(migrationInfo.getProgress().getEtaEstimate().getSeconds()) \
        if includeTransferredProgress and scannerTransferInComplete \
        else ""

    transferredPercentage = str(migrationInfo.getProgress().getMigratedPercentage()) + "%" \
        if includeTransferredProgress & scannerTransferInComplete \
        else ""

    excludedValue = migrationInfo.getProgress().getExcludedReadableTotal()
    excludedUnit = padBytesUnit(migrationInfo.getProgress().getMigrationExcludedBinaryUnitValue())

    output.append(MIGRATIONS_FORMATTER_INLINE % (
        path,
        id,
        transferredPercentage
        + " " + transferredValue,
        transferredValueUnit,
        excludedValue,
        excludedUnit,
        formatTimeFromSeconds(migrationInfo.getProgress().getDuration().getSeconds()),
        remaining))

    return output


def printDataMigrationStatuses(title, migrationsList, includeTransferredProgress):
    result = []
    result.append(MIGRATIONS_FORMATTER % (title, len(migrationsList), "Transferred  ", "Excluded", "Duration", "Remaining"))
    result.append("")

    for row in sorted(migrationsList, key=lambda x: x['path']):
        m = MigrationInfo(**row)
        result.extend(formatMigrationRow(m, True))
        result.append("")
    return result


def getAverageFilesByBucket(throughput):
    last10Sec = throughput.getMigratedInLast10Seconds().totalFiles
    lastMin = throughput.getMigratedInLast60Seconds().totalFiles
    last5Min = throughput.getMigratedInLast300Seconds().totalFiles

    return NETWORK_FORMATTER % (
        "Average Files/s:",
        "%.0f" % (last10Sec / 10.0),
        "%.0f" % (lastMin / 60.0),
        "%.0f" % (last5Min / 300.0))


def getAverageBandwidthByBucket(throughput):
    last10Sec = throughput.getMigratedInLast10Seconds().totalBytes
    lastMin = throughput.getMigratedInLast60Seconds().totalBytes
    last5Min = throughput.getMigratedInLast300Seconds().totalBytes

    return NETWORK_FORMATTER % (
        "Average Throughput: ",
        bytesToGibibitsPerSecond(last10Sec / 10.0),
        bytesToGibibitsPerSecond(lastMin / 60.0),
        bytesToGibibitsPerSecond(last5Min / 300.0))


def bytesToGibibitsPerSecond(nBytes):
    return "%.2f Gib/s" % ((nBytes * 8) / 1073741824.0)


def migrationsByType(summary, category):
    return summary.get(category, {'migrations': []}).get('migrations')


def printMigrationsForType(summary, key, label, includeTransferredProgress):
    migrations = migrationsByType(summary, key)
    if migrations:
        return printDataMigrationStatuses(label, migrations, includeTransferredProgress)
    return []


def generate_status(config):
    summary = migration_summary(config)
    throughput = ThroughputSummaryWrapper(**throughput_summary(config))
    overallCount = summary.get('overallCount', 0)

    status = []
    status.append(NETWORK_FORMATTER % ("Network", "(10s)", "(1m)", "(5m)"))
    status.append("---------")
    status.append(getAverageBandwidthByBucket(throughput))
    status.append(getAverageFilesByBucket(throughput))
    status.append("")
    status.append(MIGRATIONS_HEADER_FORMATTER % (str(overallCount) + " Migrations", "", "dd:hh:mm", "dd:hh:mm"))
    status.append("--------------")
    status.append("")
    status.extend(printMigrationsForType(summary, 'live', 'Live', True))
    status.extend(printMigrationsForType(summary, 'running', 'Running', True))
    status.extend(printMigrationsForType(summary, 'stopped', 'Stopped', True))
    status.extend(printMigrationsForType(summary, 'ready', 'Ready', True))
    return "\n".join(status)


def status(config):
    print(generate_status(config))


def notify_status(config):
    status = generate_status(config)
    email_action = EmailInformer(config)
    email_action.send_message(status, config)


def usage(text):
    print("usage: %s" % text)
    return sys.exit(1)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config', help='Configuration file for notifier.')
    parser.add_argument('--debug', action='store_true')

    subparsers = parser.add_subparsers(dest='command')

    # parser for the "status" command                                                                     
    parser_list = subparsers.add_parser('status')

    # parser for the "notify-status" command                                                                     
    parser_notify = subparsers.add_parser('notify-status')

    # parse the args and call whatever function was selected                                                      
    args = parser.parse_args()
    print("ARGS", args)

    if not args.config:
        usage("ldm-status [status | notify-status] [args ...]")
        return

    with open(args.config, 'r') as f:
        config = json.load(f)

    if args.debug:
        HTTPConnection.debuglevel = 1
        config['debug'] = True
        logging.basicConfig(level=logging.DEBUG)

    if args.command == 'status':
        return status(config)
    elif args.command == 'notify-status':
        return notify_status(config)
    else:
        usage("ldm-status [status | notify-status] [args ...]")


if __name__ == "__main__":
    sys.exit(main())
