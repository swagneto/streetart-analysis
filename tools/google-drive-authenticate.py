#!/usr/bin/env python

# authenticates the Graffiti Project with a user's Google Drive so that all of
# the tools and tech demos can access it.  information about the authenticated
# user is printed to standard output.
#
# authentication only occurs if existing credentials are invalid or missing,
# or if the user has forced re-authentication via a command line option.  as
# a result, this script is safe to run multiple times

from __future__ import print_function

import getopt
import httplib2
import os
import sys

# Google's modules.
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

# pathfor the stored Google Drive credentials.
CREDENTIALS_DIRECTORY_NAME = ".credentials"

# file name of the authenticated Google Drive credentials JSON.
CREDENTIALS_FILE_NAME      = "graffiti-analysis-google-drive.json"

# file name of the client secret JSON.  this contains identifying information
# so that Google knows which project to attribute resource usage to.  see the
# documentation on how to acquire one.
CLIENT_SECRET_FILE = 'graffiti-analysis-client-secret.json'

# NOTE: if you modify this scope, you must delete previously saved credentials
#       ~/CREDENTIALS_DIRECTORY_NAME/CREDENTIALS_FILE_NAME or force
#       re-authentication.
CREDENTIALS_SCOPE  = 'https://www.googleapis.com/auth/drive'

# name of the project so that user's know what they're granting rights to.
APPLICATION_NAME   = 'Graffiti Analysis'

def usage( script_name ):
    """
    Takes a name of the script (full path, name, etc) and prints its usage to standard
    output.
    """

    usage_format_string = """Usage: {0:s} [-f] [-h] [<client secret>]

Authenticates with Google Drive so that Graffiti Analysis tools and technology
demos may interact with a user's account.

Authentication is performed using OAuth 2.0 under the installed application model
(or web, or server-side authorization as it is also called) which requires a local
<client secret> file to identify the application requesting authorization to
Google's servers.  If omitted, <client secret> defaults to:

    {1:s}

Upon successful authentication high-level information about the current user is
displayed to standard output.

The command line options above are described below:

  -f    Force authentication to occur even if valid credentials exist.
  -h    Displays this help message and exits.
"""

    default_client_secret_path = os.path.join( get_credentials_directory(),
                                               CLIENT_SECRET_FILE )

    print( usage_format_string.format( script_name,
                                       default_client_secret_path ) )

def get_credentials_directory():
    """
    Constructs the directory where the Graffiti Project's credentials reside.
    This may be used to build full paths to cached OAuth2 credentials as well
    as client secret information.

    Takes no arguments.

    Returns 1 value:

       credentials_directory - Path to the credential's directory.
    """

    return os.path.join( os.path.expanduser( '~' ),
                         CREDENTIALS_DIRECTORY_NAME )

def display_authentication_warning( client_secret_path ):
    """
    Displays a warning message to standard error indicating that authentication
    is not possible due to a missing client secret file.  Directs the user to
    documentation detailing how to address the issue.

    Takes 1 argument:

      client_secret_path - Path to the client secret file that needs to be
                           recreated.

    Returns nothing.
    """

    warning_str = """
The client secrets file does not exist though is needed for authenticating
the Graffiti Project tool set.  This should be acquired from the project's
administrator through the API console as detailed in the documentation
directory.

Please acquire the client secrets file and place it here:

  {0:s}
"""

    print( warning_str.format( client_secret_path ),
           file=sys.stderr )

