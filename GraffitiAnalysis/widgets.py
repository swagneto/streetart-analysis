from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class PhotoPreviewArea( QScrollArea ):
    """
    Specialized scroll area used to display pixmap within a label that scales
    automatically in response to viewport resize events. Any subclass of
    QLabel is supported, but it is assumed the contents are always a pixmap
    (or child of).

    """

    def __init__( self, photo_label=None, parent=None ):
        """
        Constructs a PhotoPreviewArea, with the option for the user to provide
        their own QLabel instance to be displayed within. If none is provided,
        it defaults to a vanilla QLabel.

        Takes 2 arguments:

          photo_label - QLabel instance to be displayed. Any previous size
                        policy set on this label is ignored, and its contents
                        are set to auto scale.
          parent      - QWidget parent of this PhotoPreviewArea.

        Returns 1 value:

          self - The newly created PhotoPreviewArea object.

        """

        super().__init__( parent )

        self.photo_label = photo_label or QLabel()

        # ignore whatever size policy might of been on the label so it can
        # grow and shrink according to our needs.
        self.photo_label.setSizePolicy( QSizePolicy.Ignored,
                                        QSizePolicy.Ignored )

        # have the label auto scale its contents so it fills the entirety
        # of the label's dimensions.
        self.photo_label.setScaledContents( True )

        self.setBackgroundRole( QPalette.Dark )
        self.setAlignment( Qt.AlignHCenter | Qt.AlignVCenter )

        # hide the scroll bars since when they show up as needed things
        # get bogged down for some reason. also scroll bars are ugly.
        self.setVerticalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )

        self.setWidget( self.photo_label )

    def set_photo( self, photo_pixmap ):
        """
        Sets the pixmap for this preview area and rescales in response.

        Takes 1 argument:

          photo_pixmap - QPixmap to display.

        Returns nothing.
        """

        self.photo_label.setPixmap( photo_pixmap )
        self.rescale()

    def rescale( self ):
        """
        Rescales the internal label according to the current width of the
        viewport which displays it. All rescaling occurs based only on the
        width ratio between viewport and label to ensure the aspect ratio
        of the original photo is maintained.

        Takes no arguments.

        Returns nothing.
        """

        if self.photo_label.pixmap() and not self.photo_label.pixmap().isNull():
            if self.photo_label.pixmap().width() > self.photo_label.pixmap().height():
                scale_factor = ( self.viewport().width() /
                                 self.photo_label.pixmap().width() )
            else:
                scale_factor = ( self.viewport().height() /
                                 self.photo_label.pixmap().height() )

            self.photo_label.resize( scale_factor *
                                     self.photo_label.pixmap().size() )

    def clear( self ):
        """
        Short circuit to the clear method on the internal label.

        Takes no arguments.

        Returns nothing.
        """

        self.photo_label.clear()

    def resizeEvent( self, event ):
        """
        Event triggered whenever this preview scroll area (and hence its
        viewport) is resized. A rescaling of the internal label is also
        triggered.

        Takes 1 argument:

          event - The QResizeEvent with details of the event.

        Returns nothing.
        """

        super().resizeEvent( event )
        self.rescale()

