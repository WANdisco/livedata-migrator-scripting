#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © WANDisco 2023
#
# Author: Paul Scott Murphy, Colm Dougan, Mark Mc Keown
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

from __future__ import print_function, with_statement

import argparse
import json
import logging
import sys
import gzip
import os.path
import urllib
import fnmatch


if (2, 6) <= sys.version_info < (3, 0):
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
else:
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse


# Logging format.
LDM_DELETE_LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"


# Generata credentials for Authorization header.
def build_auth_header(username, password):
    credentials = "%s:%s" % (username, password)
    encoded_credentials = base64.b64encode(credentials.encode("ascii"))
    return "Basic %s" % encoded_credentials.decode("ascii")


def get_http_connection(endpoint):
    url = urlparse(endpoint)
    if url.scheme == "https":
        logging.debug("Making https connecting to %s" % url.netloc)
        return HTTPSConnection(url.netloc)

    logging.debug("Making http connecting to %s" % url.netloc)
    return HTTPConnection(url.netloc)


def doHttp(verb, config, path):
    conn = get_http_connection(config["api_endpoint"])
    headers = {}
    if config["username"]:
        headers["Authorization"] = build_auth_header(
            config["username"], config["password"]
        )
    try:
        conn.request(verb, path, None, headers)
    except:
        failedToConnect(config)
    return conn.getresponse()


def get_migration_info(config, migration_id):
    logging.debug("Getting migration information for %s" % (migration_id))
    resp = doHttp("GET", config, "/migrations/" + migration_id)
    if resp.status == 200:
        return json.loads(resp.read())
    else:
        logging.error(
            "Failed to get Migration with Id %s: %s" % (migration_id, resp.status)
        )
        sys.exit(1)


def read_exclusion_file(exclusion_file):
    patterns = []
    with open(exclusion_file) as fp:
        for line in fp:
            pattern = line.strip()
            logging.info("Exclusion pattern: '%s'" % (pattern))
            patterns.append(pattern)

    return patterns


def filter_paths_by_exclusions(config, missing_paths):
    files_excluded = []
    for pattern in config["exclusions"]:
        paths_excluded = fnmatch.filter(missing_paths, pattern)
        for path in paths_excluded:
            logging.debug("EXPLICITLY_EXCLUDED: %s" % (path))
        files_excluded.extend(paths_excluded)

    return sorted(list(set(files_excluded)))


def remove_child_paths(filtered_paths, excluded_paths, implicitly_excluded):
    excluded = set()
    for path in excluded_paths:
        child_excluded = fnmatch.filter(filtered_paths, path + "/*")
        for child_path in child_excluded:
            logging.debug("CHILD_IMPLICITLY_EXCLUDED %s" % (child_path))
        excluded.update(child_excluded)

    implicitly_excluded.extend(excluded)
    return [x for x in filtered_paths if x not in excluded]


# Remove the parent directories of explicitly excluded paths, add them
# to implicitly_excluded
# This is called recursively.
def remove_parent_paths(filtered_paths_set, excluded_paths, implicitly_excluded):
    excluded = set()

    for path in excluded_paths:
        parent = os.path.dirname(path)
        if parent in filtered_paths_set:
            logging.debug("PARENT_IMPLICITLY_EXCLUDED %s" % (parent))
            filtered_paths_set.remove(parent)
            excluded.add(parent)

    implicitly_excluded.extend(excluded)

    # If we have excluded parents then check for their parents.
    if excluded:
        return remove_parent_paths(
            filtered_paths_set, list(excluded), implicitly_excluded
        )

    # No excluded parents so we can stop
    return sorted(list(filtered_paths_set))


def get_target_filesystem(config, migration_id):
    migration = get_migration_info(config, migration_id)
    return migration["target"]


def set_target_filesystem(path, config):
    if config["args"].filesystem_name is not None:
        logging.info(
            "Using provided target filesystem %s" % (config["args"].filesystem_name)
        )
        return

    filename = os.path.basename(path)
    if len(filename) <= 37:
        logging.error(
            "Verification directory %s does not match expected format migration_id-timestamp and target filesystem not set."
            % (path)
        )
        sys.exit(1)

    migration_id = filename[0:36]
    logging.info("Migration Id: %s" % (migration_id))
    target_file_system = get_target_filesystem(config, migration_id)
    logging.info("Using target filesystem %s" % (target_file_system))
    config["args"].filesystem_name = target_file_system


