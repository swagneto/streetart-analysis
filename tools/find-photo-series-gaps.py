#!/usr/bin/env python

# Queries a Google Drive for a list of files that have numbers embedded within
# in their file name and then identifies pairs of files that have gaps in the
# series that are within a specific range.  This allows identification of "holes"
# within file uploads.
#
# While this was designed with the intent of finding missing pictures, it could
# be applied to anything that has a numeric counter within them.
#
# NOTE: The defaults for patterns and numbers are tailored to Panasonic series
#       cameras as that is what produced images that these tools were developed
#       against.

from __future__ import print_function

import getopt
import httplib2
import os
import pickle
import re
import sys

# Google's modules.
import apiclient
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

# path components for the stored Google Drive credentials.
CREDENTIALS_DIRECTORY_NAME = ".credentials"
CREDENTIALS_FILE_NAME      = "graffiti-analysis-google-drive.json"

# NOTE: if you modify these scopes, you must delete previously saved credentials
#       ~/CREDENTIALS_DIRECTORY_NAME/CREDENTIALS_FILE_NAME
CREDENTIALS_SCOPE  = 'https://www.googleapis.com/auth/drive.metadata.readonly'
APPLICATION_NAME   = 'Graffiti Analysis'

# Panasonic's default naming convention is PMMM0NNN.JPG where MMM is the a
# folder/group identifier (in the range of 101-999) and NNN is a photo series
# identifier (in the range of 001-999).  the fact that the folder/group
# identifier is not adjacent to the series identifier drives our default
# maximum gap size.
DEFAULT_SERIES_PATTERN = "[0-9]{7}"
DEFAULT_NAME_PATTERN   = "^P" + DEFAULT_SERIES_PATTERN + ".JPG"

# set the minimum size of detected gaps to be large enough to avoid legitimate
# holes created through culling of pictures (out of focus, slightly tilted,
# series of shots for comparison, etc).
MINIMUM_GAP_SIZE     = 10

# Panasonic's decision to only allow 999 files within a single folder ensures
# that there is a gap of 9002 potential files between the last file in a folder
# and the first in a success folder.
MAXIMUM_GAP_SIZE     = 9002

def usage( script_name ):
    """
    Takes a name of the script (full path, name, etc) and prints its usage to standard
    output.
    """

    usage_format_string = """Usage: {0:s} [-F <file name>] [-h] [-n <lower>[,<upper>]] [<name pattern> [<series pattern>]]

Queries the user's Google Drive for a series of files that have "holes" in
them.  Files that match <name pattern> have their series number extracted by
searching for <series pattern> and then are compared to identify gaps.  If
omitted, <name pattern> and <series pattern> default to:

    {1:s}
    {2:s}

Both patterns must be specified as valid Python regular expression.

Gap size may be controlled by a command line option to minimize false
positives from normal gaps in photo uploads (e.g. eliminating bad pictures
prior to archiving).  Gaps must fall within a range before reporting them
to a user.  Ranges are used so that file names with multiple numbering
schemes may be processed within introducing false positives (e.g. names
with both folder and file numbers).

Gaps are printed to standard output along with the files at the edge of each
gap.

The command line options above are described below:

  -F <file name>        Load and store the file name list from/in <file name>.
                        This allows repeated calls to the script with different
                        parameters without redundantly querying the user's Google
                        Drive.
  -h                    Displays this help message and exits.
  -n <lower>[,<upper>]  Specifies the lower, and optionally upper, bound of missing
                        files to identify a series gap with.  If omitted, defaults
                        the range [{3:d}, {4:d}).
"""

    print( usage_format_string.format( script_name,
                                       DEFAULT_NAME_PATTERN,
                                       DEFAULT_SERIES_PATTERN,
                                       MINIMUM_GAP_SIZE,
                                       MAXIMUM_GAP_SIZE ) )

def get_drive_credentials():
    """
    Acquires valid user credentails.  Queries the local system for existing
    OAauth2 credentials.  If they don't exist then a RuntimeError exception is
    raised.

    Takes no arguments.

    Returns 1 value:

      credentials - An authenticated OAuth2 credentials object.
    """

    home_dir       = os.path.expanduser( '~' )
    credential_dir = os.path.join( home_dir, CREDENTIALS_DIRECTORY_NAME )

    # ensure that we have a credentials directory.
    if not os.path.exists( credential_dir ):
        os.makedirs( credential_dir )

    credential_path = os.path.join( credential_dir,
                                    CREDENTIALS_FILE_NAME )

    store       = oauth2client.file.Storage( credential_path )
    credentials = store.get()

    # if we did not have local credentials, then let the user know that they
    # need to authenticate this machine.
    if not credentials or credentials.invalid:
        raise RuntimeError( "Valid authentication credentials were not found." );

    return credentials

