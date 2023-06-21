# LiveData Migrator Scripts

**schedular** Script to schedule starting migrations.

**notifier** Script to notify by e-mail of new Notifications.

**status** Script to send the LiveData Migrator status as an e-mail

**monitor** Script to check LiveData Migrator Diagnostics and send out warning e-mail if any metric is out of an acceptable range.

**daily-usage** Script to generate a CSV report of the daily amount of data migrated per Migration.

**parsers** Scripts for parsing logs files and generating reports. 

**delete** Script to remove extra files on a target. Script uses a verification report and will delete any files and directories that are on the target but not on the source.
