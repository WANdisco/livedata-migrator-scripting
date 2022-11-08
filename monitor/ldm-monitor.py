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
from datetime import datetime
import base64
import json
import logging
import os
import re
import pickle
import sys
import smtplib
import time

from email.mime.text import MIMEText

if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
    from urllib import urlencode
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse, urlencode

class EmailInformer():
    def __init__(self, config):
        self.config = config

    def send_message(self, warning_summary, diagnostic_summary, config, **kwargs):
        dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print("%s %s" % (dt_string, warning_summary))
        store = MonitorStore(config['swp_file'])
        (_, _, last_email_timestamp) = store.get()
        epoch_time = int(time.time())
        if (epoch_time - last_email_timestamp) < config['periodBetweenEmail']:
           print('Not sending email, %d seconds since last email.' % (epoch_time - last_email_timestamp))
           return 


        server = self._connect(config)

        for to_addr in config['email_addresses']:
            msg = MIMEText(diagnostic_summary)
            msg['From'] = config['sender_address']
            msg['To'] = to_addr
            msg['Subject'] = warning_summary + ' ' + dt_string

            data_dict = server.sendmail(config['sender_address'], to_addr, msg.as_string())
            logging.debug("sendmail: %r", data_dict)

        (code, response) = server.quit()
        store.email_sent(int(time.time()))
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
                  
class MonitorStore(object):
    def __init__(self, path):
        self.swp_file = path
        (self.timestamp, self.diagnostic_summary, self.email_timestamp) = self._read()

    def is_empty(self):
        return self.timestamp == 0

    def get(self):
        return (self.timestamp, self.diagnostic_summary, self.email_timestamp)

    def put(self, timestamp, diagnostic_summary):
        with open(self.swp_file, "wb") as fp:   #Pickling
            pickle.dump((timestamp, diagnostic_summary, self.email_timestamp), fp)

        self.timestamp = timestamp
        self.diagnostic_summary = diagnostic_summary

    def email_sent(self, email_timestamp):
        self.email_timestamp = email_timestamp
        with open(self.swp_file, "wb") as fp:   #Pickling
            pickle.dump((self.timestamp, self.diagnostic_summary, self.email_timestamp), fp)


    def _read(self):
        if os.path.exists(self.swp_file):
            with open(self.swp_file, "rb") as fp:   # Unpickling
                return pickle.load(fp)
        else:
            return (0, None, 0)

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

def doHttp(verb, config, path):
    conn = get_http_connection(config['api_endpoint'])
    headers = {}
    if config['username']:
        headers['Authorization'] = build_auth_header(config['username'], config['password'])
    conn.request(verb, path, None, headers)
    return conn.getresponse()


def get_diagnostic_summary(config):
    resp = doHttp("GET", config, "/diagnostics/summary")
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    summaryJson = resp.read()
    diagnostic_summary = json.loads(summaryJson)

    return diagnostic_summary

def get_diagnostic_summary_txt(config):
    resp = doHttp("GET", config, "/diagnostics/summary.txt")
    if resp.status != 200:
        raise ValueError(resp.status, resp.reason)

    diagnostic_summary_txt = resp.read()
    return diagnostic_summary_txt.decode("utf-8") 

def get_disk_space_warnings(config):
    if not 'path_disk_space_check' in config:
       return []
    if not 'path_disk_space_percentage' in config:
       return []
    
    warnings = []
    for path in config['path_disk_space_check']:
       try:
          st = os.statvfs(path)
       except Exception as err:
          print("Error getting disk usage: " + str(err))
          continue

       total = st.f_blocks * st.f_frsize
       used = (st.f_blocks - st.f_bfree) * st.f_frsize
       percentage_used = int((float(used)/float(total)) * 100)
       if percentage_used >= config['path_disk_space_percentage']:
           warnings.append("High Disk Usage for [" + path + "], Usage: " + str(percentage_used) + "%. " + str(int(used/(2**30))) + "GiB/" + str(int(total/(2**30))) + "GiB")
    return warnings

def check_for_tmp_log_files(config):
    if not 'check_for_log_tmp_files' in config:
       return []

    
    warnings = []
    for path in config['check_for_log_tmp_files']:
       warnings.extend(check_for_log_tmp_files_under_path(path))
    return warnings