def parse_verification(config):
    if config["args"].verification_directory is not None:
        file = (
            config["args"].verification_directory + "/verification-discrepancy.jsonl.gz"
        )
        return parse_verification_report(file)

    if config["args"].verification_file is None:
        logging.error("Neither verification_file or verification_directory is set.")
        sys.exit(1)
    return parse_verification_report(config["args"].verification_file)


def parse_verification_report(file_path):
    if not os.path.exists(file_path):
        logging.error("Path %s does not exist." % (file_path))
        sys.exit(1)

    if not os.path.isfile(file_path):
        logging.error("Path %s is not a file." % (file_path))
        sys.exit(1)

    if not os.access(file_path, os.R_OK):
        logging.error("Path %s is not readable." % (file_path))
        sys.exit(1)

    if file_path.endswith(".gz"):
        with gzip.open(file_path, "rt") as file:
            return process_file(file)

    with open(file_path, "r") as file:
        return process_file(file)


def process_file(file):
    missing_on_source_entries = []

    for line in file:
        json_obj = json.loads(line)
        if json_obj["scanResult"] == "MISSING_ON_SOURCE":
            missing_on_source_entries.append(json_obj["targetPath"])
            logging.debug("MISSING_ON_SOURCE %s" % (json_obj["targetPath"]))

    return sorted(missing_on_source_entries)


def filter_paths_fast(missing_paths):
    filtered_paths = []
    # Create a set of the paths for fast lookup.
    path_set = set(missing_paths)

    # If a parent directory of the path is to be deleted
    # then there is no point deleting the path.
    for path in missing_paths:
        directory = os.path.dirname(path)
        if directory not in path_set:
            filtered_paths.append(path)
        else:
            logging.debug("PARENT_TO_BE_DELETED: %s" % (path))

    return filtered_paths


def failedToConnect(config):
    logging.error("Failed to connected to %s" % config["api_endpoint"])
    sys.exit(1)


def quote_for_url(stuff):
    if (2, 6) <= sys.version_info < (3, 0):
        return urllib.pathname2url(stuff)
    else:
        return urllib.parse.quote(stuff)


def delete_missing_paths(filtered_paths, config):
    headers = {}
    if config["username"]:
        headers["Authorization"] = build_auth_header(
            config["username"], config["password"]
        )
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    body = json.dumps({"recursive": "true"})

    deleted = 0
    missing = 0
    failed = 0
    count = 0
    for path in filtered_paths:
        conn = get_http_connection(config["api_endpoint"])
        count = count + 1
        url = (
            "/fs/targets/"
            + quote_for_url(config["args"].filesystem_name)
            + "/deleteByPath?path="
            + quote_for_url(path)
        )
        try:
            conn.request("POST", url, body, headers)
        except:
            failedToConnect(config)

        status = conn.getresponse().status
        if status == 200:
            logging.info("%d/%d, Deleted %s" % (count, len(filtered_paths), path))
            deleted = deleted + 1
        elif status == 404:
            logging.info(
                "%d/%d, Missing on Target %s" % (count, len(filtered_paths), path)
            )
            missing = missing + 1
        else:
            failed = failed + 1
            logging.error(
                "%d/%d, Error deleting %s: %d"
                % (count, len(filtered_paths), path, status)
            )

    return deleted, missing, failed


def args_check(args):
    if not args.config:
        usage("ldm-delete [args ...]")
        return

    if args.verification_file is None and args.verification_directory is None:
        logging.error("Either verification_file or verification_directory must be set.")
        usage("ldm-delete [args ...]")
        sys.exit(1)

    if args.verification_file is not None and args.verification_directory is not None:
        logging.error(
            "Both --verification-file or --verification-directory can not be set."
        )
        usage("ldm-delete [args ...]")
        sys.exit(1)

    if args.verification_file is not None:
        if not os.path.isfile(args.verification_file):
            logging.error(
                "--verification-file option '%s' must be a file."
                % (args.verification_file)
            )
            sys.exit(1)

    if args.verification_directory is not None:
        if not os.path.isdir(args.verification_directory):
            logging.error(
                "--verification-directory option '%s' must be a directory."
                % (args.verification_directory)
            )
            sys.exit(1)

    if args.exclusion_file is not None:
        if not os.path.isfile(args.exclusion_file):
            logging.error(
                "--exclusion-file option '%s' must be a file." % (args.exclusion_file)
            )
            sys.exit(1)


