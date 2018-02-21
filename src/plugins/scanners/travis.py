#!/usr/bin/env python3
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

import time
import datetime
import re
import json
import hashlib
import threading
import requests
import requests.exceptions
import os

"""
This is the Kibble Travis CI scanner plugin.
"""

title = "Scanner for Travis CI"
version = "0.1.0"

def accepts(source):
    """ Determines whether we want to handle this source """
    if source['type'] == 'travis':
        return True
    return False


def scanJob(KibbleBit, source, bid, token, TLD):
    """ Scans a single job for activity """
    NOW = int(datetime.datetime.utcnow().timestamp())
    dhash = hashlib.sha224( ("%s-%s-%s" % (source['organisation'], source['sourceURL'], bid) ).encode('ascii', errors='replace')).hexdigest()
    found = True
    doc= None
    parseIt = False
    found = KibbleBit.exists('cijob', dhash)
    
    # Get the job data
    bURL = "https://api.travis-ci.%s/repo/%s/builds?limit=100" % (TLD, bid)
    print("Scanning %s" % bURL)
    rv = requests.get(bURL, headers = {'Travis-API-Version': '3', 'Authorization': "token %s" % token})
    if rv.status_code == 200:
        repojs = rv.json()
        print("%s has %u jobs done" % (bURL, len(repojs.get('builds', []))))
        for build in repojs.get('builds', []):
            buildID = build['id']
            buildProject = build['repository']['slug']
            startedAt = build['started_at']
            finishedAt = build['finished_at']
            duration = build['duration']
            completed = True if duration else False
            duration = duration or 0
            
            
            buildhash = hashlib.sha224( ("%s-%s-%s-%s" % (source['organisation'], source['sourceURL'], bid, buildID) ).encode('ascii', errors='replace')).hexdigest()
            builddoc = None
            try:
                builddoc = KibbleBit.get('ci_build', buildhash)
            except:
                pass
            
            # If this build already completed, no need to parse it again
            if builddoc and builddoc.get('completed', False):
                continue
            
            # Get build status (success, failed, canceled etc)
            status = 'building'
            if build['state'] in ['finished', 'passed']:
                status = 'success'
            if build['state'] in ['failed', 'errored']:
                status = 'failed'
            if build['state'] in ['aborted', 'canceled']:
                status = 'aborted'
            
            FIN = 0
            STA = 0
            if finishedAt:
                FIN = datetime.datetime.strptime(finishedAt, "%Y-%m-%dT%H:%M:%SZ").timestamp()
            if startedAt:
                STA = int(datetime.datetime.strptime(startedAt, "%Y-%m-%dT%H:%M:%SZ").timestamp())
    
            # We don't know how to calc queues yet, set to 0
            queuetime = 0

            doc = {
                # Build specific data
                'id': buildhash,
                'date': time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(FIN)),
                'buildID': buildID,
                'completed': completed,
                'duration': duration * 1000,
                'job': buildProject,
                'jobURL': bURL,
                'status': status,
                'started': STA,
                'ci': 'travis',
                'queuetime': queuetime,
                
                # Standard docs values
                'sourceID': source['sourceID'],
                'organisation': source['organisation'],
                'upsert': True,
            }
            KibbleBit.append('ci_build', doc)
            
        # Yay, it worked!
        return True
    
    # Boo, it failed!
    KibbleBit.pprint("Fetching job data failed!")
    return False


class travisThread(threading.Thread):
    """ Generic thread class for scheduling multiple scans at once """
    def __init__(self, block, KibbleBit, source, token, jobs, TLD):
        super(travisThread, self).__init__()
        self.block = block
        self.KibbleBit = KibbleBit
        self.token = token
        self.source = source
        self.jobs = jobs
        self.tld = TLD
        
    def run(self):
        badOnes = 0
        while len(self.jobs) > 0 and badOnes <= 50:
            self.block.acquire()
            try:
                job = self.jobs.pop(0)
            except Exception as err:
                self.block.release()
                return
            if not job:
                self.block.release()
                return
            self.block.release()
            if not scanJob(self.KibbleBit, self.source, job, self.token, self.tld):
                self.KibbleBit.pprint("[%s] This borked, trying another one" % job['name'])
                badOnes += 1
                if badOnes > 100:
                    self.KibbleBit.pprint("Too many errors, bailing!")
                    self.source['steps']['travis'] = {
                        'time': time.time(),
                        'status': 'Too many errors while parsing at ' + time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(time.time())),
                        'running': False,
                        'good': False
                    }
                    self.KibbleBit.updateSource(self.source)
                    return
            else:
                badOnes = 0

