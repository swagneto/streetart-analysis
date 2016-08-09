import calendar

def datetime_string_to_timestamp( string, date_separator="/", time_separator=":" ):
    """
    Converts a date/time string of the form:

      YYYY<date_sep>MM<date_sep>DD hh<time_sep>mm<time_sep>ss

    into an integral seconds since the Epoch.

    Takes 3 arguments:

      string         - The date/time string to convert.
      date_separator - Optional separator for the date portion of string.  If
                       omitted, defaults to "/".
      time_separator - Optional separator for the time portion of string.  If
                       omitted, defaults to ":".

    Returns 1 value:

      seconds - Integral seconds since the Epoch.  If string does not
                represent a valid time, seconds will be zero.

    """

    try:
        date_string, time_string = string.split()

        date_tuple = tuple( map( int, date_string.split( date_separator ) ) )
        time_tuple = tuple( map( int, time_string.split( time_separator ) ) )

        # note that we don't have the day of year/month information.  we also
        # want a non-DST timestamp.
        seconds = calendar.timegm( (*date_tuple, *time_tuple, 0, 0, 0) )
    except:
        seconds = 0

    return seconds

def exif_orientation_to_rotation( orientation ):
    """
    Converts the Exif orientation value into the corresponding number of
    degrees rotated, clockwise, the camera was when the image was captured.
    Unknown Exif orientations will cause a RuntimeError exception to be
    raised.

    NOTE: This is not the number of degrees needed to correct for the
          Exif orientation flag.

    NOTE: Not all Exif orientations are supported since they cannot be
          expressed as a simple rotation - some require a rotation and
          a flip about an axis.  Currently only the following orientations
          are supported:

            1, 3, 6, and 8

    Takes 1 argument:

      orientation - Exif orientation value.  See the Exif standards for
                    the full range of values and above for the values
                    supported.

    Returns 1 value:

      degrees - Degrees, clockwise, the camera was rotated when the image
                was captured.

    """

    if orientation == 1:
        # no rotation needed.
        return 0
    elif orientation == 3:
        # image is upside down.
        return 180
    elif orientation == 6:
        # image is rotated counter-clockwise.
        return 270
    elif orientation == 8:
        # image is rotated clockwise.
        return 90

    raise RuntimeError( "Unknown Exif orientation seen {:d}!".format( orientation ) )