class RubberBandedWidget( QWidget ):
    """
    Adds an interactive rubberband box to a widget.

    A new transparent widget is added as a child of a supplied widget which
    holds the machinery needed for an interactive rubberband.  This includes
    several QSizeGrip's that represent the corners of the transparent widget
    and a rubberband box that outlines the transparent widget's extent.

    """

    # Original code and idea came from here:
    #
    #   https://stackoverflow.com/questions/19066804/implementing-resize-handles-on-qrubberband-is-qsizegrip-relevant
    #
    # With a full project here:
    #
    #   https://gist.github.com/Riateche/6743108
    #

    # signals used to notify listeners when the rubberband size has changed
    # geometry due to user interaction.
    resizing = pyqtSignal()
    moving   = pyqtSignal()

    # recommended minimum dimension size for rubberband area. the area can get
    # smaller than this, but it should return to this size when a user
    # double-clicks.
    DEFAULT_SIZE = 37

    def __init__( self, parent ):
        """
        Builds a RubberBandedWidget as a child of the supplied parent.  The
        constructed widget is invisible though occupies the same space as
        the parent widget.

        Takes 1 argument:

          parent - QWidget parent of this RubberBandedWidget.

        Returns 1 value:

          self - The newly created RubberBandedWidget object.

        """

        # run our parent class' constructor and pass our parent widget to it.
        super().__init__( parent )

        # ensure that our size grips only control the rubberband and not the
        # widget that we're operating on.
        self.setWindowFlags( Qt.SubWindow )

        # enable mouse tracking so we can reposition the band via mouse
        # movement.
        self.setMouseTracking( True )
        self.tracking_position = None

        # create a new layout that spans the entirety of the widget without
        # any margin padding.
        layout = QGridLayout( self )
        layout.setContentsMargins( 0, 0, 0, 0 )

        # add size grips into the layout that position themselves at the
        # corners of the widget.
        LT_grip = QSizeGrip( self )
        RT_grip = QSizeGrip( self )
        LB_grip = QSizeGrip( self )
        RB_grip = QSizeGrip( self )

        # assign each grip a size policy which won't interfere with the
        # automatic scaling of the rubberband area during resizes of the preview
        # area. this also allows the rubberband area to become arbitrarily small.
        grip_policy = QSizePolicy( QSizePolicy.Ignored, QSizePolicy.Ignored )

        for grip in [LT_grip, RT_grip, LB_grip, RB_grip]:
            grip.setSizePolicy( grip_policy )

        layout.addWidget( LT_grip, 0, 0, Qt.AlignLeft  | Qt.AlignTop )
        layout.addWidget( RT_grip, 0, 1, Qt.AlignRight | Qt.AlignTop)
        layout.addWidget( LB_grip, 1, 0, Qt.AlignLeft  | Qt.AlignBottom)
        layout.addWidget( RB_grip, 1, 1, Qt.AlignRight | Qt.AlignBottom )

        # create a rubberband parented to our widget and position it in the upper
        # left corner of it.
        self.rubberband = QRubberBand( QRubberBand.Rectangle, self )

        # resize to the recommended minimum.
        self.resize( self.sizeHint() )

        # make our rubberband visible in the corner of the widget.
        self.rubberband.move( 0, 0 )
        self.rubberband.show()

    def mousePressEvent( self, event ):
        """
        Event callback for a mouse click event within this widget's geometry.
        If the left mouse button was clicked, we'll start tracking mouse
        movements.

        Takes 1 argument:

          event - QMouseEvent object with details of the press event.

        Returns nothing.
        """

        if event.button() == Qt.LeftButton:
            # use screenPos to avoid jitter.
            self.tracking_position = event.screenPos()

    def mouseMoveEvent( self, event ):
        """
        Event callback for a mouse move event within this widget's geometry.
        If we're tracking movement because the user has the left button pressed,
        we'll move the banded area to match.

        Takes 1 argument:

          event - QMouseEvent object with details of the move event.

        Returns nothing.
        """

        if self.tracking_position:
            delta_pos = QPoint( event.screenPos().x() - self.tracking_position.x(),
                                event.screenPos().y() - self.tracking_position.y() )

            self.setGeometry( self.geometry().adjusted( delta_pos.x(),
                                                        delta_pos.y(),
                                                        delta_pos.x(),
                                                        delta_pos.y() ) )

            self.tracking_position = event.screenPos()

            # let any listeners know this band's geometry just changed.
            self.moving.emit()

    def mouseReleaseEvent( self, event ):
        """
        Event callback for a mouse button release event within this widget's
        geometry. If we had been previously tracking a movement position, we
        drop it.

        Takes 1 argument:

          event - QMouseEvent object with details of the release event.

        Returns nothing.
        """

        if self.tracking_position:
            self.tracking_position = None

    def mouseDoubleClickEvent( self, event ):
        """
        Event callback for a mouse double-click event within this widget's
        geometry. The event is ignored so it can be propagated to the parent
        widget.

        Takes 1 argument:

          event - QMouseEvent object with details of the double-click event.

        Returns nothing.
        """

        # need to ignore here so the event gets propagated up to our parent
        # RubberBandedLabel widget. otherwise a double-click within the banded
        # area prevents the move-and-resize.
        event.ignore()

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

        # let listeners know the dimensions of this widget have changed.
        self.resizing.emit()

    def sizeHint( self ):
        """
        Returns the recommended size for this widget.

        Returns 1 value:

          QSize - The recommended default dimensions of this widget.

        """

        return QSize( RubberBandedWidget.DEFAULT_SIZE,
                      RubberBandedWidget.DEFAULT_SIZE )

