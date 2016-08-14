import gpxpy

def get_gpx_tracks( gpx_file_names ):
    """
    Parses one or more GPX files into a list of GPX objects.  Invalid GPX
    files are handled, the failure is logged to standard error, and a
    placeholder None is inserted into the created list.

    Takes 1 argument:

      gpx_file_names - A list of GPX file names to parse.  This may be a
                       single string as a convenience.

    Returns 1 value:

      gpx_files - A list of GPX objects, one for each file name in
                  gpx_file_names.  Files that cannot be parsed have None in
                  their corresponding position instead of an GPX object.
                  If gpx_file_names was a single string, this will be a
                  scalar.

    """

    # help the user in a common use case by creating the list for them.
    if type( gpx_file_names ) != list:
        gpx_file_names = [gpx_file_names]

    # build a list of GPX objects, one per file, with None's for any that
    # can't be parsed.
    gpx_files = []
    for gpx_file_name in gpx_file_names:
        with open( gpx_file_name, 'r' ) as f:
            try:
                gpx_file = gpxpy.parse( f )
            except Exception as e:
                import sys

                gpx_file = None

                print( "Failed to parse {:s} ({}.".format( gpx_file_name, e ),
                       file=sys.stderr )

        gpx_files.append( gpx_file )

    # help the user in a common use case by unpacking a single element list
    # into the corresponding scalar.
    if len( gpx_file_names ) == 1:
        gpx_files = gpx_files[0]

    return gpx_files
