#LiveData Migrator Notification E-mail Script

This script will poll LiveData Migrator for new Notifications and send them via e-mail.

The script is designed to be run as a cron job and stores some state between runs in a file, this allows it to know what Notifications it has sent before.

Note the script will use efficient polling using conditional GET.

The script can be run as follows:

    ./ldm-notifier.py --config notifier.config notify


The configuration file notifier.config holds all the configuration necessary.

The configuration file is as follows:

    {
       # The LiveData Migrator Endpoint
       "api_endpoint" : "http://localhost:18080",
       
       # The username and password for authenticating to LiveData Migrator
       "username" : "",
       "password" : "",
       
       # Notifications to ignore. Options are:
       # MigrationAddedNotification, MissingEventsNotification, LicenseWarningNotification, 
       # LicenseExceptionNotification, LicenseInvalidNotification
       # MigrationLiveNotification, LiveMigratorStartNotification 
       "filter_on_type" : [],
       
       # Level of Notification to Ignore. Options are:
       # INFO, WARN, ERROR
       "filter_on_level" : [],
       
       # File to hold state between runs of script, this holds the
       # timestamp of the last Notification sent.
       "swp_file" : "/tmp/notifier.swp",

       # e-mail address of the sender.
       "sender_address" : "wandisco.testing@gmail.com",

       # e-mail addresses to send the Notification to.
       "email_addresses": ["mark@wandisco.com", "zz@googlemail.com"],

       # SMTP settings, these are for Gmail. For guidance on how to setup
       # an application Gmail account see https://support.google.com/accounts/answer/185833?hl=en
       "smtp_host" : "smtp.gmail.com",
       "smtp_port" : 465,
       "smtp_username" : "wandisco.testing@gmail.com",
       "smtp_password" : "XXXXXXXXXXX",
       "smtp_ssl" : true
    }


To create a simple test SMTP server run

    python -m smtpd -c DebuggingServer -n localhost:1025

There is a configuration file for this server included, notifier.python.test.config.
