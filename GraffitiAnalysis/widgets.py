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

class ArtistSelector( QWidget ):
    """
    Widget used to select a subset of the available artists within the
    database. Consists of a QComboBox used to provide a drop-down for
    all artists and a line edit with completer for entering specific
    artists, as well as a list widget for displaying the currently subset of
    selected artists. New artists can be entered as well, and are denoted via
    blue text within the selection list.

    The selected artists can be obtained via the selected_artists property,
    and any new artists entered are returned via the new_artists property.

    """

    # role used to denote whether a selected artist is new (within the
    # database).
    NEW_ARTIST_ROLE = Qt.UserRole + 1

    # placeholder artist stored by backend database.
    DEFAULT_ARTIST = "Unknown"

    def __init__( self, artist_model, parent=None ):
        """
        Constructs a new ArtistSelector from an existing artist model.

        Takes 2 arguments:

          artist_model - Subclass of QAbstractItemModel containing the artists
                         to select from.
          parent       - QWidget parent of this ArtistSelector.

        Returns 1 value:

          self - The newly created ArtistSelector object.

        """

        super().__init__( parent )

        self.artists_box = QComboBox()
        self.artists_box.setModel( artist_model )
        self.artists_box.setEditable( True )

        # we only want this combobox to update on commits to database.
        self.artists_box.setInsertPolicy( QComboBox.NoInsert )

        # let the completer know our model is case-sensitively sorted so it
        # can do binary search behind the scenes.
        self.artists_box.completer().setModelSorting( QCompleter.CaseSensitivelySortedModel )

        self.selection_list = QListWidget()
        self.selection_list.setAlternatingRowColors( True )

        # enable a focus policy to be propagated to our focus proxy, the line
        # edit of the artist combobox. this allows the shortcuts from the buddy
        # labels to highlight the combobox contents as expected.
        self.setFocusPolicy( Qt.TabFocus )
        self.setFocusProxy( self.artists_box.lineEdit() )

        # have the customContextMenuRequested signal emit when the selection
        # list is right-clicked.
        self.selection_list.setContextMenuPolicy( Qt.CustomContextMenu )

        layout = QVBoxLayout()
        layout.setContentsMargins( 0, 0, 0, 0 )
        layout.addWidget( self.artists_box )
        layout.addWidget( self.selection_list )

        self.setLayout( layout )

        # install ArtistSelector as the event filter for its selection list so
        # we can grab key presses.
        self.selection_list.installEventFilter( self )

        # create the right-click context menu.
        self.context_menu = QMenu()

        self.remove_artist_action = QAction( "&Remove artist" )
        self.remove_artist_action.triggered.connect( self.remove_selected_artist )

        self.clear_all_action = QAction( "&Clear all" )
        self.clear_all_action.triggered.connect( self.selection_list.clear )

        self.context_menu.addAction( self.remove_artist_action )
        self.context_menu.addAction( self.clear_all_action )

        # wire everything up.
        self.selection_list.customContextMenuRequested.connect( self.context_menu_requested )

        # note that care is taken here to avoid using the 'activated' and
        # 'currentIndexChanged' signals of QComboBox for list insertion, since
        # navigating the drop-down list with the arrow keys also causes them to
        # be emitted. instead we trigger only off mouse clicks on the drop-down
        # views themselves, as well as return presses within the combobox's
        # QLineEdit.
        self.artists_box.view().pressed.connect( self.artist_selected )
        self.artists_box.lineEdit().returnPressed.connect( self.return_pressed )

    @property
    def new_artists( self ):
        """
        Property to acquire only the new artists entered by the user.

        Takes no arguments.

        Returns 1 value:

          list( str ) - List of all new artist names currently within the
                        selection list.

        """

        return [self.selection_list.item( i ).text()
                for i in range( self.selection_list.count() )
                if self.selection_list.item( i ).data( ArtistSelector.NEW_ARTIST_ROLE )]

    @property
    def selected_artists( self ):
        """
        Property to acquire all artists selected or entered by the user.

        Takes no arguments.

        Returns 1 value:

          list( str ) - List of all artist names currently within the
                        selection list.

        """
        artists = [self.selection_list.item( i ).text()
                   for i in range( self.selection_list.count() )]

        if not artists:
            artists = [self.DEFAULT_ARTIST]

        return artists

    @selected_artists.setter
    def selected_artists( self, artists ):
        """
        Setter used to pre-populate the selection list. Should only be used at
        initialization time.

        Takes 1 argument:

          artists - List of strings containing the artists to pre-populate the
                    selection list with.

        Returns nothing.
        """

        # head off any duplicates provided by casting to a set first.
        artists = set( artists )

        # filter out the default "Unknown" artist
        artists.discard( self.DEFAULT_ARTIST )

        self.selection_list.addItems( artists )

    def __contains__( self, artist ):
        """
        Lookup method for determining if an entered artist is already within
        selection list. The lookup performed is case-insensitive.

        Takes 1 argument:

          artist - Name of the artist to look up.

        Returns 1 value:

          True if the artist name is stored within the selection list, False
          otherwise.

        """
        artists = map( str.lower, self.selected_artists )

        return str.lower( str( artist ) ) in artists

    def artist_exists( self, artist ):
        """
        Helper method to query whether the given artist exists within the
        provided model.

        Takes 1 argument:

          artist - Name of the artist to search for.

        Returns 1 value:

          bool - True if artist exists within our model, False otherwise.

        """

        # perform case-insensitive search for first whole string match.
        if self.artists_box.model().match( self.artists_box.model().index( 0, 0 ),
                                           Qt.EditRole,
                                           artist,
                                           1,
                                           Qt.MatchFixedString | Qt.MatchWrap ):
            return True
        else:
            return False

    @pyqtSlot( QModelIndex )
    def artist_selected( self, artist_index ):
        """
        Slot invoked when the user selects an artist via the full drop-down
        menu of the combobox.

        Takes 1 argument:

          artist_index - QModelIndex corresponding to the artist selected from
                         the drop-down.

        Returns nothing.
        """

        # translate the model index into the artist name.
        artist = self.artists_box.itemText( artist_index.row() )

        if artist not in self:
            # since we know this artist name came from the full drop-down
            # list, we can assume its already in the model.
            artist_item = QListWidgetItem( artist )
            artist_item.setData( ArtistSelector.NEW_ARTIST_ROLE, False )
            self.selection_list.addItem( artist_item )

    @pyqtSlot( int )
    def commit_new_artists( self, record_id ):
        """
        Slot invoked when an art record has been committed, and with it any
        previously new artists entered by the user within this ArtistSelector.

        Takes 1 argument:

          record_id - Unused record identifier provided by committed signal
                      of ArtRecordEditor.

        Returns nothing.
        """

        # all that is new is old once again, reset status of all entries.
        for i in range( self.selection_list.count() ):
            current_item = self.selection_list.item( i )
            current_item.setData( ArtistSelector.NEW_ARTIST_ROLE, False )
            current_item.setForeground( Qt.black )

    @pyqtSlot( QPoint )
    def context_menu_requested( self, pos ):
        """
        Slot invoked when the user right-clicks on the selection list. The
        context menu is provided at the click position.

        Takes 1 argument:

          pos - QPoint position of the right-click in widget coordinates.

        Returns nothing.
        """

        self.context_menu.exec( self.selection_list.mapToGlobal( pos ) )

    def eventFilter( self, obj, event ):
        """
        Event filter used to capture key press events on the selection list.
        We only listen for the delete key as a shortcut for removing the
        currently selected artist from the selection list.

        Takes 2 arguments:

          obj   - Handle to the object the event was intended for. In our case
                  this will always be the selection list.
          event - QEvent containing details of the event.

        Returns 1 value:

          bool - False if the event should be propagated to obj, True
                 otherwise.

        """

        if obj == self.selection_list:
            if event.type() == QEvent.KeyPress:
                if event.key()  == Qt.Key_Delete:
                    self.remove_selected_artist()
                    return True

        return False

    @pyqtSlot()
    def return_pressed( self ):
        """
        Slot invoked whenever the return key is pressed on the line edit
        portion of the QComboBox. The current text of line edit is added as
        an artist to the selection list.

        Takes no arguments.

        Returns nothing.
        """

        artist = self.artists_box.lineEdit().text()
        artist_item = QListWidgetItem()

        # need to determine if a new artist name was entered, or the user
        # entered the full name of an existing artist. note that the
        # artist search is case-insensitive, but we utilize the completer
        # to auto-convert to the 'canonical' name stored within the model.
        if self.artist_exists( artist ):
            self.artists_box.completer().setCompletionPrefix( artist )
            artist = self.artists_box.completer().currentCompletion()

            artist_item.setData( ArtistSelector.NEW_ARTIST_ROLE, False )
        else:
            artist_item.setData( ArtistSelector.NEW_ARTIST_ROLE, True )
            artist_item.setForeground( Qt.red )

        artist_item.setData( Qt.DisplayRole, artist )

        # finally, need to see if this artist has already been entered into
        # the current selection list. this is also a case-insensitive lookup.
        if artist not in self:
            self.selection_list.addItem( artist_item )
        # if the artist exists, but hasn't been committed yet, update the
        # displayed name.
        else:
            existing_items = self.selection_list.findItems( artist,
                                                            Qt.MatchFixedString )

            # the only way the search could fail is if the designated 'default'
            # artist (Unknown) was entered.
            if existing_items and existing_items[0].data( ArtistSelector.NEW_ARTIST_ROLE ):
                existing_items[0].setData( Qt.DisplayRole, artist )

        self.artists_box.lineEdit().selectAll()

    @pyqtSlot()
    def remove_selected_artist( self ):
        """
        Slot invoked whenever the currently selected artist within the
        selection list should be removed.

        Takes no arguments.

        Returns nothing.
        """

        if self.selection_list.count() > 0:
            self.selection_list.takeItem( self.selection_list.currentRow() )

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

        # give ourselves a minimum size which still allows relatively easy
        # access to the size grips.
        self.setMinimumSize( QSize( 10, 10 ) )

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
            label_pos  = self.mapToParent( event.pos() )
            label_rect = self.parent().rect()

            delta_pos = QPoint( event.screenPos().x() - self.tracking_position.x(),
                                event.screenPos().y() - self.tracking_position.y() )

            new_geometry = self.geometry().adjusted( delta_pos.x(),
                                                     delta_pos.y(),
                                                     delta_pos.x(),
                                                     delta_pos.y() )

            # ensure the new geometry stays within the bounds of the current
            # image label while still allowing adjustment of the opposite axis
            # when the cursor is outside the bounds of the outer label.
            if( new_geometry.x() + new_geometry.width() > label_rect.width() or
                label_pos.x() > label_rect.width() ):
                new_geometry.moveTo( label_rect.width() - new_geometry.width(),
                                     new_geometry.y() )
            elif new_geometry.x() < 0 or label_pos.x() < 0:
                new_geometry.moveTo( 0, new_geometry.y() )

            if( new_geometry.y() + new_geometry.height() > label_rect.height() or
                label_pos.y() > label_rect.height() ):
                new_geometry.moveTo( new_geometry.x(),
                                     label_rect.height() - new_geometry.height() )
            elif new_geometry.y() < 0 or label_pos.y() < 0:
                new_geometry.moveTo( new_geometry.x(), 0 )

            self.setGeometry( new_geometry )

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

        self.banded_region.move( event.x(), event.y() )
        new_geometry = self.banded_region.geometry()

        # ensure the new geometry fits within the bounds of the current
        # image label. since we position the upper left corner of banded region
        # to the cursor position, we only need to check the "positive"
        # extremities since its impossible to receive a double-click event
        # outside the bounds of this label.
        if new_geometry.x() + new_geometry.width() > self.rect().width():
            self.banded_region.move( self.rect().width() - new_geometry.width(),
                                     self.banded_region.geometry().y() )

        if new_geometry.y() + new_geometry.height() > self.rect().height():
            self.banded_region.move( self.banded_region.geometry().x(),
                                     self.rect().height() - new_geometry.height() )

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
        self.normalized_band = self.get_region_geometry( True )

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
