import time

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
        seconds = time.mktime( (*date_tuple, *time_tuple, 0, 0, 0) )
    except:
        seconds = 0

    return seconds
