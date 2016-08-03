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

import piexif

def orientation_to_rotation( exif_orientation ):
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

      exif_orientation - Exif orientation value.  See the Exif standards for
                         the full range of values and above for the values
                         supported.

    Returns 1 value:

      degrees - Degrees, clockwise, the camera was rotated when the image
                was captured.

    """

    if exif_orientation == 1:
        # no rotation needed.
        return 0
    elif exif_orientation == 3:
        # image is upside down.
        return 180
    elif exif_orientation == 6:
        # image is rotated counter-clockwise.
        return 270
    elif exif_orientation == 8:
        # image is rotated clockwise.
        return 90

    raise RuntimeError( "Unknown Exif orientation seen {:d}!".format( exif_orientation ) )

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
    # parse the Exif data for this file.
    # XXX: handle the case where no Exif data exists.
    exif_data  = piexif.load( file_name )

    rotation   = orientation_to_rotation( exif_data["0th"][piexif.ImageIFD.Orientation] )
    resolution = (exif_data["Exif"][piexif.ExifIFD.PixelXDimension],
                  exif_data["Exif"][piexif.ExifIFD.PixelYDimension])

    if file_name in known_files:
        # NOTE: we can't update the resolution of an existing record.
        photo = known_files[file_name]
    else:
        photo = db.new_photo_record( file_name, resolution )

    if photo["rotation"] != rotation:
        photo["rotation"] = rotation

        db.mark_data_dirty()

# only update the database if we made changes.
if db.are_data_dirty():
    db.save_database()
else:
    print( "Database was unchanged.  Not saving." )
