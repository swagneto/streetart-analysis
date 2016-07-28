from PyQt5.QtCore import Qt, QSize, QRectF
from PyQt5.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import ( QHBoxLayout, QLabel, QRubberBand, QSizeGrip,
                              QWidget )

class ResizingPixmap( QLabel ):
    """
    Widget that displays an image as a QLabel that responds to resize events
    while maintaining the original image's aspect ratio.
    """

    def __init__( self, filename, resolution=None, minimum_resolution=None ):
        """
        Builds a ResizingPixmap from the supplied filename.  The initial size
        and minimum size may also be set.

        Takes 3 arguments:

          filename           - Path to the image to display.
          resolution         - Optional pair of positive integers specifying
                               the initial size of the widget.  If omitted,
                               defaults to (400, 300).
          minimum_resolution - Optional pair of positive integers specifying
                               the smallest size of the widget.  If omitted,
                               defaults to (1, 1).

        Returns 1 value:

          self - The newly created ResizingPixmap object.
        """

        if minimum_resolution is None:
            minimum_resolution = (1, 1)

        if resolution is None:
            # XXX: the default should be derived from the original image's
            #      aspect ratio...
            resolution = (400, 300)

        super().__init__()

        # note that we store the pixmap so that resized versions can be
        # created whenever our widget is resized.
        self.loaded_pixmap = QPixmap.fromImage( QImage( filename ) )
        self.setPixmap( self.loaded_pixmap.scaled( *resolution, Qt.KeepAspectRatio ) )

        # set a lower bound for the pixmap's size so that we can resize it
        # smaller than it is initially displayed.  otherwise we'll only be
        # able to grow the size.
        self.setMinimumSize( *minimum_resolution )

    def resizeEvent( self, event ):
        """
        Resizes the pixmap to the containing widget's new size while
        maintaining the original aspect ratio.

        Takes 1 argument:

          event - QResizeEvent object.

        Returns nothing.
        """

        self.setPixmap( self.loaded_pixmap.scaled( self.size(), Qt.KeepAspectRatio ) )
        super().resizeEvent( event )

class RubberBandedWidget( QWidget ):
    """
    Adds an interactive rubberband box to a widget.

    A new transparent widget is added as a child of a supplied widget which
    holds the machinery needed for an interactive rubberband.  This includes
    a pair of QSizeGrip's that represent the top-left/bottom-right corners of
    the transparent widget and a rubberband box that outlines the transprent
    widget's extent.

    NOTE: The minimum size the rubberband box can be is ~37x37 pixels
          (possibly smaller in one dimension as that wasn't tested, though
          possibly larger due to issues I dont't understand), otherwise
          the size grips go wonky (overlap?) and prevent resizing beyond
          the initial size.  Due to my basic knowledge of Qt, setting the
          rubberbands size and minimum size cannot be done in the
          constructor as that causes problems on my Linux system (Ubuntu
          14.04 under XFCE) in the form of the bottom/right edges of the
          rubberband box not being rendered and not being able to drag the
          grips down.

    """

    # Original code and idea came from here:
    #
    #   https://stackoverflow.com/questions/19066804/implementing-resize-handles-on-qrubberband-is-qsizegrip-relevant
    #
    # With a full project here:
    #
    #   https://gist.github.com/Riateche/6743108
    #

    # minimum box size where a pair of QSizeGrips work.  anything smaller will
    # cause problems (because they overlap?) so we prevent resizing below this
    # value.
    minimum_size = 37

    def __init__( self, parent ):
        """
        Builds a RubberBandedWidget as a child of the supplied parent.  The
        constructed widget is invisible though occupies the same space as
        the parent widget.
        """

        # run our parent class' constructor and pass our parent widget to it.
        super().__init__( parent )

        # ensure that our size grips only control the rubberband and not the
        # widget that we're operating on.
        self.setWindowFlags( Qt.SubWindow )

        # create a new layout that spans the entirety of the widget without
        # any margin padding.
        layout = QHBoxLayout( self )
        layout.setContentsMargins( 0, 0, 0, 0 )

        # add two size grips into the layout that position themselves at the
        # top-left and bottom-right of the widget.
        #
        # XXX: I *think* this is how it works.  that said, I've only had a week
        #      of Qt experience under my belt at this point.
        #
        layout.addWidget( QSizeGrip( self ), 0, Qt.AlignLeft | Qt.AlignTop )
        layout.addWidget( QSizeGrip( self ), 0, Qt.AlignRight | Qt.AlignBottom )

        # create a rubberband parented to our widget and position it in the upper
        # left corner of it.
        self.rubberband = QRubberBand( QRubberBand.Rectangle, self )

        # constrains the minimum size set to be no smaller than the class
        # minimum so that the rubberband box is always usable.  this prevents
        # the QSizeGrip widgets from becoming wonky and refusing to drag in
        # both dimensions they're configured rather than just one.
        #
        # NOTE: we need to do this before we interact with the rubberband
        #       otherwise we run into issues where the widgets and layout
        #       aren't in sync.
        #
        self.setMinimumSize( RubberBandedWidget.minimum_size,
                             RubberBandedWidget.minimum_size )

        # make our rubberband visible in the corner of the widget.
        self.rubberband.move( 0, 0 )
        self.rubberband.show()

    def resizeEvent( self, event ):
        """
        Resizes the transparent widget's rubberband box whenever the widget
        itself is resized (via the QSizeGrip's).

        Takes 1 argument:

          event - QResizeEvent object.

        Returns nothing.
        """

        # resize the rubber band whenever our proxy widget with the grips is
        # resized.
        self.rubberband.resize( self.size() )

