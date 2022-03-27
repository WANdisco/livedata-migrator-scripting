# LiveData Migrator Parsing Scripts

The parser scripts can be used to parse LiveData Migrator
logs and print them in a format that is easy to 
process and examine. They are generally used to 
parse historic logs to understand changes in system
behaviour that might stem from environmental changes.
The scripts can be used to generate CSV outputs
that can be loaded in spreadsheets for further 
processing and for generating graphs


***diagnostics_parser.py*** 

Parse diagnostic logs and pretty print JSON or in CSV format.

The diagnostic logs contain LiveData Migrator Diagnostics 
that are collected once a minute. The information is logged
in JSON format, one JSON record per line containing the
Diagnostics for that minute.

This provides a historic
picture of the internal system at a minute granularity and
covers things like CPU load, file transfer rates, connection
states etc. These logs can be useful for tracking down
changes in system behaviour due to environmental changes, 
for example network issues.

The script allows the user to select which diagnostic they
are interested in and allows the output to be formated in
CSV format which can be loaded into a spreadsheet and
graphed. 

```
usage: diagnostics_parser.py [OPTION] [FILE]...

Pretty Diagnostics logs as JSON or CSV.

positional arguments:
  files

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -k KIND, --kind KIND  filter Diagnostics by kind, eg --kind NetworkStatus or --kind
                        NetworkStatus/connectionTotals/10.69.102.183
  -o {json,csv}, --output {json,csv}
                        Output format (Default json)
  -n N                  Number of threads to spawn. By default this will equal the core count of the
                        host machine
```	

For example

```
diagnostics_parser.py -k NetworkStatus/connectionTotals/10.69.102.183 -o csv diagnostic*.gz
```

This will parse all files in the current directory which start with diagnostic and end in .gz,
filter for the NetworkStatus diagnostic and print the connectionTotals information for host
10.69.102.183 in a CSV format that can be loaded into spreadsheet.

***filetracker_parser.py***

Parse file-tracker logs, print summary in column format.	

Each Migration has an associated set of file-tracker logs. 
The file-tracker log contains an entry for each file that
is transferred for the migration in JSON format. This information
includes if the transfer was successful, how many times it was
retried, when it started, file size, how long it took to transfer 
and how fast it was transferred.

The file tracker log can be grepped to find a particular file that
was transferred. 

To understand overall performance the file-tracker log
can be converted to CSV format. This can be loaded into
a spreadsheet and values graphed, or it can be sorted
to identify files that transferred slowly or were 
retried a number of times.

```
usage: filetracker_parser.py [OPTION] [FILE]...

Pretty print LiveData Migrator FileTracker logs.

positional arguments:
  files

optional arguments:
  -h, --help     show this help message and exit
  -v, --version  show program's version number and exit
  -c, --column   display FileTacker in column format.
```

For example:

```
filetracker_parser.py -c file-tracker-aa512fe1-5bb4-4998-963a-4b0863137f03.*
```

This will parse all file-tracker logs associated with Migration aa512fe1-5bb4-4998-963a-4b0863137f03,
note the script will parse gzipped files without the need to uncompress them.

***migrations_parser.py***

Parse Migrations REST output and print summary.

This script will take the output of the Migrations REST endpoint and create a CSV output of 
the amount of data transferred by the migration by the initial scan while the Migration
was in the RUNNING state and how much data was transferred due to client activity on the
source filesystem. 

To collect the Migration information from the REST endpoint:

```
curl -s http://127.0.0.1:18080/migrations -o migrations.txt 
```

This script will parse the output JSON into a CSV format:

```
migrationId, path, scanned bytes, client bytes
```


Scanned bytes are bytes migrated during the initial scan in
the RUNNING state, client bytes are the bytes migrated due
to client activity on the source filesystem. The CSV output
can be loaded into a spreadsheet.

```
usage: migrations_parser.py [OPTION] [FILE]...

Parse Migration JSON.

positional arguments:
  files

optional arguments:
  -h, --help     show this help message and exit
  -v, --version  show program's version number and exit
```

For example

```
./migrations_parser.py /tmp/migrations.txt 
             foo,               /repl3,        563795250,                0
```


There is only one Migration and it is named "foo", the path is "/repl3", 
563795250 bytes were transferred as part of the initial scan and no bytes
were transferred due to client activity.