def get_drive_credentials( client_secret_path, force_reauth_flag=False ):
    """
    Acquires valid user credentails.

    If credentials have not been stored, or if they are invalid, or if
    re-authentication has been requested, the OAuth2 flow is completed to
    obtain new credentials.  This flow will use the client secret path
    specified.

    Takes 2 arguments:

      client_secret_path - Path to the Graffiti Tools's client secret
                           JSON file.
      force_reauth_flag  - Optional flag indicating that reauthentication
                           should be forced rather than use existing,
                           on-disk credentials.  If omitted, defaults to
                           False.

    Returns 1 value:

      credentials - An authenticated OAuth2 credentials object.
    """

    credential_dir = get_credentials_directory()

    # ensure that we have a credentials directory.
    if not os.path.exists( credential_dir ):
        os.makedirs( credential_dir )

    credential_path = os.path.join( credential_dir,
                                    CREDENTIALS_FILE_NAME )

    store = oauth2client.file.Storage( credential_path )

    # skip loading the credentials if we're being forced to reauthenticate.
    if force_reauth_flag:
        credentials = None
    else:
        credentials = store.get()

    # if we did not have local credentials, then we need to bootstrap them
    # from a client secret file.
    if not credentials or credentials.invalid:

        # verify that the secrets file exists before attempting to create a
        # flow from it, otherwise notify the user that it doesn't exist.
        try:
            file_stats = os.stat( client_secret_path )
        except:
            display_authentication_warning( client_secret_path )
            sys.exit( 1 )

        flow            = client.flow_from_clientsecrets( client_secret_path,
                                                          CREDENTIALS_SCOPE )
        flow.user_agent = APPLICATION_NAME

        # assume that we're running on a head-less system so that we provide
        # the user with a URL to copy and paste into a browser.
        #
        # force the "command line options" to log anything that is at least
        # a warning and ensure we get a URL instead of a browser opened.
        cli_oauth2_options = ['--noauth_local_webserver',
                              '--logging_level', 'WARNING']
        flags              = tools.argparser.parse_args( cli_oauth2_options )
        credentials        = tools.run_flow( flow, store, flags )

        # let the user know where we keep the credentials.
        print( "\n"
               "Storing credentials to {0:s}.\n".format( credential_path ) )

    return credentials

def display_authenticated_user( http ):
    """
    Prints information about the currently authenticated user to standard output.

    Takes 1 argument:

      http - Authenticated HTTP object.

    Returns nothing.
    """

    service = discovery.build( 'drive', 'v3', http=http )

    results = service.about().get( fields="user" ).execute()
    user    = results.get( 'user', [] )

    print( "Authenticated as {0:s} ({1:s}).".format( user['displayName'],
                                                     user['emailAddress'] ) )

def main( argv ):
    """
    Takes the command line of the script, comprised of the application name
    and an optional path to the client secret to use during authentication
    with Google Drive.
    """

    # by default we let the script look for credentials in standard locations.
    # this may be overwritten by the user on the command line.
    client_secret_path = None

    # flag indicating whether we should force reauthentication despite having
    # already done so.  by default we use any credentials found on disk.
    force_reauth_flag = False

    # parse our command line options.
    try:
        opts, args = getopt.getopt( argv[1:], "fh" )
    except getopt.GetoptError as error:
        sys.stderr.write( "Error processing option: %s\n" % str( error ) )
        sys.exit( 1 )

    # handle any valid options were were presented.
    for opt, arg in opts:
        if opt == '-f':
            force_reauth_flag = True
        elif opt == '-h':
            usage( argv[0] )
            sys.exit( 0 )

    # did we get enough command line arguments?  if so, figure out where to
    # pull the client secrets from.
    if len( args ) > 1:
        sys.stderr.write( "Expected 0 or 1 arguments, but received {0:d}.\n".format( len( args ) ) )
        sys.exit( 1 )
    elif len( args ) == 1:
        client_secret_path = args[0]
    else:
        client_secret_path = os.path.join( get_credentials_directory(),
                                           CLIENT_SECRET_FILE )

    # acquire our credentials.
    credentials = get_drive_credentials( client_secret_path, force_reauth_flag )
    http        = credentials.authorize( httplib2.Http() )

    # print some information about the user that just authenticated.
    display_authenticated_user( http )

if __name__ == "__main__":
    main( sys.argv )