class RubberBandedPixmap( QLabel ):
    """
    Widget that displays an image as a QLabel that respects resizing and provides
    a rubberband region on it.
    """

    # XXX: this could be improved by modifying the transparent QWidget so that
    #      it is transparent and responsed to single clicks to move the banded
    #      region around.

    def __init__( self, filename, resolution=None ):
        """
        Builds a RubberBandedPixmap from the supplied filename.  The
        initial size and minimum size may also be set.

        Takes 4 arguments:

          filename   - Path to the image to display.
          resolution - Optional pair of positive integers specifying
                       the initial size of the widget.  If omitted,
                       defaults to (400, 300).

        Returns 1 value:

          self - The newly created RubberBandedResizingPixmap object.
        """

        super().__init__()

        if resolution is None:
            resolution = (400, 300)

        # note that we store the pixmap so that resized versions can be
        # created whenever our widget is resized.
        self.loaded_pixmap = QPixmap.fromImage( QImage( filename ) )
        self.setPixmap( self.loaded_pixmap.scaled( *resolution, Qt.KeepAspectRatio ) )

        # add a banded region to ourselves.  track it so we can move it around
        # programmatically.
        self.banded_region = RubberBandedWidget( self )

    def mouseDoubleClickEvent( self, event ):
        """
        Resizes and moves the banded region to where the double click occurred.

        Takes 1 argument:

          event - QMouseEvent object.

        Returns nothing.
        """

        # move to the click and reset the region to the smallest possible
        # size.
        self.banded_region.move( event.x(), event.y() )
        self.banded_region.resize( 1, 1 )

    def get_region_geometry( self, normalized_flag=False ):
        """
        Returns the banded region's geometry.  The geometry may be normalized
        relative to the associated pixmap's size so that it may be used with
        scaled versions of the pixmap.

        Takes 1 argument:

          normalized_flag - Optional flag indicating a normalized geometry
                            is desired.  If omitted, defaults to False.

        Returns 1 value:

          geometry - A QRectF object containing the geometry.

        """
        region_geometry = self.banded_region.geometry()

        if not normalized_flag:
            return QRectF( region_geometry )

        pixmap_size = self.pixmap().size()

        normalized_position = (region_geometry.x() / pixmap_size.width(),
                               region_geometry.y() / pixmap_size.height())

        normalized_size = (region_geometry.width() / pixmap_size.width(),
                           region_geometry.height() / pixmap_size.height())

        return QRectF( *normalized_position,
                       *normalized_size )

