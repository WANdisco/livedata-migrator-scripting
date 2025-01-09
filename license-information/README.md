# LiveData Migrator License Information

Script to retrieve the license information from LiveData Migrator and
report in CSV format. The script will show current license information 
in use by the instance along with the total instance usage. 

The output will output its results to screen by default and will additionally 
save to file when the filename parameter is supplied.


The script can be run as follows:

```
    ./license-information.py --config license-information.config
```

The configuration file license-information.config holds all the configuration necessary.

The configuration file is as follows:

```
    {
      # Alias a LiveData Migrator Endpoint
      "host1" : {
      
        # The LiveData Migrator Endpoint
        "api_endpoint" : "http://localhost:18080",
        
        # The username and password for authenticating to LiveData Migrator
        "username" : "foo",
        "password" : "bar"
      },
      "host2" : {
        "api_endpoint" : "http://localhost2:18080",
        "username" : "foo",
        "password" : "bar"
      }
    }
```

Command Line Options:

```
optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Configuration file of format: {"api_endpoint" :
                        "http://localhost:18080", "username" : "foo",
                        "password" : "bar"}
  --filename FILENAME   Filename to save output
  --debug               Enable HTTP Debug.
```

Sample output

```
./license-information.py --config license-information.config 
LM2 ID,License Type,Data Limit in Bytes,Data Used in Bytes,Data Remaining in Bytes,Expiry Date,Collection Time, Config Host ID
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx,volume,5497558138880,1375554650,5490582584230,2025-03-02T00:00:00,2025-01-08T12:00:00,host1
yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy,consumption,,,,,,host2
```

The script was checking two Data Migrator instances and reporting back on general license information.