def get_live_file_names( credentials ):
    """
    Queries the Google Drive for a list of non-trashed file names.  No
    filtering by name or file type is performed.  Properly handles Drives
    that have more files than can be queried in a single API call.

    Takes 1 argument:

      credentials - Authenticated OAuth2 credentials object.

    Returns 1 value:

      name_list - List of file names in the Google Drive, sorted
                  lexiographically.
    """

    # Files results dictionary returned by our query.  the 'items' key is
    # updated to contain all of the files returned by every query made.
    results         = None

    # page token used to walk through our Files listing.  starts out empty,
    # then set to the appropriate token for restarting our listing, then
    # transitions to None when our listing is complete.
    next_page_token = ''

    # dictionary that will hold our pageToken for restarting our listing.
    kwargs          = {}

    http        = credentials.authorize( httplib2.Http() )
    service     = discovery.build( 'drive', 'v2', http=http )

    # continue to make requests while we have a valid page token.  only when
    # we don't do we know that there aren't any addition files in the Drive.
    while not (next_page_token is None):

        # only provide a pageToken during our listing request when we have
        # one.
        if next_page_token != '':
            kwargs['pageToken'] = next_page_token

        try:
            # only request non-trashed file names.
            entries = service.files().list( maxResults=1000,
                                            fields="nextPageToken, items(title)",
                                            orderBy="title",
                                            q="trashed=false",
                                            **kwargs ).execute()
        except apiclient.errors.HttpError as error:
            # XXX: we could be more fancy about this by identifying the error
            #      code and then doing something with the response body
            #      (e.g. parse JSON for more information) though simply
            #      printing it is enough for now.
            print( error )
            sys.exit( 1 )

        # start our results list or add to it, depending on whether this is is
        # the first time through the loop or not.
        if results is None:
            results = entries
        else:
            results['items'] += entries['items']

        next_page_token = entries.get( 'nextPageToken' )

    # return just the titles for each of the items found.
    name_list = [item['title'] for item in results.get( "items" )]

    return name_list

def get_matching_file_names( name_list, name_pattern, series_pattern ):
    """
    Takes a sorted list of file names and applies name and series patterns
    to create a filtered list of tuples comprised of matching names and
    a series number extracted from the name.

    Takes 3 arguments:

      name_list      - A list of file name strings.
      name_pattern   - Regular expression string that can be compiled with the re
                       module to filter names out of name_list.
      series_pattern - Regular expression string that can be compiled with the re
                       module to extract series numbers out of each filtered
                       name.

    Returns 1 value:

      filtered_list - List of tuples comprised of names and extracted series
                      numbers.
    """

    name_filter = re.compile( name_pattern )

    # make the series match a group so that we can find it.
    series_re   = re.compile( ".*(?P<series>" + series_pattern + ").*" )

    # list of pairs containing the file names of interest, and the portion
    # of their names representing the series.
    filtered_list = []

    for name in name_list:
        if name_filter.match( name ):
            # NOTE: we assume that our series are numeric.  unclear whether
            #       we care about anything else.
            filtered_list.append( (name, int( series_re.match( name ).group( 'series' )) ) )

    return filtered_list

def list_gaps( names_numbers_list, gap_range ):
    """
    Takes a list of file and series number pairs, as well as a range of
    acceptable gaps, and finds the gaps in the series.  Each series gap is
    displayed to standard output with its size and the files that bracket the
    gap.

    Takes 2 arguments:

      names_numbers_list - List of file name and series number pairs.
      gap_range          - List of lower and upper bounds on the acceptable gap
                           sizes.

    Returns 1 value:

      gaps - List of pairs identifying the series numbers bracketing each gap.
    """

    # list of pairs (start, stop) identifying gaps within the file names.
    gaps = []

    # start counting from the first in the series.
    previous_name, previous_number = names_numbers_list[0]

    # walk through the names_numbers list and look for gaps that are in the range
    # of [gap_range[0], gap_range[1]).  keep track of any we find and display
    # the files that bracket them.
    for (current_name, current_number) in names_numbers_list:
        current_gap_size = current_number - previous_number
        if gap_range[0] <= current_gap_size < gap_range[1]:
            gaps.append( [previous_number + 1, current_number - 1] )

            print( "Gap of size {0:d} between {1:s} and {2:s}".format( current_number - previous_number,
                                                                       previous_name,
                                                                       current_name ) )

        previous_name, previous_number = current_name, current_number

    return gaps

def load_file_names( file_name ):
    """
    Loads a list of pickled file names from disk.  If the file exists but
    isn't a valid pickle jar, then an exception is raised.  If the file
    doesn't exist, an empty list is returned.

    Takes 1 argument:

      file_name - Name of pickled file to load.

    Returns 1 value:

      name_list - List of file names contained in file_name.
    """

    # treat non-existent files as empty.
    try:
        stat_s = os.stat( file_name )
    except FileNotFoundError:
        return []

    # though everything else must be valid pickle jars.
    try:
        with open( file_name, 'rb' ) as f:
            name_list = pickle.load( f )
    except Exception as e:
        print( "Failed to load file names from {0:s}!".format( file_name ),
               file=sys.stderr )
        sys.exit( 1 )

    return name_list

def save_file_names( file_name, names ):
    """
    Saves a list of names to disk.  If the file specified already exists it
    will be overwritten.
    """

    # save these to disk.
    with open( file_name, 'wb' ) as f:
        pickle.dump( names, f, pickle.HIGHEST_PROTOCOL )

