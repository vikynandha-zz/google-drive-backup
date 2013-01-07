Google Drive Backup
===================

A python script to sync your google drive contents.

## Features
* You can Download your entire google drive or any given folder
* Downloads a file it has been modified since last download
* Logs all actions (optional)
* Uses OAuth2 authentication and can remember authentication

## Options
Following command line options are available.

*--destination* - Path to the folder where the files have to be downloaded to. If not specified, a folder named `downloaded` is created in the current directory.

*--debug* - If present (accepts no value), every step will be logged to the log file.

*--logile* - Path to the file to which the logs should be written to. By default, writes to `drive.log` in the current directory. The file will be overwritten every time the script is run.

*--drive_id* ID of the folder which you want to download. By default, entire "My Drive" is downloaded.