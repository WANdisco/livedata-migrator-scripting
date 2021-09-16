#LiveData Migrator Monitor E-mail Script

This script will poll LiveData Migrator monitoring critical values and will 
e-mail if any fall outside acceptable parameters. Example configurations for
TLS/SSL and STARTTLS SMTP servers are provided.

The script is designed to be run as a cron job and stores some state between runs in a file.

Script polls the /diagnostics/summary and checks the following metrics:

* actionStoreCurrent - total number of actions queued for all migrations, if this number is breached e-mail will be triggered.

* actionStoreLargestMigration - if the number of actions queued for a single Migration is breached then e-mail will be sent.

* pendingRegionCurrent - number of pending regions for all migrations.

* pendingRegionMaxMigration - if the number of pending regions for a Migration exceeds this number an e-mail will be sent.

* retryCountDeltaLimit - if the number of retries exceeds this number between executions of the script then an email will be triggered.

* periodBetweenEmail - period between emails. Measured in seconds. This limits the number of emails to one period.

The script can be run as follows:

    ./ldm-monitor.py --config monitor.config 

The configuration file monitor.config holds all the configuration necessary.

The configuration file is as follows:

    {
      # The LiveData Migrator Endpoint
      "api_endpoint" : "http://localhost:18080",
      
      # The username and password for authenticating to LiveData Migrator
      "username" : "",
      "password" : "",

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
      "smtp_ssl" : true,

      "actionStoreCurrent" : 200000,
      "actionStoreLargestMigration" : 100000,
      "pendingRegionCurrent" : 400000,
      "pendingRegionMaxMigration" : 100000,
      "retryCountDeltaLimit" : 5,
      # Limit to 6 hours between emails, measured in seconds.
      "periodBetweenEmail" : 21600
    }


To create a simple test SMTP server run

    python -m smtpd -c DebuggingServer -n localhost:1025

There is a configuration file for this server included, monitor.python.test.config.
