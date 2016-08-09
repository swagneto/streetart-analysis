import os
import time

import folium
import numpy as np

def get_track_bounds( track_coordinates ):
    """
    Computes a bounding box for the supplied track.  The upper left and lower
    right corners of the track's bounding box are returned to the caller.

    Takes 1 argument:

      track_coordinates - A Numpy array, Nx2, whose columns are latitudes and
                          longitudes, respectively.

    Returns 1 value:

      track_bounds = A list of two pairs - the upper left and lower right
                     (latitude, longitude)'s.

    """

    # compute the extrema across the track's points.
    lower_bounds = np.min( track_coordinates, axis=0 )
    upper_bounds = np.max( track_coordinates, axis=0 )

    return [tuple( lower_bounds ), tuple( upper_bounds )]

def get_api_key( map_type ):
    """
    Gets a secret key for a map interface by type and returns it as a string.
    Raises RuntimeException() for unknown map types.

    Currently the following map types are supported:

      mapbox - API key for MapBox.

    Takes 1 argument:

      map_type - String specifying the API whose key is requested.  See above
                 for supported APIs.

    Returns 1 value:

      api_key - API key string.

    """

    map_type = map_type.lower().strip()

    if map_type == "mapbox":
        file_name = "mapbox-api-key.txt"
    else:
        raise RuntimeException( "Unknown map type requested ({}).".format( map_type ) )

    with open( file_name ) as f:
        api_key = f.read()

    return api_key

def get_folium_map( map_center, dimensions=None, zoom_level=12, use_simple_tiles=True, use_mapbox_tiles=False ):
    """
    Creates a Folium map with a simplified interface.  The initial location,
    zoom level, and base layers can be configured without having to know the
    vagaries of the available layers.

    Takes 4 arguments:

      map_center       - Tuple of (latitude, longitude), in fractional degrees,
                         specifying the the center of the map.
      dimensions       - Optional tuple specifying the width and height of the
                         map.  If omitted, the map's size is set by Folium.
      zoom_level       - Optional integral level of detail for the initial
                         map view.  Must be in the range of [1, 16] and defaults
                         to 12 if omitted.
      use_simple_tiles - Optional boolean flag specifying whether only the simple
                         OpenStreetMap layer should be added to the default layers.
                         If False, a number of free layers are added.  If omitted,
                         defaults to True.
      use_mapbox_tiles - Optional boolean flag specifying whether MapBox layers
                         should be added.  If omitted, defaults to False.

                         NOTE: This requires a MapBox account and a suitably
                               configured API key available on disk.  See
                               get_api_key() for more information.

    Returns 1 value:

      fmap - The created Folium map.

    """

    dimensions_dict = {}
    if dimensions is not None:
        dimensions_dict["width"]  = dimensions[0]
        dimensions_dict["height"] = dimensions[1]

    folium_map = folium.Map( location=list( map_center ),
                             detect_retina=True,
                             control_scale=True,
                             zoom_start=zoom_level,
                             tiles=None,
                             **dimensions_dict )

    # NOTE: the Mapbox layers should have the following as their attribution, though
    #       Folium seems to trip up over the embedded HTML.
    #
    #       Map data © <a href='http://openstreetmap.org'>OpenStreetMap</a>contributors,
    #       Imagery © <a href='http://mapbox.com'>MapBox</a>
    #
    esri_layers = [["ESRI Imagery",        { "url":         "http://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/MapServer/tile/{z}/{y}/{x}",
                                              "attribution": "Data by Esri from various sources" }],
                   ["ESRI Topography",     { "url":         "http://services.arcgisonline.com/arcgis/rest/services/World_Topo_Map/MapServer/MapServer/tile/{z}/{y}/{x}",
                                              "attribution": "Data by Esri from various sources" }]]

    if use_mapbox_tiles:
        mapbox_api_key = get_api_key( "mapbox" )
        mapbox_layers =[["Mapbox - Dark",       { "url":         "https://api.mapbox.com/styles/v1/mapbox/dark-v9/tiles/{z}/{x}/{y}?access_token=" + mapbox_api_key,
                                                  "attribution": "Map data © OpenStreetMap contributors, Imagery © MapBox"}],
                        ["Mapbox - Light",      { "url":         "https://api.mapbox.com/styles/v1/mapbox/light-v9/tiles/{z}/{x}/{y}?access_token=" + mapbox_api_key,
                                                  "attribution": "Map data © OpenStreetMap contributors, Imagery © MapBox"}],
                        ["Mapbox - Outdoors",   { "url":         "https://api.mapbox.com/styles/v1/mapbox/outdoors-v9/tiles/{z}/{x}/{y}?access_token=" + mapbox_api_key,
                                                  "attribution": "Map data © OpenStreetMap contributors, Imagery © MapBox"}],
                        ["Mapbox - Streets",    { "url":         "https://api.mapbox.com/styles/v1/mapbox/streets-v9/tiles/{z}/{x}/{y}?access_token=" + mapbox_api_key,
                                                  "attribution": "Map data © OpenStreetMap contributors, Imagery © MapBox"}],
                        ["Mapbox - Satellite",  { "url":         "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/{z}/{x}/{y}?access_token=" + mapbox_api_key,
                                                  "attribution": "Map data © OpenStreetMap contributors, Imagery © MapBox"}],
                        ["Mapbox - Hybrid",     { "url":         "https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v9/tiles/{z}/{x}/{y}?access_token=" + mapbox_api_key,
                                                  "attribution": "Map data © OpenStreetMap contributors, Imagery © MapBox"}]]

    folium_layers = [("MapQuest Open",        "mapquest open"),
                     ("MapQuest Open Aerial", "mapquest open aerial"),
                     ("Stamen - Terrain",     "stamen terrain"),
                     ("Stamen - Toner",       "stamen toner"),
                     ("Stamen - Watercolor",  "stamen watercolor"),
                     ("CartoDB - Positron",   "cartodb positron"),
                     ("CartoDB - Dark Mater", "cartodb dark_matter"),
                     ("OpenStreetMap",        "openstreetmap")]

    layers_to_add = esri_layers

    if use_mapbox_tiles:
        layers_to_add = mapbox_layers + layers_to_add

    # walk through each additional ESRI layer and add it.  the layer control
    # lists them in the order they're added and leaves the last one selected.
    for layer in layers_to_add:
        layer_name       = layer[0]
        layer_attributes = layer[1]

        folium_map.add_tile_layer( name=layer_name,
                                   tiles=layer_attributes["url"],
                                   attr=layer_attributes["attribution"] )

    # add all of the Folium tiles if we're not making a simple map.
    if not use_simple_tiles:
        for layer in folium_layers:
            layer_name = layer[0]
            tile_name  = layer[1]

            folium_map.add_tile_layer( name=layer_name,
                                       tiles=tile_name )
    else:
        folium_map.add_tile_layer( name=folium_layers[-1][0],
                                   tiles=folium_layers[-1][0] )

    return folium_map

