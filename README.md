# Kibble Scanner Application
The Kibble Scanners collect information for the Kibble Suite.

## Setup instructions:

 - Edit conf/config.yaml to match your Kibble service

### Dependencies

 - a running Elasticsearch server

## How to run:

 - On a daily/weekly/whatever basis, run in folder src: `python3 kibble-scanner.py`.

### Command line options:

    usage: kibble-scanner.py [-h] [-o ORG] [-f CONFIG] [-a AGE] [-s SOURCE]
                             [-n NODES] [-t TYPE] [-e EXCLUDE [EXCLUDE ...]]
                             [-v VIEW]

    optional arguments:
      -h, --help            show this help message and exit
      -o ORG, --org ORG     The organisation to gather stats for. If left out, all
                            organisations will be scanned.
      -f CONFIG, --config CONFIG
                            Location of the yaml config file (full path)
      -a AGE, --age AGE     Minimum age in hours before performing a new scan on
                            an already processed source. --age 12 will not process
                            any source that was processed less than 12 hours ago,
                            but will process new sources.
      -s SOURCE, --source SOURCE
                            A specific source (wildcard) to run scans on.
      -n NODES, --nodes NODES
                            Number of nodes in the cluster (used for load
                            balancing)
      -t TYPE, --type TYPE  Specific type of scanner to run (default is run all
                            scanners)
      -e EXCLUDE [EXCLUDE ...], --exclude EXCLUDE [EXCLUDE ...]
                            Specific type of scanner(s) to exclude
      -v VIEW, --view VIEW  Specific source view to scan (default is scan all
                            sources)


## Directory structure:

 - `conf/`: Config files
 - `src/`:
 - - `kibble-scanner.py`: Main script for launching scans
 - - `plugins/`:
 - - - `brokers`: The various database brokers (ES or JSON API)
 - - - `utils`: Utility libraries
 - - - `scanners`: The individual scanner applications

## Currently available scanner plugins:

 - Apache Pony Mail (`plugins/scanners/ponymail.py`)
 - Atlassian JIRA (`plugins/scanners/jira.py`)
 - BugZilla Issue Tracker (`plugins/scanners/bugzilla.py`)
 - BuildBot (`plugins/scanners/buildbot.py`)
 - Discourse (`plugins/scanners/discourse.py`)
 - Gerrit Code Review (`plugins/scanners/gerrit.py`)
 - Git Repository Fetcher (`plugins/scanners/git-sync.py`)
 - Git Census Counter (`plugins/scanners/git-census.py`)
 - Git Code Evolution Counter (`plugins/scanners/git-evolution.py`)
 - Git SLoC Counter (`plugins/scanners/git-sloc.py`)
 - GitHub Issues/PRs (`plugins/scanners/github.py`)
 - GitHub Traffic Statistics (`plugins/scanners/github-stats.py`)
 - GNU Mailman Pipermail (`plugins/scanners/pipermail.py`)
 - Jenkins (`plugins/scanners/jenkins.py`)
 - Travis CI (`plugins/scanners/travis.py`)

## Requirements:

 - [cloc](https://github.com/AlDanial/cloc) version 1.76 or later `(optional)`
 - git binaries
 - python3 (3.3 or later)
 - python3-elasticsearch
 - python3-certifi
 - python3-yaml

### Testing

  TBD

### Pre-commit

  After running

    pip install -r requirements.txt

  Run

    pre-commit install

  to install

  Run it explicitely by

    pre-commit

  to run the checks in .pre-commit-config.yaml

  If installed the pre-commit reads the configuration, and will check on the hooks, currently pre-comit and pre-push.
  While the checks are not satisfied, just rerun the commit command until the hook checks are passed.


### Project build

  After installation of the build tool

    pip install -q build

  build the project by running

    python -m build

  Find more information in project.toml file and [Setuptools](https://setuptools.pypa.io/).

# Get involved

  TBD. Please see https://kibble.apache.org/ for details!
