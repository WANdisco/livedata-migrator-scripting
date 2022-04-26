#LiveData Migrator Start/Stop Script

Script to start or stop migrations. This can be used during maintenance, for example to stop migrations when it is known the target filesystem will be unavailable.

To stop migrations run:
```
  ./ldm-stop-start.py --config ldm-stop-start.config stop
```
The file ldm-stop-start.config contains configuration information for the LiveData Migrator REST API.

To start migrations run:
```
  ./ldm-stop-start.py --config ldm-stop-start.config start
```
This will only start migrations that are in the STOPPED state, for example it will not start migrations in the NONSCHEDULED state. If a migration is in a STOPPED start and cannot be restarted, for example it has been aborted then an error message will be output indicating that it was not started.

```
./ldm-stop-start.py --config ldm-stop-start.config start
Not starting Migration [migration-2][/repl2] as current state is [NONSCHEDULED]
Migration [migration-3][/repl3] not started.  403 The migration migration-3 can't be started from STOPPED state.
Migration [migration-1][/repl1] started
```
migration-2 is not started as it is in the NONSCHEDULED state, migration-3 is not started as it cannot be started.

The format of the configuration file is:

```
cat ldm-stop-start.config 
{
  "api_endpoint" : "http://localhost:18080",
  "username" : "foo",
  "password" : "bar"
}
```
