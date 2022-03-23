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
import json
import logging
import os
import pickle
import smtplib
import sys
from email.mime.text import MIMEText

if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse


class Notification(object):
    def __init__(self, id=None, type=None, message=None, timeStamp=None, dateCreated=None, dateUpdated=None, resolved=None, level=None,
                 **kwargs):
        self.id = id
        self.type = type
        self.message = message
        self.timeStamp = timeStamp
        self.dateCreated = dateCreated
        self.dateUpdated = dateUpdated
        self.resolved = resolved
        self.level = level

    def __repr__(self):
        return "Notification(" + str(self.__dict__) + ")"

    def as_json(self):
        return json.dumps(self.__dict__, indent=4)


class EmailInformer():
    def __init__(self, config):
        self.config = config

    def send_message(self, body, subject, config, **kwargs):
        server = self._connect(config)

        for to_addr in config['email_addresses']:
            msg = MIMEText(body)
            msg['From'] = config['sender_address']
            msg['To'] = to_addr
            msg['Subject'] = subject

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


class NotifiedStore(object):
    def __init__(self, path):
        self.swp_file = path
        (self.timestamp, self.etag, self.alive) = self._read()

    def is_empty(self):
        return self.timestamp == 0

    def get(self):
        return (self.timestamp, self.etag, self.alive)

    def down(self):
        self._put(self.timestamp, self.etag, 'false')

    def put(self, timestamp, etag):
        self._put(timestamp, etag, 'true')

    def _put(self, timestamp, etag, alive):
        with open(self.swp_file, "wb") as fp:  # Pickling
            pickle.dump((timestamp, etag, alive), fp)

        self.timestamp = timestamp
        self.etag = etag
        self.alive = alive


    def _read(self):
        if os.path.exists(self.swp_file):
            with open(self.swp_file, "rb") as fp:  # Unpickling
                stored = pickle.load(fp)
                if len(stored) == 2:
                    return (stored[0], stored[1], 'true')
                return stored
        else:
            return (0, None, None)


def build_auth_header(username, password):
    credentials = ('%s:%s' % (username, password))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))
    return 'Basic %s' % encoded_credentials.decode("ascii")


def get_http_connection(endpoint):
    url = urlparse(endpoint)
    if url.scheme == 'https':
        print("Making https connecting to %s" % url.netloc)
        return HTTPSConnection(url.netloc)

    print("Making http connecting to %s" % url.netloc)
    return HTTPConnection(url.netloc)


def sendConnectionFailed(config):
    store = NotifiedStore(config['swp_file'])
    (_, _, alive) = store.get()
    # If the system was down from previous call then skip
    # sending e-mail.
    if alive == 'true':
        store.down()
        print('Sending e-mail for failure to connect.')
        msg_subject = 'WANDisco service unavailable, failed to connect to ' + config['api_endpoint']
        email_action = EmailInformer(config)
        email_action.send_message(msg_subject, msg_subject, config)
        
    sys.exit(1)
    
    

def failedToConnect(config):
    print("Failed to connected to %s" % config['api_endpoint'])
    if config['command'] == 'list':
        sys.exit(1)
    sendConnectionFailed(config)


def doHttp(verb, config, path, etag):
    conn = get_http_connection(config['api_endpoint'])
    headers = {}
    if config['username']:
        headers['Authorization'] = build_auth_header(config['username'], config['password'])
    if etag is not None:
        headers['If-None-Match'] = etag
    try:
        conn.request(verb, path, None, headers)
    except:
        failedToConnect(config)
    return conn.getresponse()


def latest_notification(config):
    resp = doHttp("GET", config, "/notifications/last", None)
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    obj = json.loads(resp.read())
    return Notification(**obj)


def list_notifications(config, etag):
    resp = doHttp("GET", config, "/notifications", etag)
    if resp.status == 304:
        return ([], etag)
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    etag = resp.getheader("Etag", None)
    listJson = resp.read()
    items = json.loads(listJson)

    notifications = []
    for row in sorted(items, key=lambda x: x['timeStamp']):
        notifications.append(Notification(**row))

    return (notifications, etag)


def list(config):
    (notifications, etag) = list_notifications(config, None)

    for n in notifications:
        print(n.as_json())


def notify(config):
    store = NotifiedStore(config['swp_file'])
    if store.is_empty():
        latest = latest_notification(config)
        store.put(latest.timeStamp, None)
        return

    (since, old_etag, _) = store.get()
    (notifications, etag) = list_notifications(config, old_etag)
    notifications_to_send = filter_notifications(notifications, since, config)
    email_action = EmailInformer(config)
    for notification in notifications_to_send:
        print("Notification: %s %s %s" % (notification.dateCreated, notification.level, notification.type))
        email_action.send_message(notification.as_json(), notification.level + ' ' + notification.type + ' ' + notification.dateCreated, config)
        store.put(notification.timeStamp, etag)

    return 0


def filter_notifications(notifications, since, config):
    filtered = []
    for notification in notifications:
        if int(notification.timeStamp) <= int(since):
            continue
        if notification.type in config['filter_on_type']:
            continue
        if notification.level in config['filter_on_level']:
            continue
        filtered.append(notification)
    return filtered


def usage(text):
    print("usage: %s" % text)
    return sys.exit(1)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config', help='Configuration file for notifier.')
    parser.add_argument('--debug', action='store_true')

    subparsers = parser.add_subparsers(dest='command')

    # parser for the "list" command                                                                     
    parser_list = subparsers.add_parser('list')

    # parser for the "notify" command                                                                     
    parser_notify = subparsers.add_parser('notify')

    # parse the args and call whatever function was selected                                                      
    args = parser.parse_args()
    print("ARGS", args)

    if not args.config:
        usage("ldm-notifier [list | notify] [args ...]")
        return

    with open(args.config, 'r') as f:
        config = json.load(f)

    if args.debug:
        HTTPConnection.debuglevel = 1
        config['debug'] = True
        logging.basicConfig(level=logging.DEBUG)

    if args.command == 'list':
        config['command'] = 'list'
        return list(config)
    elif args.command == 'notify':
        config['command'] = 'notify'
        return notify(config)
    else:
        usage("ldm-notifier [list | notify] [args ...]")


if __name__ == "__main__":
    sys.exit(main())
