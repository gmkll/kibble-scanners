#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
 #the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import hashlib
import importlib
import os
import re
import sys
import subprocess
import time
import shutil

from src.plugins.brokers.kibbleES import KibbleBit

title = "Traffic statistics plugin for GitHub repositories"
version = "0.1.0"

def accepts(source):
    """ Do we accept this source? """
    if source['type'] == 'github':
        return True
    return False

def getTime(string):
    """ Convert GitHub timestamp to epoch """
    return time.mktime(time.strptime(re.sub(r"Z", "", str(string)), "%Y-%m-%dT%H:%M:%S"))

def scan(KibbletBit, source):

    # Get some vars, construct a data path for the repo
    path = source['sourceID']
    url = source['sourceURL']

    auth=None
    people = {}
    if 'creds' in source:
        KibbleBit.pprint("Using auth for repo %s" % source['sourceURL'])
        creds = source['creds']
        if creds and 'username' in creds:
            auth = (creds['username'], creds['password'])
    else:
        KibbleBit.pprint("GitHub stats requires auth, none provided. Ignoring this repo.")
        return
    try:
        source['steps']['stats'] = {
            'time': time.time(),
            'status': 'Fetching statistics from source location...',
            'running': True,
            'good': True
        }
        KibbletBit.updateSource(source)

        # Get views
        github = importlib.import_module("plugins.utils.github")
        views = github.views(url, auth)
        if 'views' in views:
            for el in views['views']:
                ts = getTime(el['timestamp'])
                #print("reformatted time:", ts)
                shash = hashlib.sha224( ("%s-%s-%s-clones" %(source['organisation'], url, el['timestamp'])).encode('ascii', errors = 'replace')).hexdigest()
                bit = {
                    'organisation': source['organisation'],
                    'sourceURL': source['sourceURL'],
                    'sourceID': source['sourceID'],
                    'date': time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(ts)),
                    'count': el['count'],
                    'uniques': el['uniques'],
                    'ghtype': 'views',
                    'id': shash
                }
                KibbleBit.append('ghstats', bit)

        # Get clones
        clones = github.clones(url, auth)
        if 'clones' in clones:
            for el in clones['clones']:
                ts = getTime(el['timestamp'])
                shash = hashlib.sha224( ("%s-%s-%s-clones" %(source['organisation'], url, el['timestamp'])).encode('ascii', errors = 'replace')).hexdigest()
                bit = {
                    'organisation': source['organisation'],
                    'sourceURL': source['sourceURL'],
                    'sourceID': source['sourceID'],
                    'date': time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(ts)),
                    'count': el['count'],
                    'uniques': el['uniques'],
                    'ghtype': 'clones',
                    'id': shash
                }
                KibbleBit.append('ghstats', bit)

        # Get referrers
        refs = github.referrers(url, auth)
        if refs:
            for el in refs:
                el['timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S", time)
                ts = getTime(el['timestamp'])
                shash = hashlib.sha224( ("%s-%s-%s-refs" %(source['organisation'], url, el['timestamp'])).encode('ascii', errors = 'replace')).hexdigest()
                bit = {
                    'organisation': source['organisation'],
                    'sourceURL': source['sourceURL'],
                    'sourceID': source['sourceID'],
                    'date': time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(ts)),
                    'count': el['count'],
                    'uniques': el['uniques'],
                    'ghtype': 'referrers',
                    'id': shash
                }
                KibbleBit.append('ghstats', bit)
    except:
        pass
        # All done!
