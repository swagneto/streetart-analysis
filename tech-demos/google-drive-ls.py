#!/usr/bin/env python

# lists the contents of a Google Drive (associated with default credentials)
# similar to the Unix 'ls' command.  one or more folders may be listed,
# possibly recursively, with or without the contained files' metadata.  output
# may be sorted based on name or modification times as well.

from __future__ import print_function

import getopt
import os
import sys

def usage( script_name ):
    """
    Takes a name of the script (full path, name, etc) and prints its usage to standard
    output.
    """

    usage_format_string = """Usage: {0:s} [-h] [-l] [-R] [-r] [-t] [<path> [...]]

Lists the contents of a Google Drive account in a manner similar to the Unix utility
'ls'.  Zero or more paths may be specified and each path's information will be displayed
in the order provided.  If no paths are specified, the root of the Drive account will
be displayed.

The command line options above are described below:

  -h        Displays this help message and exits.
  -l        Additional metadata is printed for each <path>.
  -R        The contents of each <path> are recursively displayed.  By default, only the
            immediate contents are displayed.
  -r        The contents of each <path> are sorted in reverse.
  -t        The contents of each <path> are sorted by last modification time instead of
            the contents' names.
"""

    print( usage_format_string.format( script_name ) )

def normalize_path( path_name ):
    """
    Normalizes the supplied path so that it is suitable for use with Google Drive's
    API.  Currently does the following:

      * Ensures the path is absolute.
      * Removes runs of consecutive path separators.
      * Removes relative directories.

    Takes 1 argument:

      path_name - Path to normalize.

    Returns 1 value:

      normalized_name - Normalized version of path_name.
    """

    # let someone else do the heavy lifting for normalization.
    normalized_path_name = os.path.abspath( path_name )

    # subtract out the current directory's path if the original path was
    # relative.
    if path_name[0] != '/':
        normalized_path_name = normalized_path_name[len( os.getcwd() ):]

    # handle the special case of two path separators at the beginning.
    # exactly two path separators are left as is, though more than two are
    # normalized properly.
    if normalized_path_name[0:2] == os.sep + os.sep:
        normalized_path_name = normalized_path_name[1:]

    return normalized_path_name

def list_path( path_name, recurse_flag, reverse_sort_flag, time_sort_flag, verbose_flag ):
    """
    Displays the supplied path to standard output.  If the path to display is
    a folder, it's contents are displayed, otherwise the path itself will be
    displayed.

    Takes 5 arguments:

      path_name         - Path to the Drive content to list relative to the root of
                          the Drive, using an absolute path.
      recurse_flag      - Flag indicating that the contents of path_name should be
                          recursively displayed.
      reverse_sort_flag - Flag indicating whether the contents of path_name should
                          be sorted in reverse.
      time_sort_flag    - Flag indicating whether the contents of path_name should
                          be sorted by modification time instead of by name.
      verbose_flag      - Flag indicating whether additional metadata should be
                          displayed.

    Returns nothing.
    """

    print( "implement me! ({0:s})".format( path_name ) )

def main( argv ):
    """
    Takes the command line of the script, comprised of the application name and an optional
    list of directories whose contents will be listed and displays them to standard output.
    """

    # flag indicating whether each folder should be recursively listed.  by
    # default only the immediate contents of a folder are listed.
    recurse_flag      = False

    # flag indicating whether a folder's contents should be reversed when
    # listed.  by default contents will be displayed in "forward" order.
    # see time_sort_flag below for information on the sorting key.
    reverse_sort_flag = False

    # flag indicating whether additional metadata should be displayed for each
    # file listed.
    verbose_flag      = False

    # flag indicating that a folder's contents should be sorted by
    # modification time instead of name.  by default contents are sorted
    # lexiographically by each file's name, otherwise numerically by
    # each file's modification time.
    time_sort_flag    = False

    # parse our command line options.
    try:
        opts, args = getopt.getopt( argv[1:], "hlrRtv" )
    except getopt.GetoptError as error:
        sys.stderr.write( "Error processing option: %s\n" % str( error ) )
        sys.exit( 1 )

    # handle any valid options were were presented.
    for opt, arg in opts:
        if opt == '-h':
            usage( argv[0] )
            sys.exit()
        elif opt == '-l':
            verbose_flag = True
        elif opt == '-R':
            recurse_flag = True
        elif opt == '-r':
            reverse_sort_flag = True
        elif opt == '-t':
            time_sort_flag = True

    # if the user didn't specify any folders, default to the root folder.
    if len( args ) < 1:
        args = [ "/" ]

    # display what the user has requested, if they have.
    for path_name in args:
        list_path( normalize_path( path_name ),
                   recurse_flag,
                   reverse_sort_flag,
                   time_sort_flag,
                   verbose_flag )

if __name__ == "__main__":
    main( sys.argv )
