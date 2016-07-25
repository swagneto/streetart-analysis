import collections
import time

from lxml import etree

def _read_xml_database( filename ):
    """
    Reads the database from the specified XML file.

    Takes 1 argument:

      filename - Path to the XML file containing the database contents.

    Returns 4 values:

      art_fields        - Dictionary containing various database field values
                          associated with art records.  Each key's value is
                          a list of strings.
      processing_states - List of values representing the states records may
                          be in.
      photo_records     - A list of photo objects, one per record in the
                          database.
      art_records       - A list of art objects, one per record in the
                          database.

    """

    def parse_simple_node_list( node, node_name, attribute_name ):
        """
        Parses a list of nodes from a parent node.  Each node in the list is
        expected to have the same element name and the value to parse is
        in the specified attribute.  The values are returned as a list with
        the same order as encountered.

        If an unexpected child node is encountered, a RuntimeError is raised
        indicating the node found.

        Takes 3 argument:

          node           - Element whose children nodes are to be parsed.
          node_name      - Name of the children nodes to parse.  Any child node
                           with a differing name will raise an exception.
          attribute_name - Name of the children nodes' attribute to parse for
                           values.

        Returns 1 value:

           values - List of value strings parsed from the children nodes.

        """

        values = []

        for child_index, child_node in enumerate( node ):
            if child_node.tag != node_name:
                raise RuntimeError( "Expected '{:s}' but got '{:s}' instead for child #{:d}.".format( node_name,
                                                                                                      child_node.tag,
                                                                                                      child_index ) )

            values.append( child_node.get( attribute_name ) )

        return values

    def parse_art_fields_node( art_fields_node ):
        """
        Parses the art fields from the supplied node.  Returns a dictionary
        with the following keys:

          types     - List of art types.
          sizes     - List of art sizes.
          qualities - List of art qualities.

        No validation is performed on the values parsed.

        Takes 1 argument:

          art_fields_node - Element whose children contain art field nodes to
                            parse.

        Returns 1 value:

          art_fields - Dictionary whose values are lists of the values parsed.
                       See above for a list of keys.
        """

        if len( art_fields_node ) != 3:
            raise RuntimeError( "Expected 3 children, received {:d}.".format( len( art_fields_node ) ) )

        # parse each of our children nodes as simple lists.
        if art_fields_node[0].tag != "Types":
            raise RuntimeError( "Expected the 1st child to be 'Types', received '{:s}'.".format( art_fields_node[0].tag ) )
        types = parse_simple_node_list( art_fields_node[0], "Type", "name" )

        if art_fields_node[1].tag != "Sizes":
            raise RuntimeError( "Expected the 2nd child to be 'Sizes', received '{:s}'.".format( art_fields_node[1].tag ) )
        sizes     = parse_simple_node_list( art_fields_node[1], "Size", "name" )

        if art_fields_node[2].tag != "Qualities":
            raise RuntimeError( "Expected the 3rd child to be 'Qualities', received '{:s}'.".format( art_fields_node[2].tag ) )
        qualities = parse_simple_node_list( art_fields_node[2], "Quality", "name" )

        return { "types":     types,
                 "sizes":     sizes,
                 "qualities": qualities }

    def parse_processing_states_node( processing_states_node ):
        """
        Parses the processing states from the supplied node.  Returns a list
        of values.  No validation is performed on the values parsed.

        Takes 1 argument:

          processing_states_node - Element whose children nodes contain the
                                   processing states to parse.

        Returns 1 value:

          processing_states - List of processing states parsed.

        """

        return parse_simple_node_list( processing_states_node, "State", "name" )

    def parse_artists_node( artists_node ):
        """
        Parses the artists from the supplied node.  Returns a list of values.
        No validation is performed on the values parsed.

        Takes 1 argument:

          artists_node - Element whose children nodes contain the artists to
                         parse.

        Returns 1 value:

          artists - List of artists parsed.

        """

        return parse_simple_node_list( artists_node, "Artist", "name" )

    def parse_fields_node( fields_node ):
        """
        Parses the databases fields from the supplied node.  Returns a
        dictionary for the art fields and a list of artists.  The dictionary's
        keys are:

          types     - List of art types.
          sizes     - List of art sizes.
          qualities - List of art qualities.

        No validation is performed on the values parsed.

        Takes 1 argument:

          fields_node - Element whose children nodes contain the art fields,
                        processing states, and artists to parse.

        Returns 2 values:

          art_fields        - Dictionary whose values are lists of the values
                              parsed.  See above for a list of keys.
          processing_states - List of processing states.

        """

        if len( fields_node ) != 3:
            raise RuntimeError( "parse_fields_node(): Expected 3 nodes but got {:d}.".format( len( fields_node ) ) )

        if fields_node[0].tag != "ArtFields":
            raise RuntimeError( "" )
        art_fields = parse_art_fields_node( fields_node[0] )

        if fields_node[1].tag != "ProcessingStates":
            raise RuntimeError( "" )
        processing_states = parse_processing_states_node( fields_node[1] )

        if fields_node[2].tag != "Artists":
            raise RuntimeError( "" )
        artists = parse_artists_node( fields_node[2] )

        return ({ "types":     art_fields["types"],
                  "sizes":     art_fields["sizes"],
                  "qualities": art_fields["qualities"],
                  "artists":   artists },
                 processing_states )

    def parse_photos_node( photos_node ):
        """
        Parses a Photos node into a list of PhotoRecord objects.  No
        validation is performed on the values parsed.

        Takes 1 argument:

          photos_node - Element whose children represent the database's photo
                        records.

        Returns 1 value:

          photos - List of PhotoRecord objects parsed.

        """

        photos = []

        for photo_index, photo_node in enumerate( photos_node ):
            if photo_node.tag != "Photo":
                raise RuntimeError( "Expected a Photo node but got {:s} [#{:d}].".format( photo_node.tag,
                                                                                          photo_index ) )

            # get a proper dictionary of this node's attributes.
            attributes    = photo_node.attrib

            # these are our mandatory arguments for building a PhotoRecord...
            id            = int( attributes.pop( "id", None ) )
            filename      = attributes.pop( "filename", None )
            resolution    = attributes.pop( "resolution", None )

            # ... and these are the optional ones.
            state         = attributes.pop( "processing_state", None )  # name change.
            created_time  = float( attributes.pop( "created_time", None ) )
            modified_time = float( attributes.pop( "modified_time", None ) )
            location      = attributes.pop( "location", None )
            rotation      = int( attributes.pop( "rotation", None ) )

            # handle conversion between our XML and internal Python
            # representations.  resolutions are specified as "NxM" and
            # locations as "X, Y".
            resolution = [size for size in map( int, resolution.split( "x" ) )]
            location   = [where for where in map( float, location.split( "," ) )]

            #
            # NOTE: all of the remaining attributes are fine to be passed as is.
            #
            photos.append( PhotoRecord( id,
                                        filename,
                                        resolution,
                                        created_time=created_time,
                                        modified_time=modified_time,
                                        location=location,
                                        rotation=rotation,
                                        **attributes ) )

        return photos

    def parse_arts_node( arts_node ):
        """
        Parses a Arts node into a list of ArtRecord objects.  No validation is
        performed on the values parsed.

        Takes 1 argument:

          art_node - Element whose children represent the database's art
                     records.

        Returns 1 value:

          art - List of ArtRecord objects parsed.

        """

        art = []

        for art_index, art_node in enumerate( arts_node ):
            if art_node.tag != "Art":
                raise RuntimeError( "Expected a Art node but got {:s} [#{:d}].".format( art_node.tag,
                                                                                        art_index ) )

            # get a proper dictionary of this node's attributes.
            attributes    = art_node.attrib

            # these are our mandatory arguments for building a ArtRecord...
            id            = int( attributes.pop( "id", None ) )
            photo_id      = int( attributes.pop( "photo_id", None ) )
            art_type      = attributes.pop( "type", None )

            # ... and these are the optional ones.
            state         = attributes.pop( "processing_state", None )  # name change.
            artists       = attributes.pop( "artists", None )
            associates    = attributes.pop( "associates", None )
            vandals       = attributes.pop( "vandals", None )
            created_time  = float( attributes.pop( "created_time", None ) )
            modified_time = float( attributes.pop( "modified_time", None ) )
            region        = attributes.pop( "region", None )

            # handle conversion between our XML and internal Python
            # representations.  artists, associates, and vandals are all comma
            # delimited lists.  region is a comma delimited 4-tuple of
            # normalized floats.
            artists    = [string for string in map( lambda x: x.strip(), artists.split( "," ) )]
            associates = [string for string in map( lambda x: x.strip(), associates.split( "," ) )]
            vandals    = [string for string in map( lambda x: x.strip(), vandals.split( "," ) )]

            if region is not None:
                region = tuple( [value for value in map( float, region.split( "," ))] )

            art.append( ArtRecord( id,
                                   photo_id,
                                   art_type,
                                   artists=artists,
                                   associates=associates,
                                   vandals=vandals,
                                   state=state,
                                   region=region,
                                   created_time=created_time,
                                   modified_time=modified_time,
                                   **attributes ) )

        return art

    def validate_art_fields( art_fields, processing_states ):
        """
        Validates the art fields and processing states to ensure that they are
        suitable for processing.  Ensures that there is at least one value
        for each field and that there aren't duplicates within a field.

        If the supplied arguments are invalid a RuntimeError describing the
        validation error is raised.

        Takes 2 arguments:

          art_fields        - Dictionary (from parse_fields_node()) to validate.
          processing_states - List of processing states to validate.

        Returns nothing.

        """

        # validate that we did not have any duplicate fields in what we read.
        duplicate_art_types         = [item for item, count in collections.Counter( fields[0]["types"] ).items() if count > 1]
        duplicate_art_sizes         = [item for item, count in collections.Counter( fields[0]["sizes"] ).items() if count > 1]
        duplicate_art_qualities     = [item for item, count in collections.Counter( fields[0]["qualities"] ).items() if count > 1]
        duplicate_artists           = [item for item, count in collections.Counter( fields[0]["artists"] ).items() if count > 1]
        duplicate_processing_states = [item for item, count in collections.Counter( fields[1] ).items() if count > 1]

        if len( duplicate_art_types ) > 0:
            raise RuntimeError( "Duplicate art types: {:s}".format( ", ".join( duplicate_art_types ) ) )
        elif len( fields[0]["types"] ) == 0:
            raise RuntimeError( "No art types were parsed." )

        if len( duplicate_art_sizes ) > 0:
            raise RuntimeError( "Duplicate art sizes: {:s}".format( ", ".join( duplicate_art_sizes ) ) )
        elif len( fields[0]["sizes"] ) == 0:
            raise RuntimeError( "No art sizes were parsed." )

        if len( duplicate_art_qualities ) > 0:
            raise RuntimeError( "Duplicate art qualities: {:s}".format( ", ".join( duplicate_art_qualities ) ) )
        elif len( fields[0]["qualities"] ) == 0:
            raise RuntimeError( "No art qualities were parsed." )

        if len( duplicate_artists ) > 0:
            raise RuntimeError( "Duplicate artists: {:s}".format( ", ".join( duplicate_artists ) ) )
        elif len( fields[0]["artists"] ) == 0:
            raise RuntimeError( "No artists were parsed." )

        if len( duplicate_processing_states ) > 0:
            raise RuntimeError( "Duplicate aprocessing states: {:s}".format( ", ".join( duplicate_processing_states ) ) )
        elif len( fields[1] ) == 0:
            raise RuntimeError( "No processing states were parsed." )

    def validate_identifiers( photos, art ):
        """
        Validates the photo and art records to ensure that they are suitable
        for processing.  Ensures that every record's identifier is unique
        within its class, and that every art record has a parent photo record.

        If the supplied arguments are invalid a RuntimeError describing the
        validation error is raised.

        Takes 2 arguments:

          photos - List of PhotoRecord objects to validate.
          art    - List of ArtRecord objects to validate.

        Returns nothing.

        """

        # validate that we did not have any duplicates in our photo record
        # identifiers.
        photo_ids = dict()
        for photo in photos:
            if photo["id"] in photo_ids:
                photo_ids[photo["id"]] += 1
            else:
                photo_ids[photo["id"]] = 1

        duplicate_photo_ids = [photo_id for photo_id, count in photo_ids.items() if count > 1]

        # validate that we don't have duplicate art record identifiers, as well as
        # seeing if we have any orphaned art records (read: no parent photo
        # record).
        art_ids          = dict()
        orphaned_art_ids = []
        for record in art:
            if record["id"] in art_ids:
                art_ids[record["id"]] += 1
            else:
                art_ids[record["id"]] = 1

            if record["photo_id"] not in photo_ids:
                orphaned_art_ids.append( record["id"] )

        duplicate_art_ids = [art_id for art_id, count in art_ids.items() if count > 1]

        if len( duplicate_photo_ids ) > 0:
            raise RuntimeError( "Duplicate photo ID: {:s}.".format( ", ".join( map( str, duplicate_photo_ids ) ) ) )

        if len( duplicate_art_ids ) > 0:
            raise RuntimeError( "Duplicate art ID: {:s}.".format( ", ".join( map( str, duplicate_art_ids ) ) ) )

        if len( orphaned_art_ids ) > 0:
            raise RuntimeError( "Orphaned art records: {:s}.".format( ", ".join( map( str, orphaned_art_ids ) ) ) )

    # read the XML file as a giant string and then convert its DOM into
    # something we can work with.
    with open( filename, "rt" ) as xml_file:
        xml_string = xml_file.read()
    root_node = etree.fromstring( xml_string )

    if len( root_node ) != 3:
        raise RuntimeError( "Expected 3 elements within the document, but received {:d}.".format( len( root_node ) ) )

    # parse the fields, and our photos and art records.
    if root_node[0].tag != "Fields":
        raise RuntimeError( "" )
    fields = parse_fields_node( root_node[0] )

    if root_node[1].tag != "Photos":
        raise RuntimeError( "" )
    photos = parse_photos_node( root_node[1] )

    if root_node[2].tag != "Arts":
        raise RuntimeError( "" )
    art = parse_arts_node( root_node[2] )

    # validate what we received so we don't pass garbage back to the user.
    validate_art_fields( fields[0], fields[1] )
    validate_identifiers( photos, art )

    # XXX: rework the interface here
    return (fields[0], fields[1], photos, art)