class MultiRubberBandedPixmap( QLabel ):
    """
    Widget that displays an image as a QLabel that overlays zero or more
    rubberband regions.  One of the rubberband regions can be designed as
    selected which will cause its rendering to be highlighted relative to the
    remaining regions.
    """
    # XXX: explore this handling resizeEvent()'s.

    def __init__( self, filename, resolution=None, line_width=2, line_colors=None ):
        """
        Builds a MultiRubberBandedPixmap from the supplied filename.  The
        initial size may also be specified, as can properties controlling the
        rubberbanded region's visual appearance.

        Takes 4 arguments:
          filename    - Path to the image to display.
          resolution  - Optional pair of positive integers specifying the
                        initial size of the widget.  If omitted, defaults
                        to (400, 300).
          line_width  - Optional integer specifying the width of the
                        rubberband outlines.  If omitted, defaults to 2
                        pixels.
          line_colors - Optional pair of QColors, one for the selected
                        rubberband region and the other for the remaining.
                        If omitted, suitable defaults are chosen.

        Returns 1 value:

          self - The newly created MultiRubberBandedPixmap object.

        """

        super().__init__()

        # get our pixmap from the supplied object or from disk.
        if isinstance( filename, QPixmap ):
            self.loaded_pixmap = filename
        else:
            self.loaded_pixmap = QPixmap.fromImage( QImage( filename ) )

        if resolution is None:
            resolution = (400, 300)

        if line_colors is None:
            line_colors = (QColor( "#222222" ),
                           QColor( "#aa2222" ))

        # use a scaled version of the pixmap in question.
        self.setPixmap( self.loaded_pixmap.scaled( *resolution, Qt.KeepAspectRatio ) )

        # map from tag to bands we're rendering.  only one band can be
        # selected at a time as specified by .selected_tag.
        self.bands        = dict()
        self.selected_tag = None

        self.line_colors  = line_colors
        self.line_width   = line_width

    def add_band( self, tag, geometry ):
        """
        Adds a rubberband to the widget.  If the tag supplied corresponds to
        an existing rubberband, the rubberband takes on the newly supplied
        geometry.

        This method causes the widget to be repainted.

        Takes 2 values:

          tag      - Tag associated with the added rubberband.  Must be
                     hashable.
          geometry - Geometry of the added rubberband, specified as
                     (x, y, width, height) in normalized coordinates (in the
                     range of [0, 1]).

        Returns nothing.
        """

        # we do not need to worry about whether this replaced an existing band
        # or not as we're redrawing everything anyway.
        self.bands[tag] = geometry

        self.repaint()

    def remove_band( self, tag ):
        """
        Removes a rubberband from the widget.  If the rubberband specified by
        the supplied tag is the selected region, no rubberband will be
        selected after its removal.

        Tags that do not correspond to a rubberband are silently ignored.

        This method causes the widget to be repainted.

        Takes 1 value:

          tag - Tag whose rubberband should be removed.

        Returns nothing.
        """

        # ignore requests for removing things we don't know about.
        if not tag in self.bands:
            return

        self.bands.pop( tag, None )

        # handle this band being the selected band.
        if tag is self.selected_tag:
            self.selected_tag = None

        self.repaint()

    def set_selection( self, tag ):
        """
        Sets the selected rubberband.  Selected rubberbands are highlighted to
        indicate the selection status.

        Tags that do not correspond to a rubberband are silently ignored.

        This method causes the widget to be repainted.

        Takes 1 value:

          tag - Tag whose rubberband should be selected.

        Returns nothing.

        """

        if tag in self.bands:
            self.selected_tag = tag

        self.repaint()

    def paintEvent( self, event ):
        """
        Qt widget painting handler.

        NOTE: This should not be invoked directly.

        Takes 1 argument:

          event - QPaintEvent object.

        Returns nothing.

        """

        # repaint the pixmap before we begin drawing on it.
        super().paintEvent( event )

        # get our pixmap's current size so we can draw the bands correctly.
        width, height = (self.pixmap().size().width(),
                         self.pixmap().size().height())

        qp = QPainter()

        qp.begin( self )

        # draw each band that we have, coloring the selected band differently.
        for tag, normalized_geometry in self.bands.items():

            # scale our normalized geometry so it is usable on this pixmap.
            geometry = (normalized_geometry[0] * width,
                        normalized_geometry[1] * height,
                        normalized_geometry[2] * width,
                        normalized_geometry[3] * height)

            # create a dashed outline around our region.  the outline's color
            # is determined by whether this is the selected band or not.
            qp.setBrush( Qt.NoBrush )
            pen = QPen( Qt.DashLine )
            pen.setWidth( self.line_width )

            if tag == self.selected_tag:
                pen.setColor( self.line_colors[1] )
            else:
                pen.setColor( self.line_colors[0] )

            qp.setPen( pen )

            # do it.
            qp.drawRect( *geometry )

        qp.end()
