#!/usr/bin/env python

# script demonstrating how Exif modification is not a lossless operation.
# JPEGs on disk (presumably from different devices) are read in, have their
# location modified, and then written back out.  the size of the original
# file is displayed along with the size of the newly written file to show
# how much data is lost.
#
# things learned from this:
#
#  * PIL relies upon external libraries to manipulate Exif data.  it will
#    inherit any strengths and weaknesses from the Exif library while
#    introducing the fact that saving JPEG files will recompress the image
#    data.
#
#  * piexif throws away information when saving Exif data with unknown
#    content, though does not corrupt the data stream like pexif does.
#    And piexif works with Python 2 and 3 where as pexif only works with
#    Python 2.

# NOTE: we need to be careful since not all of the libraries we're using are
#       Python 2/3 compatible.
from __future__ import print_function

import getopt
import io
import os
import sys

def get_exif_size( file_name ):
    """
    Returns the length of the Exif data in the supplied file.

    Takes 1 argument:

      file_name - Name of file who's Exif data should be measured.

    Returns 1 value:

      exif_size - Length, in bytes, of the Exif data.
    """

    import piexif

    exif_dict  = piexif.load( file_name )
    exif_bytes = piexif.dump( exif_dict )

    return len( exif_bytes )

def test_piexif( input_file_name, output_file_name, args ):
    """
    Tests Exif manipulation using Piexif performing JPEG I/O with buffered
    reads and writes.

    Takes 3 arguments:

      input_file_name  - Path of input JPEG file.
      output_file_name - Path of output JPEG file.
      args             - Dictionary of arguments provided to the test.  This
                         is unused.

    Returns nothing.
    """

    import piexif

    jpeg_data = open( input_file_name, "rb" ).read()
    o         = io.BytesIO()

    # use piexif to extract our Exif data and insert it back into the raw JPEG
    # byte stream.
    exif_dict = piexif.load( input_file_name )
    exif_dict['GPS'][2] = ((1, 1), (2, 1), (3, 1))
    exif_dict['GPS'][4] = ((4, 1), (5, 1), (6, 1))
    exif_bytes = piexif.dump( exif_dict )

    piexif.insert( exif_bytes, jpeg_data, o )

    with open( output_file_name, "wb" ) as file:
        file.write( o.getvalue() )

    munged_jpeg_data  = open( output_file_name, "rb" ).read()
    munged_exif_dict  = piexif.load( output_file_name )
    munged_exif_bytes = piexif.dump( munged_exif_dict )

def test_pexif( input_file_name, output_file_name, args ):
    """
    Tests Exif manipulation and JPEG I/O using pexif.

    Takes 3 arguments:

      input_file_name  - Path of input JPEG file.
      output_file_name - Path of output JPEG file.
      args             - Dictionary of arguments provided to the test.  This
                         is unused.

    Returns nothing.
    """

    from pexif import JpegFile

    ef = JpegFile.fromFile( input_file_name )
    ef.set_geo( 1.234567, -9.876543 )
    ef.writeFile( output_file_name )

def test_piexif_with_pil( input_file_name, output_file_name, args ):
    """
    Tests Exif manipulation using Piexif performing JPEG I/O with PIL.
    Note that PIL performs image decompression and recompression which
    will likely alter the contents of image.

    Takes 3 arguments:

      input_file_name  - Path of input JPEG file.
      output_file_name - Path of output JPEG file.
      args             - Dictionary of arguments provided to the test.  This
                         may contain a "quality" key that specifies a
                         quality parameter suitable for use when saving a JPEG
                         with PIL.

    Returns nothing.
    """
    import piexif
    from PIL import Image

    # use piexif to extract our Exif data.
    exif_dict = piexif.load( input_file_name )
    exif_dict['GPS'][2] = ((1, 1), (2, 1), (3, 1))
    exif_dict['GPS'][4] = ((4, 1), (5, 1), (6, 1))
    exif_bytes = piexif.dump( exif_dict )

    # use PIL to specify raw Exif data when saving.
    #
    # NOTE: this will reencode the file that has been opened which is likely
    #       not what a user wants.
    im = Image.open( input_file_name )
    im.save( output_file_name, exif=exif_bytes, **args )

