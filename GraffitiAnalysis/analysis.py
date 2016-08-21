import calendar

import numpy as np
import pandas as pd

# XXX: do we do something special with the timestamps in the *_to_dataframe()
#      routines?

def correct_photo_timestamp( timestamp, remove=False ):
    """
    Adjusts a photo timestamp to correct for non-standard camera clocks.
    This adjusts for known clock drift, clock misconfiguration, or clocks set to
    non-UTC time zones.  "Removing" an adjustment is also possible to go from
    the correct, UTC time back to the original time.

    Currently this method understands and compensates for the following:

       1. Pictures taken before 2016/04/20 were in UTC-5 (CST).
       2. Pictures taken after 2016/04/20 were in UTC+1 (CEST).

    Takes 2 arguments:

      timestamp - The timestamp to adjust.
      remove    - Optional flag specifying whether the adjustment should be
                  undone.  If false, the adjustment is made, otherwise it is
                  undone.  If omitted, defaults to False.

    Returns 1 value:

      timestamp - The adjusted timestamp.

    """

    # the one threshold we handle is sometime on 2016/04/20 the camera's time
    # was moved from UTC-5 (CST) to UTC+1 (CEST due to misunderstanding which
    # timezone Sarajevo is in).
    cst_offset                 = 5 * 3600
    threshold_20160420_tuple   = (2016, 4, 20, 0, 0, 0, 0, 0, 0)
    threshold_20160420_seconds = calendar.timegm( threshold_20160420_tuple ) - cst_offset

    # seconds to add to get us to UTC+0. before we were UTC-5 and after we
    # were UTC+1.
    before_20160420_offset = 5 * 3600
    after_20160420_offset  = -3600

    # if we're removing the correction, switch the signs on our offsets.
    if remove == True:
        before_20160420_offset *= -1
        after_20160420_offset  *= -1

    # adjust things based on the single threshold we know about.
    if timestamp < threshold_20160420_seconds:
        timestamp += before_20160420_offset
    else:
        timestamp += after_20160420_offset

    return timestamp

def photos_to_dataframe( photos ):
    """
    Converts a list of PhotoRecord objects into a Pandas DataFrame.  Each
    record's identifier is used as the DataFrame index for quick access.  Each
    row in the DataFrame also includes a reference to the PhotoRecord object
    it is derived from.

    Takes 1 argument:

      photos - A list of PhotoRecord objects to convert.

    Returns 1 value:

      df - A DataFrame object with len( photos ) many rows.

    """

    # ordered list of processing states of photos.  these will be categories
    # in our DataFrame.
    photo_states = ["unreviewed",
                    "needs_review",
                    "reviewed"]

    # columns in the constructed DataFrame.
    photo_columns = ["id",
                     "filename",
                     "state",
                     "location",
                     "rotation",
                     "created_time",
                     "modified_time",
                     "photo_time",
                     "tags",
                     "record"]

    # create a list of tuples containing the contents of the PhotoRecords.
    photo_tuples = []
    for photo in photos:
        # handle missing locations and resolution information.
        if photo["location"] is None:
            location = (np.nan, np.nan)
        else:
            location = (photo["location"][0], photo["location"][1])

        if photo["resolution"] is None:
            resolution = (np.nan, np.nan)
        else:
            resolution = (photo["resolution"][0], photo["resolution"][1])

        photo_tuples.append( (photo["id"],
                              photo["filename"],
                              photo["state"],
                              location,
                              photo["rotation"],
                              photo["created_time"],
                              photo["modified_time"],
                              photo["photo_time"],
                              photo["tags"],
                              photo) )

    # create our base DataFrame that we'll doctor up.
    photos_df = pd.DataFrame.from_records( photo_tuples,
                                           index="id",
                                           columns=photo_columns )

    # convert our state to ordered categorical data so that we can rely on its
    # structure during analysis.
    photos_df["state"] = pd.Categorical( photos_df["state"],
                                         categories=photo_states,
                                         ordered=True )

    return photos_df

