#!/usr/bin/env python

# Takes a list of GPX track files and interpolates a database's photo
# locations from the tracks.  All existing tracks are lost.

import getopt
import sys

import GraffitiAnalysis.database as grafdb
import GraffitiAnalysis.analysis as grafanal
import GraffitiAnalysis.tracks as graftracks

import numpy as np
import pandas as pd

# flag indicating that we're testing and no permanent changes should be made
# to the database.
testing_flag = False

# parse our command line options.
try:
    opts, args = getopt.getopt( sys.argv[1:], "t" )
except getopt.GetoptError as error:
    sys.stderr.write( "Error processing option: {:s}\n".format( error ) )
    sys.exit( 1 )

# handle any valid options were were presented.
for opt, arg in opts:
    if opt == '-t':
        testing_flag = True

# ensure that we got a database and at least one track file.
if len( args ) < 3:
    print( "Usage: {:s} [-t] <database> <track files>".format( sys.argv[0] ),
           file=sys.stderr )
    sys.exit( 1 )

# get our parameters from the command line.
database_filename = args[0]
track_file_names  = args[1:]

# load the database and get all of the records.
db     = grafdb.Database( database_filename )
photos = db.get_photo_records()

# create a single track DataFrame from the GPX files supplied.
gpxs        = graftracks.get_gpx_tracks( track_file_names )
track_df, _ = grafanal.gpx_to_dataframe( gpxs )

# create a new column for seconds since Epoch so we can interpolate against
# it.
track_df["timestamp"] = track_df.index.map( pd.Timestamp.timestamp )

# interpolate each photo's location individually.
for photo in photos:
    photo["location"] = (np.interp( photo["photo_time"],
                                    track_df["timestamp"],
                                    track_df["latitude"] ),
                         np.interp( photo["photo_time"],
                                    track_df["timestamp"],
                                    track_df["longitude"] ))
    print( "Time: {:f} -> {}.".format( photo["photo_time"],
                                       photo["location"] ) )

    # record this update if we're not testing.
    if not testing_flag:
        db.mark_data_dirty()

# only update the database if we made changes.
if db.are_data_dirty():
    db.save_database()
else:
    print( "Database was unchanged.  Not saving." )
