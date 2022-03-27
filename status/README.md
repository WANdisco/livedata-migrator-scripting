#LiveData Migrator Status E-mail Script

This script will poll LiveData Migrator status and send it via e-mail.
To recieve a daily update of the status of LiveData Migrator configure
this script to run once a day via a cron job.

**Usage:**

    ./ldm-status.py --config status.config status

This will display the status of the LiveData Migrator similar to what is displayed in the CLI.

    ./ldm-status.py --config status.config notify-status

This will e-mail the status to the e-mail addresses included in the config file.

**Configuration:**

The configuration file status.config holds all the configuration necessary.

The configuration file is as follows:

    {
      # The LiveData Migrator Endpoint
      "api_endpoint" : "http://localhost:18080",

      # The username and password for authenticating to LiveData Migrator
      "username" : "",
      "password" : "",

      # e-mail address of the sender.
      "sender_address" : "foo@gmail.com",

      # e-mail addresses to send the status to.
      "email_addresses": ["foo@wandisco.com", "foo@googlemail.com"],

      # SMTP settings, these are for Gmail. For guidance on how to setup
      # an application Gmail account see https://support.google.com/accounts/answer/185833?hl=en
      "smtp_host" : "smtp.gmail.com",
      "smtp_port" : 465,
      "smtp_username" : "wandisco.testing@gmail.com",
      "smtp_password" : "XXXXXXXXXXX",
      "smtp_ssl" : true
    }


**Testing:**

To create a simple test SMTP server run:

    python -m smtpd -c DebuggingServer -n localhost:1025

This will start a simple Python SMTP server running on port 1025,
configure ldm-status to use this SMTP server and you should see
e-mail's arriving with status details.