def check_for_log_tmp_files_under_path(path):
    tmp_log_files = []
    warnings = []
    reg_ex = re.compile('\.log[0-9]+\.tmp$')

    try:
       for root, dirs, files in os.walk(path):
           for file in files:
               m = reg_ex.search(file)
               if m:
                  tmp_log_files.append(os.path.join(root, file))
    except Exception as err:
       print("Error searching for tmp log files: " + str(err)) 
       return warnings
               
    if tmp_log_files:
       warnings.append("tmp log files found under [" + path + "]: " + ','.join(tmp_log_files))
    return warnings

def check_for_core_files(config):
    if not 'check_for_core_files' in config:
       return []

    if not isinstance(config['check_for_core_files'], list):
       return check_for_core_files_under_path(config['check_for_core_files'])

    warnings = []
    for path in config['check_for_core_files']:
       warnings.extend(check_for_core_files_under_path(path))
    return warnings


def check_for_core_files_under_path(path):
    hprof_files = []
    warnings = []
    try:
       for root, dirs, files in os.walk(path):
         for file in files:
            if file.endswith(".hprof"): 
               hprof_files.append(os.path.join(root, file))
    except Exception as err:
       print("Error searching for core files: " + str(err))
       return warnings

    if hprof_files:
       warnings.append("Hprof files found under [" + path + "]: " + ','.join(hprof_files))
    return warnings   


def monitor(config):
    timeStamp = int(time.time())
    diagnostic_summary = get_diagnostic_summary(config)
    
    label = ""
    if 'e_mail_subject_label' in config:
        label = config['e_mail_subject_label'] + ' '

    store = MonitorStore(config['swp_file'])
    (old_time_stamp, old_diagnostic_summary, _) = store.get() 
    store.put(timeStamp, diagnostic_summary)
    email_action = EmailInformer(config)

    warnings = get_warnings(config, diagnostic_summary, old_time_stamp, old_diagnostic_summary)
    warnings.extend(get_disk_space_warnings(config))
    warnings.extend(check_for_core_files(config))
    warnings.extend(check_for_tmp_log_files(config))
    if len(warnings) > 0:
        body = generate_message_text(config, warnings)
        email_action.send_message(label + "WARN: " + warnings[0], body, config)

def generate_message_text(config, warnings):
    return """
Warnings
=========
%s

Summary
========
%s
""" % ("\n".join(warnings), get_diagnostic_summary_txt(config))

def get_warnings(config, diagnostic_summary, old_time_stamp, old_diagnostic_summary):
    warnings = []

    # Check total queued Actions
    if config['actionStoreCurrent'] <= diagnostic_summary['actionStoreCurrent']:
        warnings.append("High Total Action Store Queue Size " + str(diagnostic_summary['actionStoreCurrent']))
       	
    # Check the Migration with the largest queued Actions
    if config['actionStoreLargestMigration'] <= diagnostic_summary['actionStoreLargestMigration']:
        warnings.append("High Action Store Queue Size For Migration " + diagnostic_summary['actionStoreLargestMigrationId'])

    # Check the total pending regions.
    if config['pendingRegionCurrent'] <= diagnostic_summary['pendingRegionCurrent']:
        warnings.append("High Total Pending Region Queue Size " + str(diagnostic_summary['pendingRegionCurrent']))

    # Check the migration with most pending regions.
    if config['pendingRegionMaxMigration'] <= diagnostic_summary['pendingRegionMaxMigration']:
        warnings.append("High Pending Region Queue Size for " + diagnostic_summary['pendingRegionMaxMigrationPath'])

    # Only allowed retryCountDeltaLimit retries between checks.
    if old_time_stamp > 0:
        if config['retryCountDeltaLimit'] <= (diagnostic_summary['retryCount'] - old_diagnostic_summary['retryCount']):
            warnings.append("High Retry Rate " + str(diagnostic_summary['retryCount']))

    return warnings

def usage(text):
    print("usage: %s" % text)
    return sys.exit(1)

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config', help='Configuration file for notifier.')
    parser.add_argument('--debug', action='store_true')

    args = parser.parse_args()
    print("ARGS", args)

    if not args.config:
        usage("ldm-monitor [args ...]")
        return

    with open(args.config, 'r') as f:
        config = json.load(f)

    if args.debug:
        HTTPConnection.debuglevel = 1
        config['debug'] = True
        logging.basicConfig(level=logging.DEBUG)

    return monitor(config)
   
if __name__ == "__main__":
    sys.exit(main())