def _read_memory_database( ):
    """
    Constructs a test database from internal structures.

    Takes no arguments.

    Returns 4 values:

      art_fields        - Dictionary containing various database field values
                          associated with art records.  Each key's value is
                          a list of strings.
      processing_states - List of values representing the states records may
                          be in.
      photo_records     - A list of photo objects, one per record in the
                          database.
      art_records       - A list of art objects, one per record in the
                          database.

    """

    art_types     = ["tag", "throwup", "wild_style", "mural", "sticker", "text", "other"]
    art_sizes     = ["tiny", "small", "medium", "large", "huge"]
    art_qualities = ["bad", "poor", "fair", "good", "excellent"]

    artists = ["Amoz", "Badu", "Daru", "Drip", "EWO", "Fuck", "HBD",
               "Kolm", "Omar", "PBR", "Rulof", "TV", "Unknown", "Zebra"]

    processing_states = ["needs_review", "reviewed", "unreviewed"]

    photos = [PhotoRecord( 1, "images/P9400741.JPG", (4112, 3884), "reviewed", (0,0), 0, 1468507707, 1468507707, [] ),
              PhotoRecord( 2, "images/P9400919.JPG", (4112, 3884), "reviewed", (0,0), 0, 1468507608, 1468507608, [] ),
              PhotoRecord( 3, "images/P9410159.JPG", (4112, 3884), "reviewed", (0,0), 0, 1468507668, 1468507668, [] ),
              PhotoRecord( 4, "images/P9430585.JPG", (4112, 3884), "reviewed", (0,0), 0, 1468507638, 1468507638, [] ),
              PhotoRecord( 5, "images/P9440028.JPG", (4112, 3884), "unreviewed", (0,0), 0, 1468507546, 1468507546, [] ),
              PhotoRecord( 6, "images/P9470260.JPG", (4112, 3884), "needs_review", (0,0), 0, 1468507567, 1468507567, [] )]
    art    = [ArtRecord( 1, 1, "throwup", ["Daru"],    [], "large", "good", [], 1234, 1234, None, "reviewed", (0.2, 0.13924050632911392, 0.7142857142857143, 0.3291139240506329) ),
              ArtRecord( 2, 1, "throwup", ["Amoz"],    [], "large", "fair", [], 1234, 1234, None, "reviewed", (0.24952380952380954, 0.41012658227848103, 0.3219047619047619, 0.3012658227848101) ),
              ArtRecord( 3, 1, "throwup", ["EWO"],     [], "large", "fair", [], 1234, 1234, None, "reviewed", (0.5619047619047619, 0.3569620253164557, 0.42857142857142855, 0.3367088607594937) ),
              ArtRecord( 4, 1, "throwup", ["Unknown"], [], "large", "poor", [], 1234, 1234, None, "reviewed", (0.015238095238095238, 0.4, 0.26476190476190475, 0.29873417721518986) ),

              ArtRecord( 5, 2, "wild_style", ["Fuck"], [], "huge", "excellent", [], 1234, 1234, "2016", "reviewed", (0.02857142857142857, 0.31645569620253167, 0.9352380952380952, 0.37721518987341773) ),

              ArtRecord( 6, 3, "throwup", ["Badu"], ["PBR", "Zebra"], "large", "excellent", [], 1234, 1234, "2016", "reviewed", (0.0419047619047619, 0.002531645569620253, 0.8819047619047619, 0.9772151898734177) ),
              ArtRecord( 7, 3, "tag",     ["Badu"], [],               "small", "good", [], 1234, 1234, None, "reviewed", (0.878095238095238, 0.6177215189873417, 0.10857142857142857, 0.10886075949367088) ),
              ArtRecord( 8, 3, "tag",     ["Badu"], [],               "small", "good", [], 1234, 1234, None, "reviewed", (0.8838095238095238, 0.1189873417721519, 0.10857142857142857, 0.10126582278481013) ),

              ArtRecord( 9, 4,  "throwup", ["PBR"], ["PBR", "Drip"], "small", "good", [], 1234, 1234, None, "reviewed", (0.0019047619047619048, 0.22025316455696203, 0.9447619047619048, 0.5569620253164557) ),
              ArtRecord( 10, 4, "tag",     ["Drip"],             [], "small", "fair", [], 1234, 1234, None, "reviewed", (0.7695238095238095, 0.5341772151898734, 0.12761904761904763, 0.10126582278481013) ),
              ArtRecord( 11, 4, "tag",     ["MR", "Unknown"],    [], "small", "fair", [], 1234, 1234, None, "needs_review", (0.7847619047619048, 0.6481012658227848, 0.09523809523809523, 0.1620253164556962) ),

              ArtRecord( 12, 5, "wild_style", ["Unknown"], ["Rulof"], "huge", "good", [], 1234, 1234, None, "needs_review", (0.0019047619047619048, 0.2481012658227848, 1.0, 0.47341772151898737) ),

              ArtRecord( 13, 6, "mural", ["HBD"], ["Omar"], "large", "fair", [], 1234, 1234, "2014/11/21", "reviewed", (0.08, 0.3189873417721519, 0.4247619047619048, 0.4253164556962025) ),
              ArtRecord( 14, 6, "text",  ["HBD"], [],       "small", "good", [], 1234, 1234, "2014/11/21", "reviewed", (0.4, 0.3240506329113924, 0.4266666666666667, 0.379746835443038) )]

    return ({ "types":     art_types,
              "sizes":     art_sizes,
              "qualities": art_qualities,
              "artists":   artists },
            processing_states,
            photos,
            art)