def test_pyexiv2( input_file_name, output_file_name, args ):
    """
    Tests Exif manipulation using PyExiv2.

    Takes 3 arguments:

      input_file_name  - Path of input JPEG file.
      output_file_name - Path of output JPEG file.
      args             - Dictionary of arguments provided to the test.  This
                         is unused.

    Returns nothing.
    """

    # NOTE: this is incomplete as I could never get pyexiv2 installed properly
    #       under Ubuntu 14.04 and Conda using Python 3.
    raise ImportError( "Please implement this test." )

    import pyexiv2

    jpeg_data = open( input_file_name, "rb" ).read()
    o         = io.BytesIO()

    # read in our metadata.
    metadata = pyexiv2.ImageMetadata( input_file_name )
    metadata.read()

    # XXX: modify the GPS location.
    # XXX: serialize metadata and insert it into the byte stream.

    with open( output_file_name, "wb" ) as file:
        file.write( o.getvalue() )

# path to test case JPEGs.
SOURCE_DIRECTORY = "data/exif-modification-demo"

# simple extension to search for.  this clearly excludes things like .JPG,
# .jpeg, files that are JPEGs but aren't named as such, etc.
JPEG_SUFFIX      = ".jpg"

# list of JPEGs we've found on disk to test.
jpg_file_names = []

# table of tests to run.  tuples of test name, test function, and arguments to
# supply to said test function.  the test name is prepended to each file
# tested.
function_table = [("piexif",               test_piexif,          {}),
                  ("piexif+pil_q=default", test_piexif_with_pil, {}),
                  ("piexif+pil_q=95",      test_piexif_with_pil, { "quality": 95 }),
                  ("piexif+pil_q=100",     test_piexif_with_pil, { "quality": 100 }),
                  ("pexif",                test_pexif,           {}),
                  ("py3exiv2",             test_pyexiv2,         {})]

# flag controlling whether we are debugging or not.  this determines whether
# generated files are left on disk after creation or not.  by default, do not
# leave files on disk.
debug_flag = False

# parse our command line options.
try:
    opts, args = getopt.getopt( sys.argv[1:], "F:hn:" )
except getopt.GetoptError as error:
    print( "Error processing option: {0:s}.".format( str( error ) ), file=sys.stderr )
    sys.exit( 1 )

# handle any valid options were were presented.
for opt, arg in opts:
    if opt == '-d':
        debug_flag = True

# get a list of JPEGs to test in our target directory.
#
# NOTE: we only pull the first iteration of file names from os.walk() so that
#       this could be easily extended to recursing through the source
#       directory's sub-directories.
for (dir_path, dir_names, file_names) in os.walk( SOURCE_DIRECTORY ):
    file_names = [file_name for file_name in file_names if file_name.endswith( JPEG_SUFFIX ) ]
    jpg_file_names.extend( file_names )

    break

# bail if there isn't anything to do.
if len( jpg_file_names ) == 0:
    print( "No JPEGs were found in {0:s}.  Exiting.".format( SOURCE_DIRECTORY ),
           file=sys.stderr )
    sys.exit( 1 )

print( "{0:60s} {1:9s}  {2:5s}  {3:9s}  {4:5s}".format( "File Name",
                                                        "File Size",
                                                        "Exif Size",
                                                        "File Diff",
                                                        "Exif Diff" ) )

# walk through each file and run each test on it.
for file_name in jpg_file_names:
    input_file_name = os.path.join( SOURCE_DIRECTORY, file_name )
    input_file_size = os.stat( input_file_name ).st_size
    input_exif_size = get_exif_size( input_file_name )

    print( "{0:60s} {1:9d}   {2:5d}".format( input_file_name,
                                             input_file_size,
                                             input_exif_size ) )

    for (test_name, test_func, args) in function_table:
        # output files reside in the current directory with the test name
        # prepended to the original file name.
        output_file_name = test_name + "-" + file_name

        try:
            test_func( input_file_name, output_file_name, args )
        except Exception as e:
            # NOTE: we'll usually get here due an import error or a problem
            #       parsing code that is only available in a different version
            #       of the Python interpreter.
            print( "{0:60} {1:^9s}    {2:^5s}  {3:^9s}   {4:^9s}".format( output_file_name,
                                                                          "N/A",
                                                                          "N/A",
                                                                          "N/A",
                                                                          "N/A" ) )
        else:
            # compute the output file and Exif sizes and their differences.
            # we assume that files will shrink due to lossy Exif manipulation
            # so those should be displayed as negative values.
            output_file_size = os.stat( output_file_name ).st_size
            output_exif_size = get_exif_size( output_file_name )
            file_difference  = output_file_size - input_file_size
            exif_difference  = output_exif_size - input_exif_size

            print( "{0:60} {1:9d}   {2:5d}   {3:9d}    {4:5d}".format( output_file_name,
                                                                       output_file_size,
                                                                       output_exif_size,
                                                                       file_difference,
                                                                       exif_difference ) )

            # keep the generated files only if we're debugging.  otherwise
            # these just take up space.
            if not debug_flag:
                os.remove( output_file_name )

    print( "" )
