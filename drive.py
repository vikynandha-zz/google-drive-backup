"""Simple command-line sample for the Google Drive API.

Command-line application that retrieves the list of files in google drive.

Usage:
    $ python drive.py

You can also get help on all the command-line flags the program understands
by running:

    $ python drive.py --help

To get detailed log output run:

    $ python drive.py --logging_level=DEBUG
"""

__author__ = 'viky.nandha@gmail.com (Vignesh Nandha Kumar)'

import gflags, httplib2, logging, os, pprint, sys, re, time
import pprint

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError, flow_from_clientsecrets
from oauth2client.tools import run


FLAGS = gflags.FLAGS

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret, which are found
# on the API Access tab on the Google APIs
# Console <http://code.google.com/apis/console>
CLIENT_SECRETS = 'client_secrets.json'

# Helpful message to display in the browser if the CLIENT_SECRETS file
# is missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the APIs Console <https://code.google.com/apis/console>.

""" % os.path.join(os.path.dirname(__file__), CLIENT_SECRETS)

# Set up a Flow object to be used if we need to authenticate.
FLOW = flow_from_clientsecrets(CLIENT_SECRETS,
    scope='https://www.googleapis.com/auth/drive',
    message=MISSING_CLIENT_SECRETS_MESSAGE)


# The gflags module makes defining command-line options easy for
# applications. Run this program with the '--help' argument to see
# all the flags that it understands.
gflags.DEFINE_enum('logging_level', 'ERROR',
                   ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                   'Set the level of logging detail.')
gflags.DEFINE_string('destination', 'downloaded/', 'Destination folder location', short_name='d')
gflags.DEFINE_boolean('debug', False, 'Log folder contents as being fetched' )
gflags.DEFINE_string('logfile', 'drive.log', 'Location of file to write the log' )
gflags.DEFINE_string('drive_id', 'root', 'ID of the folder whose contents are to be fetched' )


def open_logfile():
    if not re.match( '^/', FLAGS.logfile ):
        FLAGS.logfile = FLAGS.destination + FLAGS.logfile
    global LOG_FILE
    LOG_FILE = open( FLAGS.logfile, 'w+' )

def log(str):
    LOG_FILE.write( (str + '\n').encode('utf8') )

def ensure_dir(directory):
    if not os.path.exists(directory):
        log( "Creating directory: %s" % directory )
        os.makedirs(directory)

def is_google_doc(drive_file):
    return True if re.match( '^application/vnd\.google-apps\..+', drive_file['mimeType'] ) else False

def is_file_modified(drive_file, local_file):
    if os.path.exists( local_file ):
        rtime = time.mktime( time.strptime( drive_file['modifiedDate'], '%Y-%m-%dT%H:%M:%S.%fZ' ) )
        ltime = os.path.getmtime( local_file )
        return rtime > ltime
    else:
        return True

def get_folder_contents( service, http, folder, base_path='./', depth=0 ):
    if FLAGS.debug:
        log( "\n" + '  ' * depth + "Getting contents of folder %s" % folder['title'] )
    try:
        folder_contents = service.files().list( q="'%s' in parents" % folder['id'] ).execute()
    except:
        log( "ERROR: Couldn't get contents of folder %s. Retrying..." % folder['title'] )
        get_folder_contents( service, http, folder, base_path, depth )
        return
    folder_contents = folder_contents['items']
    dest_path = base_path + folder['title'].replace( '/', '_' ) + '/'

    def is_file(item):
        return item['mimeType'] != 'application/vnd.google-apps.folder'

    def is_folder(item):
        return item['mimeType'] == 'application/vnd.google-apps.folder'

    if FLAGS.debug:
        for item in folder_contents:
            if is_folder( item ):
                log( '  ' * depth + "[] " + item['title'] )
            else:
                log( '  ' * depth + "-- " + item['title'] )

    ensure_dir( dest_path )

    for item in filter(is_file, folder_contents):
        full_path = dest_path + item['title'].replace( '/', '_' )
        if is_file_modified( item, full_path ):
            is_file_new = not os.path.exists( full_path )
            if download_file( service, item, dest_path ):
                if is_file_new:
                    log( "Created %s" % full_path )
                else:
                    log( "Updated %s" % full_path )
            else:
                log( "ERROR while saving %s" % full_path )

    for item in filter(is_folder, folder_contents):
        get_folder_contents( service, http, item, dest_path, depth+1 )


def download_file( service, drive_file, dest_path ):
    """Download a file's content.

    Args:
      service: Drive API service instance.
      drive_file: Drive File instance.

    Returns:
      File's content if successful, None otherwise.
    """
    file_location = dest_path + drive_file['title'].replace( '/', '_' )

    if is_google_doc(drive_file):
        download_url = drive_file['exportLinks']['application/pdf']
    else:
        download_url = drive_file['downloadUrl']
    if download_url:
        try:
            resp, content = service._http.request(download_url)
        except httplib2.IncompleteRead:
            log( 'Error while reading file %s. Retrying...' % drive_file['title'].replace( '/', '_' ) )
            download_file( service, drive_file, dest_path )
            return False
        if resp.status == 200:
            try:
                target = open( file_location, 'w+' )
            except:
                log( "Could not open file %s for writing. Please check permissions." % file_location )
                return False
            target.write( content )
            return True
        else:
            log( 'An error occurred: %s' % resp )
            return False
    else:
        # The file doesn't have any content stored on Drive.
        return False


def main(argv):
    # Let the gflags module process the command-line arguments
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, argv[0], FLAGS)
        sys.exit(1)

    # Set the logging according to the command-line flag
    logging.getLogger().setLevel(getattr(logging, FLAGS.logging_level))

    # If the Credentials don't exist or are invalid run through the native client
    # flow. The Storage object will ensure that if successful the good
    # Credentials will get written back to a file.
    storage = Storage('drive.dat')
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run(FLOW, storage)

    # Create an httplib2.Http object to handle our HTTP requests and authorize it
    # with our good Credentials.
    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build("drive", "v2", http=http)

    open_logfile()

    try:
        start_folder = service.files().get( fileId=FLAGS.drive_id ).execute()
        get_folder_contents( service, http, start_folder, FLAGS.destination )
    except AccessTokenRefreshError:
        print ("The credentials have been revoked or expired, please re-run"
               "the application to re-authorize")

if __name__ == '__main__':
    main(sys.argv)