def create_photo_markers( photo_df, group, popup_html=None, popup_dimensions=None, marker_properties=None ):
    """
    Creates Folium markers for each of the photos in the supplied DataFrame.
    All markers are added into a supplied folium.FeatureGroup or into a newly
    created one if a name is supplied instead.  The caller has full control
    over each marker's popup by supplying a HTML template that is instantiated
    from the supplied DataFrame's contents.  Control over the markers
    appearance is available as well.

    The popup's template will have the following keyword parameters substituted
    during instantiation:

      image_height    - Integer specifying the photo's thumbnail's height,
                        in pixels.
      image_width     - Integer specifying the photo's thumbnail's width,
                        in pixels.
      latitude        - Latitude of the photo's location, in fractional
                        degrees.
      latitude_ref    - "N" or "S" if the photo was taken in the northern or
                        southern hemisphere, respectively.
      longitude       - Longitude of the photo's location, in fractional
                        degrees.
      longitude_ref   - "E" or "W" if the photo was taken in the eastern or
                        western hemisphere, respectively.
      photo_filename  - Path to the file name, as found in the DataFrame.
      photo_id        - Integer PhotoRecord identifier.
      tag             - Comma delimited string of any tags associated with
                        the photo.
      url             - URI to the photo that is derived from photo_filename.

                        NOTE: This is normalized path on the local system
                              and is *NOT* suitable for use with a web server.

    The marker_properties dictionary must contain the following keys:

      color        - The marker's border color.  String suitable for use with
                     folium.CircleMarker().
      fill_color   - The marker's interior color.  String suitable for use with
                     folium.CircleMarker().
      fill_opacity - The marker's opacity value in the range of [0.0, 1.0].
      radius       - The marker's radius.  Must be positive.

    Takes 5 arguments:

      photo_df          - DataFrame for the photos to create markers for.
      group             - Name of the FeatureGroup to create, or an existing
                          FeatureGroup, to add markers into.
      popup_html        - Optional HTML template to use for markers created.
                          If omitted, defaults to a simple popup that shows
                          a clickable thumbnail of the photo and basic vitals
                          of its record.
      popup_dimensions  - Optional pair tuple specifying the size of each
                          marker's popup.  If omitted, it is sized according
                          to the default popup_html.
      marker_properties - Optional dictionary whose contents govern created
                          marker's properties.  See above for details.

    Returns 1 value:

      group - The FeatureGroup populated with created markers.

    """

    # default to a simple, small marker that provides contrast against many
    # base layers.
    if marker_properties is None:
        marker_properties = { "color":        "purple",
                              "fill_color":   "purple",
                              "fill_opacity": 1.0,
                              "radius":       1.0 }

    if popup_dimensions is None:
        # XXX: these defaults are weird.
        popup_dimensions = (325, 285)

    # use a default popup if the caller did not provide one.
    if popup_html is None:
        popup_html = """
<link rel="stylesheet" type="text/css" href="//fonts.googleapis.com/css?family=Open+Sans" />

<style>
   .waypoint-marker
   {{
       font-family: "Open Sans", "Times New Roman", Georgia, Serif;
       font-size:   9pt;
    }}
</style>

<div class="photo-marker">
    <table>
        <tbody>
            <tr>
                <td>Photo:</td>
                <td><a href="{url:s}"> <img src="{url:s}" height="{image_height:d}" width="{image_width:d}"/> </a> </td>
            </tr>
            <tr>
                <td>File name:</td>
                <td>{photo_filename:s} ({photo_id:d})</td>
            </tr>
            <tr>
                <td>Time:</td>
                <td>{time:s}</td>
            </tr>
            <tr>
                <td>Location:</td>
                <td>({latitude:8.5f}{latitude_ref:s}, {longitude:9.5f}{longitude_ref:s})</td>
            </tr>
            <tr>
                <td>Tags:</td>
                <td>{tags:s}</td>
            </tr>
        </tbody>
    </table>
</div>
"""

    # create a new feature group with the supplied name if we weren't handed a
    # feature group to append to.
    if type( group ) != folium.FeatureGroup:
        group = folium.FeatureGroup( name=group )

    # walk through each of the rows in this DataFrame and populate our
    # dictionary that provides values to the popup template.
    #
    # XXX: do we want to handle duplicate photo records?  as is they add bloat
    #      though they cause the opacity to stack and become opaque when many
    #      markers are created for the same record.
    #
    for photo_index in photo_df.index:
        photo_series = photo_df.loc[photo_index]

        kwargs = dict()
        kwargs["photo_filename"] = photo_series["filename"]

        # XXX: this assumes we're doing local development.  this needs to be
        #      fixed later.
        kwargs["url"]            = "file://{:s}{:s}{:s}".format( os.path.realpath( os.path.curdir ),
                                                                 os.path.sep,
                                                                 photo_series["filename"] )
        kwargs["image_width"]    = 160
        kwargs["image_height"]   = 120
        kwargs["photo_id"]       = photo_series.name
        kwargs["time"]           = "{:s} [{:d}]".format( time.strftime( "%Y/%m/%d %H:%M:%S",
                                                                        time.gmtime( photo_series["photo_time"] ) ),
                                                         int( photo_series["photo_time"] ) )
        kwargs["latitude"]       = photo_series["location"][0]
        kwargs["longitude"]      = photo_series["location"][1]
        kwargs["latitude_ref"]   = "N" if kwargs["latitude"] >= 0 else "S"
        kwargs["longitude_ref"]  = "E" if kwargs["longitude"] >= 0 else "W"
        kwargs["tags"]           = ", ".join( photo_series["tags"] )

        # instantiate the popup's template and create an IFrame to hold it.
        iframe_html = popup_html.format( **kwargs )
        iframe      = folium.element.IFrame( html=iframe_html,
                                             width=popup_dimensions[0],
                                             height=popup_dimensions[1] )

        # create a marker and the popup that occurs when it is clicked.
        #
        # XXX: is the popup's max_width what we want?
        #
        popup  = folium.Popup( iframe, max_width=popup_dimensions[0] )
        marker = folium.CircleMarker( location=photo_series["location"],
                                      popup=popup,
                                      **marker_properties )

        group.add_child( marker )

    return group
