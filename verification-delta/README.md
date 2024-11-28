# LiveData Migrator Verification Comparision Script

Script requires python3 and duckdb (pip install duckdb)

Script loads the inconsistencies from two LiveData Migrator 
verification reports and compares them. It will determine
which inconsistencies have not been resolved, which are
resolved and which are new.

**Usage:**

    python3 ldm-verification-delta.py --h
    usage: ldm-verification-delta.py [-h] [--debug] [--output OUTPUT] --first FIRST --second SECOND

    options:
        -h, --help       show this help message and exit
        --debug
        --output OUTPUT  Store the output into csv files.
        --first FIRST    First verification report to check against.
        --second SECOND  Second verification report to check against.