class Record( object ):
    """
    Provides a dictionary-like interface with a fixed set of keys, some
    mutable, that may be accessed after creation.
    """

    def __init__( self, keys, mutable_keys, **kwargs ):
        """
        Constructs a Record from the supplied list of keys and values.

        Takes 3 arguments:

          keys         - A list of key names whose values are read-only within
                         the Record.  Each item must be hashable.
          mutable_keys - A list of key names whose values are read-write within
                         the Record.  Each item must be hashable.
          kwargs       - Keyword arguments containing the key/value pairs to
                         initialize the Record with.  Must contain all of the
                         entries in keys, though does not have to contain any
                         of the entries in mutable_keys.

        Returns 1 value:

          self - The newly created Record object.

        """

        self._info         = {}
        self._keys         = keys
        self._mutable_keys = mutable_keys

        # initialize the record.
        for key, value in kwargs.items():
            if not key in self._keys:
                raise KeyError( "{:s} is not a valid key!".format( key ) )
            self._info[key] = value

        # ensure that all immutable keys have values associated with them.
        for key in self._keys:
            if not key in self._info:
                raise KeyError( "{:s} must be initialized with a value!".format( key ) )

    def __getitem__( self, key ):
        """
        Retrieves the value for an key within the Record.

        Takes 1 argument:

          key - The key whose value is requested.

        Returns 1 value:

          value - The value associated with key.

        """

        return self._info[key]

    def __setitem__( self, key, value ):
        """
        Sets the value for an key within the Record.  If the supplied key is
        not mutable, a KeyError is raised.

        Takes 2 arguments:

          key   - The key whose value will be set.
          value - The value to set.

        Returns nothing.

        """

        if not key in self._mutable_keys:
            raise KeyError( "{:s} is not a mutable key!".format( key ) )

        self._info[key] = value