def arts_to_dataframe( arts, photos_df=None ):
    """
    Converts a list of ArtRecord objects into a Pandas DataFrame, possibly
    with references to a DataFrame representing the parent PhotoRecord
    objects.  Each record's identifier is used as the DataFrame index for
    quick access.  Each row in the DataFrame also includes a reference to the
    PhotoRecord object it is derived from as well as Pandas Series object
    representing the parent PhotoRecord's information.

    Takes 1 argument:

      arts - A list of ArtRecord objects to convert.

    Returns 1 value:

      df - A DataFrame object with len( arts ) many rows.

    """

    # ordered list of types of art.  these will be categories in our
    # DataFrame.
    art_types = ["tag",
                 "sticker",
                 "stencil",
                 "text",
                 "other",
                 "throwup",
                 "piece",
                 "mural"]

    # ordered list of sizes of art.  these will be categories in our
    # DataFrame.
    art_sizes = ["tiny",
                 "small",
                 "medium",
                 "large",
                 "huge"]

    # ordered list of qualities of art.  these will be categories in our
    # DataFrame.
    art_qualities = ["bad",
                     "poor",
                     "fair",
                     "good",
                     "excellent"]

    # ordered list of processing states of art.  these will be categories in
    # our DataFrame.
    art_states = ["unreviewed",
                  "needs_review",
                  "reviewed"]

    # columns in the constructed DataFrame.
    art_columns = ["id",
                   "photo_id",
                   "type",
                   "size",
                   "quality",
                   "state",
                   "region",
                   "tags",
                   "created_time",
                   "modified_time",
                   "artists",
                   "associates",
                   "vandals",
                   "photo_series",
                   "record"]

    # create a list of tuples containing the contents of the PhotoRecords.
    art_tuples = []
    for art in arts:
        # we can't provide Series information if we weren't handed a DataFrame.
        if photos_df is None:
            photo_series = None
        else:
            photo_series = photos_df.loc[art["photo_id"]]

        art_tuples.append( (art["id"],
                            art["photo_id"],
                            art["type"],
                            art["size"],
                            art["quality"],
                            art["state"],
                            art["region"],
                            art["tags"],
                            art["created_time"],
                            art["modified_time"],
                            art["artists"],
                            art["associates"],
                            art["vandals"],
                            photo_series,
                            art) )

    # create our base DataFrame that we'll doctor up.
    arts_df = pd.DataFrame.from_records( art_tuples,
                                         index="id",
                                         columns=art_columns )

    # convert several columns to ordered categorical data so that we can rely
    # on its structure during analysis.
    arts_df["type"] = pd.Categorical( arts_df["type"],
                                      categories=art_types,
                                      ordered=True )
    arts_df["size"] = pd.Categorical( arts_df["size"],
                                      categories=art_sizes,
                                      ordered=True )
    arts_df["quality"] = pd.Categorical( arts_df["quality"],
                                         categories=art_qualities,
                                         ordered=True )
    arts_df["state"] = pd.Categorical( arts_df["state"],
                                       categories=art_states,
                                       ordered=True )

    return arts_df

def gpx_to_dataframe( gpxs ):
    """
    Converts a list of GPX objects into a pair of Pandas DataFrames, one
    representing a concatenated track and the other all of the reported
    waypoints.  Both DataFrames are indexed by the track points' UTC
    timestamps.

    NOTE: Only the first track's first segment is used to create the
          DataFrame.

    NOTE: The original GPX objects are not referenced in the generated
          DataFrame since it unclear what would be most useful to capture.

    Takes 1 argument:

      gpxs - A list of GPX objects whose first track segments are converted
             into DataFrames.  A single GPX object may be supplied as a
             scalar as a convenience instead of creating a list out of it.

    Returns 2 values:

      tracks_dfs    - DataFrame representing the concatenated track.
      waypoints_dfs - DataFrame representing the waypoints.

    """

    track_columns = ["longitude",
                     "latitude",
                     "altitude",
                     "course",
                     "computed_speed",
                     "reported_speed",
                     "satellites",
                     "source",
                     "geoid_height",
                     "symbol",
                     "gpx_fix_type",
                     "hdop",
                     "vdop",
                     "pdop"]

    # our GPX data source doesn't populate much for waypoints, so we don't
    # bother creating useless columns.
    waypoint_columns = ["name",
                        "longitude",
                        "latitude",
                        "altitude",
                        "source"]

    tracks_df    = pd.DataFrame( [], columns=track_columns )
    waypoints_df = pd.DataFrame( [], columns=waypoint_columns )

    # help the user in a common use case by creating the list for them.
    if type( gpxs ) != list:
        gpxs = [gpxs]

    # walk through each GPX object creating new DataFrames and appending them
    # to the existing DataFrames.
    for gpx in gpxs:
        # XXX: assumes we only have a single track with a single segment in it.

        track_data = []
        times      = []
        for (point_index, point) in enumerate( gpx.tracks[0].segments[0].points ):
            track_data.append( [point.longitude,
                                point.latitude,
                                point.elevation,
                                point.course,
                                gpx.tracks[0].segments[0].get_speed( point_index ),
                                point.speed,
                                point.satellites,
                                point.source,
                                point.geoid_height,
                                point.symbol,
                                point.type_of_gpx_fix,
                                point.horizontal_dilution,
                                point.vertical_dilution,
                                point.position_dilution] )
            times.append( pd.Timestamp( point.time ) )

        # convert this track into a data frame and store it.
        tracks_df = pd.concat( [tracks_df,
                                pd.DataFrame( track_data,
                                              index=times,
                                              columns=track_columns )] )

        waypoint_data = []
        times         = []
        for (point_index, point) in enumerate( gpx.waypoints ):
            waypoint_data.append( [point.name,
                                   point.longitude,
                                   point.latitude,
                                   point.elevation,
                                   point.source] )
            times.append( pd.Timestamp( point.time ) )

        # convert this track into a data frame and store it.
        waypoints_df = pd.concat( [waypoints_df,
                                   pd.DataFrame( waypoint_data,
                                                 index=times,
                                                 columns=waypoint_columns )] )

    # work around gpxpy's speed computation for first points in a track.
    null_indices = tracks_df["computed_speed"].isnull()
    tracks_df.loc[null_indices, "computed_speed"] = 0.0

    # explicitly label our times as UTC as that's what is stored in GPX.
    tracks_df.tz_localize( "UTC", copy=False )
    waypoints_df.tz_localize( "UTC", copy=False )

    return (tracks_df, waypoints_df)