def parse_gap_range( gap_range_str ):
    """
    Parses one or two integers defining a non-empty range specifying gaps to
    search for within a series of files.  Throws a ValueError exception if
    the range specified does not meet the following criteria:

      * Range boundaries are positive integers, larger than one.
      * The upper bound on ranges is larger than the lower bound.

    Takes 1 argument:

      gap_range_str - String of the form <lower>[,<upper>] that defines a
                      non-empty range gaps, that covers [<lower>, <upper>) to
                      search for.

    Returns 1 value:

      gap_range - List of two integers bracketing the acceptable range of gaps.
    """

    gap_range = str.split( gap_range_str, ',' )

    # ensure that we got either "<lower>" or "<lower>,<upper>".  the latter
    # takes the default <upper>.
    if not 0 < len( gap_range ) < 3:
        print( "Invalid gap range string ({0:s}).  Must be of the form '<lower>[,<upper>]'.".format( gap_range_str ),
               file=sys.stderr )
        raise ValueError( "Malformed gap range pair." )
    elif len( gap_range ) < 2:
        gap_range.append( MAXIMUM_GAP_SIZE )

    # verify that we actually got numbers defining our range.
    try:
        gap_range = [int( string ) for string in gap_range]
    except ValueError:
        print( "Invalid gap range string ({0:s}).  Gap range boundaries must be integers.".format( gap_range_str ),
               file=sys.stderr )
        raise ValueError( "Non-integral range boundaries." )

    # ensure that 2 <= <lower> < <upper> so that we both detect gaps (and not
    # sequentially numbered files) and have at least one gap size to detect.
    if (gap_range[0] < 2 or
        not (gap_range[0] < gap_range[1]) or
        gap_range[0] == gap_range[1]):
        print( "Invalid gap size string ({0:s}).  <lower> must an integer greater than 1, and <upper> must be bigger than <lower>.".format( gap_range_str ),
                       file=sys.stderr )
        raise ValueError( "Invalid ranges specified." )

    print( "Gap is limited to {0:d}-{1:d}".format( gap_range[0], gap_range[1] ) )

    return gap_range

def main( argv ):
    """
    Takes the command line of the script, comprised of the application name and
    optional patterns for file names and series components and displays gaps in
    them to standard output.
    """

    # bounds to determing acceptable gaps within file series numbers.
    gap_range = [MINIMUM_GAP_SIZE, MAXIMUM_GAP_SIZE]

    # file name containing our list of file names.  used as an offline cache
    # for the user's Google Drive listing if specified as a command line
    # option.
    list_file_name = None

    # list of file names from the user's Google Drive.
    full_name_list = []

    # parse our command line options.
    try:
        opts, args = getopt.getopt( argv[1:], "F:hn:" )
    except getopt.GetoptError as error:
        sys.stderr.write( "Error processing option: %s\n" % str( error ) )
        sys.exit( 1 )

    # handle any valid options were were presented.
    for opt, arg in opts:
        if opt == '-F':
            list_file_name = arg
        elif opt == '-h':
            usage( argv[0] )
            sys.exit( 0 )
        elif opt == '-n':
            try:
                gap_range = parse_gap_range( arg )
            except ValueError:
                sys.exit( 1 )

    # if the user didn't specify a pattern.
    if len( args ) < 1:
        name_pattern, series_pattern = DEFAULT_NAME_PATTERN, DEFAULT_SERIES_PATTERN
    elif len( args ) == 2:
        name_pattern, series_pattern = args[0], args[1]
    else:
        sys.stderr.write( "Invalid number of arguments supplied.  Expected 0-2, received {0:d}.\n".format( len( args ) ) )
        sys.exit( 1 )

    # get a list of file names either from disk or from Google Drive.
    if list_file_name is not None:
        full_name_list = load_file_names( list_file_name )

    if len( full_name_list ) == 0:
        # acquire our credentials.
        try:
            credentials = get_drive_credentials( )
        except RuntimeError as error:
            sys.stderr.write( "Failed to acquire Google Drive credentials: {0:s}.\n".format( error.args[0] ) )
            sys.exit( 1 )

        # get the files we're working with.
        full_name_list = get_live_file_names( credentials )

        # save our query result if requested.
        if list_file_name is not None:
            save_file_names( list_file_name, full_name_list )

    print( "Number of files found in Drive: {0:d}".format( len( full_name_list ) ) )

    # identify the files we're interested in.  if there aren't any that match
    # our patterns, then we can bail early.
    filtered_list = sorted( get_matching_file_names( full_name_list,
                                                     name_pattern,
                                                     series_pattern ),
                            key=lambda pair: pair[1] )

    if len( filtered_list ) == 0:
        print( "Did not match anything matching names against '{0:s}' and series against '{1:s}'.".format( name_pattern,
                                                                                                           series_pattern ) )
        return

    # display what the user has requested, if they have.
    list_gaps( filtered_list, gap_range )

if __name__ == "__main__":
    main( sys.argv )
