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