class ArtRecord( Record ):
    """
    Database record representing a piece of art associated with a PhotoRecord.
    The following keys are available (mutable keys are marked with *):

      *artists        Non-empty list of artist names.
      *associates     List, possibly empty, of artists who are associated with
                      the work.
      created_time    Fractional seconds since Epoch when the record was created.
      *date           Four digit year when the art was created.
      id              Unique, positive integer identifier for the art.
      *modified_time  Fractional seconds since Epoch when the record was last
                      updated.
      photo_id        Unique, positive integer identifier for the photo the art
                      was documented in.
      *quality        String representing the art's physical quality/state.
      *region         Geometry tuple containing (x, y, width, height) values
                      normalized to the parent photo's resolution.
      *size           String representing the art's physical size.
      *state          String representing the processing state the record is
                      in.
      *type           String specifying the type of the art.
      *vandals        List, possibly empty, of artists who have vandalized the
                      art.

    """

    def __init__( self, id, photo_id, type, artists=["Unknown"], associates=[], size="medium", quality="fair", vandals=[], created_time=None, modified_time=None, date=None, state=None, region=None ):
        """
        Constructs an ArtRecord object from the supplied parameters.

        Takes 13 arguments:

          id            - Identifier for the art record.  Must be a positive
                          integer, different from other record identifiers.
          photo_id      - Identifier for the parent PhotoRecord.  Must be a
                          positive integer.
          type          - String specifying the type.
          artists       - Optional, non-empty list of strings specifying the
                          creators of the art.  If omitted, defaults to
                          ["Unknown"].
          associates    - Optional, possibly empty, list of strings specifying
                          associates of the creators of the art.  If omitted,
                          defaults to an empty list.
          size          - Optional string specifying the size of the art.  If
                          omitted, defaults to "medium".
          quality       - Optional string specifying the physical quality of
                          the art.  If omitted, defaults to "fair".
          vandals       - Optional, possibly empty, list of strings specifying
                          vandals of the art.  If omitted, defaults to an empty
                          list.
          created_time  - Optional fractional seconds since the Epoch
                          indicating when the art record (not the physical
                          art) was created.  If omitted, defaults to the current
                          time.
          modified_time - Optional fractional seconds since the Epoch
                          indicating when the art record (not the physical
                          art) was last modified.  If omitted, defaults to the current
                          time.
          date          - Optional year, as a four digit integer, indicating when the
                          physical art was created.  If omitted, defaults to None.
          state         - Optional string specifying the processing state of the
                          record.  If omitted, defaults to "unreviewed".
          region        - Optional tuple of (x, y, width, height) values, normalized
                          to the parent PhotoRecord's resolution, representing the
                          art's presence within the photograph.  If omitted, defaults
                          to None.

        Returns 1 value:

          self - The newly created ArtRecord object.

        """

        if state is None:
            state = "unreviewed"

        if created_time is None:
            created_time = time.mktime( time.gmtime() )

        if modified_time is None:
            modified_time = created_time

        _readable_keys = ["artists", "associates", "created_time", "date",
                          "id", "modified_time", "photo_id", "quality",
                          "region", "size", "state", "type", "vandals"]
        _mutable_keys = ["artists", "associates", "date", "modified_time",
                         "quality", "region", "size", "state", "type",
                         "vandals"]

        # XXX: validation of type, artists (must not be empty), associates,
        #      size, quality, vandals, and state
        # XXX: higher level validation of id and photo_id

        super().__init__( _readable_keys,
                          _mutable_keys,
                          artists=artists,
                          associates=associates,
                          created_time=created_time,
                          date=date,
                          id=id,
                          modified_time=modified_time,
                          photo_id=photo_id,
                          quality=quality,
                          region=region,
                          size=size,
                          state=state,
                          type=type,
                          vandals=vandals )

