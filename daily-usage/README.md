# LiveData Migrator Daily Usage

Script to retrieve the daily amount of data migrated from LiveData Migrator and
report in CSV format. The script will show how much data was transferred on each
day for each Migration over the last set of days. This is useful for identifying
which Migrations are the busiest Migration and which are the least busy or
are not migrating data at all. Tracking this level of information can be used for
managing License usage. 

The output from the script can be loaded into a spreadsheet.


The script can be run as follows:

```
    ./ldm-daily-usage.py --config ldm-daily-usage.config
```

The configuration file ldm-daily-usage.config holds all the configuration necessary.

The configuration file is as follows:

```
    {
      # The LiveData Migrator Endpoint
      "api_endpoint" : "http://localhost:18080",
      
      # The username and password for authenticating to LiveData Migrator
      "username" : "",
      "password" : "",
    }
```

Command Line Options:

```
optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Configuration file of format: {"api_endpoint" :
                        "http://localhost:18080", "username" : "foo",
                        "password" : "bar"}
  --migration MIGRATION
                        Migration to retrieve daily usage for.
  --debug               Enable HTTP Debug.
  --days {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59}
                        Number of days to display, default is 29. Limited to
                        59
  --date DATE           Limit display to single date, must be in format
                        2021-11-24. If the date is not available then there
                        will be a blank entry.
```

Sample output

```
./ldm-daily-usage.py --days 5 --config ldm-daily-usage.config 
Migration, State, 2022-03-26, 2022-03-25, 2022-03-24, 2022-03-23, 2022-03-22
foo, LIVE, 0, 0, 0, 563795250, 0
```

The system has only one Migration, "foo", and it's in the "LIVE" state. For the
last three days no data was migrated but on 2022-03-23 there were 563795250
bytes transferred.


