# LiveData Migrator Schedular Script

When deploying LiveData Migrator the goal is to setup
a number of Migration paths that can run into the hundreds.
When a Migration is first started the Migration is in the
RUNNING state, in this state it scans existing files 
on the path and migrates those paths along with any 
new activity on the path that is in a region already
scanned. When the scan and migration of already existing
data is complete the Migration moves into the LIVE stater.
In the LIVE state all migration activity is triggered
by changes on the source filesystem.

If a user has a large number of Migrations they wish to
add to the system then it can make sense to limit
the number in the RUNNING state. Limiting the number in
the RUNNING state can reduce the load on the source 
filesystem NameNode from scanning and listing of the filesystem.
A user can do this by closely monitoring the system and
the number of Migrations in the RUNNING state, only starting
new Migrations when the number of Migrations in the RUNNING
state is below a certain level.

This script automates the managing of the Migrations
in the RUNNING state. The user adds the Migrations to
LiveData Migrator but does not start them. They create
a "priority list" of the Migrations, listing the Migrations
in the order they want them to be started. They then
run this script via cron such that it executes every 5
minutes and provide the script with the limit of the 
number of Migrations allowed to be in the RUNNING
state. The script will run and check how many Migrations
are RUNNING, if it is less than the required number
then it will start the next one in the priority list.

This script and priority list can also be used if Migrations
have been reset. After a reset of all Migrations they have to
got through the RUNNING state again, this script can manage
that.

**Usage**

'''
ldm-schedular.py --howmany 1 --priority-list priorities.txt --username admin --password password --endpoin https://127.0.0.1:18080
'''

When run with the above arguments the script will check how many Migrations
are in the RUNNING state. If there are less than 1, ie zero, the it will
look through the priorities.txt for the next Migration that is not started
and start the Migration.

'''
usage: ldm-schedular.py [-h] --howmany HOWMANY [--priority-list PRIORITY_LIST]
                        [--username USERNAME] [--password PASSWORD]
                        [--endpoint ENDPOINT] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --howmany HOWMANY     Ensure that HOWMANY migrations are running at once. If there are queued
                        migrations (those created without --auto-start) this script will "run"
                        them to a max of HOWMANY.
  --priority-list PRIORITY_LIST
                        Optional filename of paths which define a custom priority for migration
                        run order.  The file ordering defines the priority.  If no priority list is
                        supplied or if a particular path is missing from the file the priority will be
                        dictated by the creation time
                        
                        The file format is one path per line. example:
                        
                        cat << EOF > priorities.txt
                        /repl3
                        /repl1
                        /src
                        EOF
  --username USERNAME   Username for basic authentication (if enabled)
  --password PASSWORD   Password for bsaic authentication (if enabled)
  --endpoint ENDPOINT   Override API endpoint (e.g. for https or custom port)
                        (default: http://localhost:18080)
                        
  --debug
'''