class PhotoRecord( Record ):
    """
    Database record documenting one or more pieces of street art.  The
    following keys are available (mutable keys are marked with *):

      created_time   Fractional seconds since Epoch when the record was
                     created.
      *filename      Path to the photograph file on disk.
      id             Unique, positive integer identifier for the phtograph.
      location       Tuple of fractional (latitude, longitude) with positive
                     being north and east, and negative being south and west.
      modified_time  Fractional seconds since Epoch when the record was
                     last updated.
      resolution     Tuple of positive integers specifying the (width, height)
                     of the photograph.
      rotation       XXX
      *state         String representing the processing state the record is
                     in.
      *tags          List, possibly empty, of strings describing the
                     photograph.

    XXX: constants here need to be consistent but different than the database
    """

    def __init__( self, id, filename, resolution, state=None, location=None, rotation=0, created_time=None, modified_time=None, tags=None ):
        """
        Constructs an PhotoRecord object from the supplied parameters.

        Takes 9 arguments:

          id            - Identifier for the photo record.  Must be a positive
                          integer, different from other record identifiers.
          filename      - Path to the photograph file on disk.
          resolution    - Tuple of positive integers specifying the (width, height)
                          of the photograph.
          state         - Optional string specifying the processing state of the
                          record.  If omitted, defaults to "unreviewed".
          location      - Tuple of fractional (latitude, longitude) with positive
                          being north and east, and negative being south and west.
          rotation      - Optional degrees of rotation needed to apply to the
                          photograph for display purposes.  If omitted, defaults
                          to zero.
          created_time  - Optional fractional seconds since the Epoch
                          indicating when the photo record (not the
                          photograph) was created.  If omitted, defaults to
                          the current time.
          modified_time - Optional fractional seconds since the Epoch
                          indicating when the art record (not the photograph)
                          was last modified.  If omitted, defaults to the
                          current time.
          tags          - Optional, possibly empty, list of strings specifying
                          tas associated with the photograph.  If omitted,
                          defaults to an empty list.

        Returns 1 value:

          self - The newly created PhotoRecord object.

        """

        if state is None:
            state = "unreviewed"

        if created_time is None:
            created_time = time.mktime( time.gmtime() )

        if modified_time is None:
            modified_time = created_time

        # XXX: should these lists be somewhere else?
        _readable_keys = ["created_time", "filename", "id", "location",
                          "modified_time", "resolution", "rotation", "state", "tags"]
        _mutable_keys   = ["filename", "modified_time", "state", "tags"]

        resolution = (4112, 3884)
        tags       = []

        super().__init__( _readable_keys,
                          _mutable_keys,
                          created_time=created_time,
                          filename=filename,
                          id=id,
                          location=location,
                          modified_time=modified_time,
                          resolution=resolution,
                          rotation=rotation,
                          state=state,
                          tags=tags )