class RubberBandedLabel( QLabel ):
    """
    Widget that displays an image as a QLabel and provides a rubberband region
    on it.

    """

    def __init__( self, pixmap, parent=None ):
        """
        Builds a RubberBandedLabel from the supplied pixmap.

        Takes 2 arguments:

          pixmap - QPixmap of the image to display.
          parent - QWidget parent of this RubberBandedLabel.

        Returns 1 value:

          self - The newly created RubberBandedLabel object.

        """

        super().__init__( parent )

        self.setPixmap( pixmap )

        # add a banded region to ourselves.  track it so we can move it around
        # programmatically.
        self.banded_region   = RubberBandedWidget( self )
        self.normalized_band = QRectF()

        self.banded_region.resizing.connect( self.band_geometry_changed )
        self.banded_region.moving.connect( self.band_geometry_changed )

        # enable mouse tracking so the user can draw a rubberband via
        # click-und-drag.
        self.setMouseTracking( True )
        self.click_origin = None

    def set_normalized_band( self, region ):
        """
        Sets the normalized rubberband region displayed by this widget.

        Takes 1 argument:

          region - Tuple containing the normalized (x, y, width, height) of the
                   region.

        Returns nothing.
        """

        self.normalized_band = QRectF( *region )

    def mousePressEvent( self, event ):
        """
        Event callback for a mouse click event within this widget's geometry.
        If the left mouse button was clicked, we'll store the origin point
        of the click until the button is released.

        Takes 1 argument:

          event - QMouseEvent object with details of the press event.

        Returns nothing.
        """

        if event.button() == Qt.LeftButton:
            self.click_origin = event.pos()

    def mouseMoveEvent( self, event ):
        """
        Event callback for a mouse move event within this widget's geometry.
        If we're tracking movement because the user has the left button pressed,
        we'll redraw the rubberband from the stored origin point to the current
        mouse position.

        Takes 1 argument:

          event - QMouseEvent object with details of the move event.

        Returns nothing.

        """

        if self.click_origin:
            self.banded_region.setGeometry( QRect( self.click_origin, event.pos() ).normalized() )

    def mouseReleaseEvent( self, event ):
        """
        Event callback for a mouse button release event within this widget's
        geometry. If we had been previously tracking an origin click, we drop
        it.

        Takes 1 argument:

          event - QMouseEvent object with details of the release event.

        Returns nothing.
        """

        if self.click_origin:
            self.click_origin = None

    def mouseDoubleClickEvent( self, event ):
        """
        Event callback for a mouse double-click event within this widget's
        geometry. Resizes and moves the banded region to where the double-click
        occurred.

        Takes 1 argument:

          event - QMouseEvent object.

        Returns nothing.
        """

        # move to the click and reset the region to the recommended
        # starting size.
        self.banded_region.resize( self.banded_region.sizeHint() )

        new_position = self.banded_region.geometry()
        new_position.moveCenter( QPoint( event.x(), event.y() ) )
        self.banded_region.setGeometry( new_position )

        # need to update this here since a calling resize() won't trigger a
        # resizeEvent if the band is already at its recommended size.
        self.normalized_band = self.get_region_geometry( True )

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

        normalized_position = ( region_geometry.x() / self.size().width(),
                                region_geometry.y() / self.size().height() )

        normalized_size = ( region_geometry.width() / self.size().width(),
                            region_geometry.height() / self.size().height() )

        return QRectF( *normalized_position,
                       *normalized_size )

    def resizeEvent( self, event ):
        """
        Event callback whenever this widgets size has changed. The dimensions
        of the banded area are scaled to match the new size.

        Takes 1 argument:

          event - QSizeEvent object with details of the resize.

        Returns nothing.
        """

        super().resizeEvent( event )

        geometry = QRect( round( self.normalized_band.x() * event.size().width() ),
                          round( self.normalized_band.y() * event.size().height() ),
                          round( self.normalized_band.width() * event.size().width() ),
                          round( self.normalized_band.height() * event.size().height() ) )

        self.banded_region.setGeometry( geometry )
        self.normalized_geometry = self.get_region_geometry( True )

    @pyqtSlot()
    def band_geometry_changed( self ):
        """
        Slot invoked whenever the geometry of the banded area changes due to
        user interaction. The normalized band tracked in this widget is updated
        accordingly.

        Takes no arguments.

        Returns nothing.
        """

        self.normalized_band = self.get_region_geometry( True )


class MultiRubberBandedLabel( QLabel ):
    """
    Widget that displays an image as a QLabel that overlays zero or more
    rubberband regions.  One of the rubberband regions can be designed as
    selected which will cause its rendering to be highlighted relative to the
    remaining regions.

    """

    def __init__( self, filename, line_width=2, line_colors=None, parent=None ):
        """
        Builds a MultiRubberBandedLabel from the supplied filename. Properties
        controlling the rubberbanded region's visual appearance may also be
        provided.

        Takes 4 arguments:
          filename    - Path or pixmap of the image to display.
          line_width  - Optional integer specifying the width of the
                        rubberband outlines.  If omitted, defaults to 2
                        pixels.
          line_colors - Optional pair of QColors, one for the selected
                        rubberband region and the other for the remaining.
                        If omitted, suitable defaults are chosen.
          parent      - QWidget parent of this MultiRubberBandedLabel.

        Returns 1 value:

          self - The newly created MultiRubberBandedLabel object.

        """

        super().__init__( parent )

        # get our pixmap from the supplied object or from disk.
        if isinstance( filename, QPixmap ):
            loaded_pixmap = filename
        else:
            loaded_pixmap = QPixmap.fromImage( QImage( filename ) )

        if line_colors is None:
            line_colors = (QColor( "#222222" ),
                           QColor( "#aa2222" ))

        self.setPixmap( loaded_pixmap )

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
        if tag not in self.bands:
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

        # get our current size so we can draw the bands correctly.
        width, height = ( self.size().width(),
                          self.size().height() )

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
