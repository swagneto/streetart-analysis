#!/usr/bin/env python

# Takes a list of image file paths and updates a database to include photo
# records for them.  Any images that are already known to the database are
# updated with the photos current metadata, otherwise a new photo record is
# inserted.
#
# NOTE: Currently this does little, if any, error checking.  Buyer beware.
#

import sys

import GraffitiAnalysis.database as grafdb
import GraffitiAnalysis.utility as grafutil

import piexif

if len( sys.argv ) != 3:
    print( "Usage: {:s} <database> <photo list file>".format( sys.argv[0] ),
           file=sys.stderr )
    sys.exit( 1 )

database_filename   = sys.argv[1]
files_list_filename = sys.argv[2]

# parse our files path file.
with open( files_list_filename, "rt" ) as f:
    files_list_string = f.read()

    # get a stripped, sorted list of photos to insert into the database.
    # ignore the last entry since it's empty - it's a by product of splitting
    # on new lines.
    files_list        = list( map( lambda x: x.strip(),
                                   files_list_string.split( "\n" ) ) )[:-1]
    files_list.sort()

    # XXX: check for duplicates.

# acquire all of the photo records so we can update/add to them.
db     = grafdb.Database( database_filename )
photos = db.get_photo_records()

# build a map from filename to PhotoRecord so we know when we need to update
# an existing record vice inserting a new one.
known_files = dict()
for photo in photos:
    known_files[photo["filename"]] = photo

for file_name in files_list:
    fields = dict()

    # parse the Exif data for this file.  set some (not so) suitable defaults
    # when we can't get Exif data.
    try:
        exif_data  = piexif.load( file_name )

        fields["rotation"]   = grafutil.exif_orientation_to_rotation( exif_data["0th"][piexif.ImageIFD.Orientation] )
        fields["resolution"] = (exif_data["Exif"][piexif.ExifIFD.PixelXDimension],
                                exif_data["Exif"][piexif.ExifIFD.PixelYDimension])
        fields["photo_time"] = grafutil.datetime_string_to_timestamp( exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal].decode( "utf-8" ),
                                                                      ":", ":" )
    except:
        fields["rotation"]   = 0
        fields["resolution"] = (0, 0)
        fields["photo_time"] = 0

    if file_name in known_files:
        print( "'{:s}' already exists in the database, skipping.".format( file_name ) )
        continue

    photo = db.new_photo_record( file_name, **fields )

    db.mark_data_dirty()

# only update the database if we made changes.
if db.are_data_dirty():
    db.save_database()
else:
    print( "Database was unchanged.  Not saving." )