class Database( object ):
    """
    Represents a database of photo and art records for analyzing street art.
    """

    def __init__( self, filename=None ):
        """
        Initializes a Database object from the contents of the supplied file.
        Commiting changes to the object will update the file supplied.  If no
        file is supplied, a test database is constructed.

        Takes 1 argument:

          filename - File name backing the database.  If omitted, a test
                     database is constructed and changes will not be
                     commited anywhere when save_database() is called.

        Returns 1 value:

          database - The Database object.

        """

        self.filename = filename

        self.load_database()

    def load_database( self ):
        """
        Populates the database object from the backing store.  Uncommited
        changes to the database are lost.

        Takes no arguments.

        Returns nothing.
        """

        # figure out where our backing store is.
        if self.filename is None:
            filename  = "memory"
            read_func = _read_memory_database
        else:
            filename  = self.filename
            read_func = _read_xml_database

        # load the database.
        self.art_fields, self.processing_states, self.photos, self.arts = read_func( filename )

    def save_database( self, filename=None ):
        """
        Commits changes to the database to the supplied backing store.

        Takes 1 argument:

          filename - Optional path to the on-disk file to commit changes to.
                     If omitted, defaults to the file name supplied during
                     the Database object's initialization.

        Returns nothing.
        """

        # XXX: hack to prevent corruption of our test DB during development.
        filename = None

        if filename is None:
            if self.filename is None:
                filename = "memory"
            else:
                filename = self.filename

        if filename == "memory":
            print( "XXX: Writing out database to {:s}.".format( filename ) )

            return 0
        else:
            return _write_xml_database( filename )

    def get_photo_records( self, photo_ids=None ):
        """
        Retrieves all of the PhotoRecord's in the database matching the
        supplied identifiers.

        Takes 1 argument:

          photo_ids - List of photo identifiers whose PhotoRecords are needed.
                      If specified as None, all PhotoRecords in the database
                      are requested.

        Returns 1 value:

          requested_photos - A list of PhotoRecord's matching the requested
                             identifiers.  If only a single identifier was requested
                             then requested_photos will be scalar instead of a list
                             as a convenience.

        """

        if photo_ids is None:
            return self.photos
        elif type( photo_ids ) != list:
            photo_ids = [photo_ids]

        requested_photos = [photo for photo in self.photos if photo["id"] in photo_ids]

        # help the user and return a scalar if they requested a single record.
        #
        # NOTE: this assumes that the identifiers are unique and can't return
        #       multiple records...
        #
        if len( photo_ids ) == 1 and len( requested_photos ) > 0:
            requested_photos = requested_photos[0]

        return requested_photos

    def get_art_records( self, photo_ids=None ):
        """
        Retrieves all of the ArtRecord's in the database associated with the
        supplied PhotoRecords identifiers.

        Takes 1 argument:

          photo_ids - List of photo identifiers whose associated ArtRecords
                      are needed.  If specified as None, all ArtRecords in
                      the database are requested.

        Returns 1 value:

          requested_art - A list of ArtRecord's matching the requested
                          identifiers.

        """

        #
        # NOTE: this interface isn't the most flexible though was designed to
        #       directly support the following use cases:
        #
        #         * art records associated with a particular photo
        #         * arbitrary art records (no use case through the OMI)
        #         * all art records
        #

        if photo_ids is None:
            return self.arts
        elif type( photo_ids ) != list:
            photo_ids = [photo_ids]

        return [art for art in self.arts if art["photo_id"] in photo_ids]

    def new_art_record( self, photo_id ):
        """
        Creates a new art record initialized with default values. XXX

        Takes 1 argument:

          photo_id - XXX

        Returns 1 value:

          art_record - XXX

        """

        # compute a unique index that hasn't been used yet.
        art_id = max( [art["id"] for art in self.arts] ) + 1

        # XXX: hardcoded constant
        self.arts.append( ArtRecord( art_id, photo_id, "throwup" ) )

        return self.arts[-1]

    def delete_art_record( self, art_id ):
        """
        XXX
        """

        # filter our the records that match the supplied identifier.
        self.arts = [art for art in self.arts if art["id"] != art_id]

    def get_artists( self ):
        """
        Gets a list of artists known by the database.

        Takes no arguments.

        Returns 1 value:

          artists - List of artist names.

        """

        return self.art_fields["artists"]

    def get_art_types( self ):
        """
        Gets a list of the art types known by the database.

        Takes no arguments.

        Returns 1 value:

          art_types - List of art types.

        """

        return self.art_fields["types"]

    def get_art_sizes( self ):
        """
        Gets a list of art sizes known by the database.

        Takes no arguments.

        Returns 1 value:

          art_sizes - List of art sizes.

        """

        return self.art_fields["sizes"]

    def get_art_qualities( self ):
        """
        Gets a list of art qualities known by the database.

        Takes no arguments.

        Returns 1 value:

          art_qualities - List of art qualities.

        """

        return self.art_fields["qualities"]

    def get_processing_states( self ):
        """
        Gets a list of processing states known by the database.

        Takes no arguments.

        Returns 1 value:

          processing_states - List of processing states.

        """

        return self.processing_states
