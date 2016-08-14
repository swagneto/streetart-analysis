import numpy as np
import pandas as pd

# XXX: do we do something special with the timestamps in the *_to_dataframe()
#      routines?

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

    return pd.DataFrame.from_records( photo_tuples,
                                      index="id",
                                      columns=photo_columns )

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

    return pd.DataFrame.from_records( art_tuples,
                                      index="id",
                                      columns=art_columns )

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