def usage(text):
    print(
        "Script to delete files that may have been left undeleted on a target filesystem"
    )
    print("usage: %s" % text)
    return sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Process verification report to delete extraneous content."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Configuration file.",
    )
    parser.add_argument(
        "--filesystem_name",
        help="The target filesystem name. Not required if a verification directory is used. The script will retrieve the target filesystem name for the migration using the migration id embedded in the directory name.",
    )
    parser.add_argument(
        "-f",
        "--verification-file",
        help="The name of the verification report JSONL file",
    )
    parser.add_argument(
        "-e",
        "--exclusion-file",
        help="File of exclusion patterns for files not to be deleted, one per line. Patterns are based on https://docs.python.org/3/library/fnmatch.html",
    )
    parser.add_argument(
        "-d",
        "--verification-directory",
        help="The directory holding the verification results.",
    )
    parser.add_argument(
        "--dry-run",
        default=False,
        action="store_true",
        help="List the paths that would be deleted on Target but do not delete them.",
    )

    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.load(f)

    # Configure logging - send to std out
    if args.debug:
        HTTPConnection.debuglevel = 1
        config["debug"] = True
        logging.basicConfig(
            stream=sys.stdout, level=logging.DEBUG, format=LDM_DELETE_LOG_FORMAT
        )
    else:
        logging.basicConfig(
            stream=sys.stdout, level=logging.INFO, format=LDM_DELETE_LOG_FORMAT
        )

    # Sanity check the arguments.
    args_check(args)

    # Take a copy of args.
    config["args"] = args

    config["exclusions"] = []
    if args.exclusion_file is not None:
        config["exclusions"] = read_exclusion_file(args.exclusion_file)

    # Extract the extra paths on the target.
    missing_paths = parse_verification(config)
    # Filter out paths that are subpaths of directories that are going to be deleted.
    filtered_paths = []
    excluded_paths = []
    implicitly_excluded = []
    if config["exclusions"]:
        # Find all the paths directly to be excluded.
        excluded_paths = filter_paths_by_exclusions(config, missing_paths)
        # remove excluded_paths from missing_paths
        filtered_paths = [x for x in missing_paths if x not in excluded_paths]
        # remove children of excluded paths from the paths to delete
        filtered_paths = remove_child_paths(
            filtered_paths, excluded_paths, implicitly_excluded
        )
        # remove parent directories of the paths excluded for delete
        filtered_paths = remove_parent_paths(
            set(filtered_paths), excluded_paths, implicitly_excluded
        )
        # Do not delete a path if its parent is going to be deleted.
        filtered_paths = filter_paths_fast(filtered_paths)
    else:
        # filter paths such that if the parent directory of a path is to be
        # deleted then you do not need to delete the path.
        filtered_paths = filter_paths_fast(missing_paths)

    logging.info("Paths missing on source:         %8d" % (len(missing_paths)))
    logging.info("Explicitly Excluded:             %8d" % (len(excluded_paths)))
    logging.info("Implicitly Excluded:             %8d" % (len(implicitly_excluded)))
    logging.info("Paths to delete:                 %8d" % (len(filtered_paths)))

    # If dry run log paths to be deleted and exit.
    if args.dry_run:
        logging.info("Dry run, paths that would be deleted:")
        for path in filtered_paths:
            logging.info("%s" % (path))
        return

    # If using a verification_directory then we can check for target_filesystem
    if config["args"].verification_directory is not None:
        set_target_filesystem(config["args"].verification_directory, config)

    # Delete paths.
    deleted, missing, failed = delete_missing_paths(filtered_paths, config)
    logging.info("Deleted Count:           %8d" % deleted)
    logging.info("Missing on Target:       %8d" % missing)
    logging.info("Failed to Delete:        %8d" % failed)


if __name__ == "__main__":
    sys.exit(main())