def scan(KibbleBit, source):
    # Simple URL check
    travis = re.match(r"https?://travis-ci\.(org|com)", source['sourceURL'])
    if travis:
        # Is this travs-ci.org or travis-ci.com - we need to know!
        TLD = travis.group(1)
        source['steps']['travis'] = {
            'time': time.time(),
            'status': 'Parsing Travis job changes...',
            'running': True,
            'good': True
        }
        KibbleBit.updateSource(source)
        
        badOnes = 0
        pendingJobs = []
        KibbleBit.pprint("Parsing Travis activity at %s" % source['sourceURL'])
        source['steps']['travis'] = {
            'time': time.time(),
            'status': 'Downloading changeset',
            'running': True,
            'good': True
        }
        KibbleBit.updateSource(source)
        
        # Travis needs a token
        token = None
        if source['creds'] and 'token' in source['creds'] and source['creds']['token'] and len(source['creds']['token']) > 0:
            token = source['creds']['token']
        else:
            KibbleBit.pprint("Travis CI requires a token to work!")
            return False
            
        # Get the job list, paginated
        sURL = source['sourceURL']
        
        # Used for pagination
        jobs = 100
        offset = 0
        
        # Counters; builds queued, running and total jobs
        queued = 0 # We don't know how to count this yet
        building = 0
        total = 0
        blocked = 0 # Dunno how to count yet
        stuck = 0 # Ditto
        avgqueuetime = 0 # Ditto, fake it
        
        while jobs == 100:
            URL = "https://api.travis-ci.%s/repos?repository.active=true&sort_by=current_build:desc&offset=%u&limit=100&include=repository.last_started_build" % (TLD, offset)
            offset += 100
            r = requests.get(URL, headers = {'Travis-API-Version': '3', 'Authorization': "token %s" % token})
            
            if r.status_code != 200:
                KibbleBit.pprint("Travis did not return a 200 Okay, bad token?!")
                
                source['steps']['travis'] = {
                    'time': time.time(),
                    'status': 'Travis CI scan failed at ' + time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(time.time()) + ". Bad token??!"),
                    'running': False,
                    'good': False
                }
                KibbleBit.updateSource(source)
                return
            
            
            # For each build job
            js = r.json()
            for repo in js['repositories']:
                total += 1
                cb = repo.get('last_started_build')
                if cb:
                    # Is the build currently running?
                    if cb['state'] == 'started':
                        building += 1
                
                # Queue up build jobs for the threaded scanner
                bid = repo['id']
                pendingJobs.append(bid)
            
            jobs = len(js['repositories'])
            KibbleBit.pprint("Scanned %u jobs..." % total)
            
        # Save queue snapshot
        NOW = int(datetime.datetime.utcnow().timestamp())
        queuehash = hashlib.sha224( ("%s-%s-queue-%s" % (source['organisation'], source['sourceURL'], int(time.time())) ).encode('ascii', errors='replace')).hexdigest()
        
        # Write up a queue doc
        queuedoc = {
            'id': queuehash,
            'date': time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(NOW)),
            'time': NOW,
            'building': building,
            'size': queued,
            'blocked': blocked,
            'stuck': stuck,
            'avgwait': avgqueuetime,
            'ci': 'travis',
            
            # Standard docs values
            'sourceID': source['sourceID'],
            'organisation': source['organisation'],
            'upsert': True,
        }
        KibbleBit.append('ci_queue', queuedoc)
        
        
        KibbleBit.pprint("Found %u jobs in Travis" % len(pendingJobs))
        
        threads = []
        block = threading.Lock()
        KibbleBit.pprint("Scanning jobs using 4 sub-threads")
        for i in range(0,4):
            t = travisThread(block, KibbleBit, source, token, pendingJobs, TLD)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()

        # We're all done, yaay        
        KibbleBit.pprint("Done scanning %s" % source['sourceURL'])

        source['steps']['travis'] = {
            'time': time.time(),
            'status': 'Travis successfully scanned at ' + time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(time.time())),
            'running': False,
            'good': True
        }
        KibbleBit.updateSource(source)
    