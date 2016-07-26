#!/usr/bin/env python

# Broken:
#
#   * Saving a photo record explodes (singleton helper change in get_photo_record())
#   * X'ing out of art record editor doesn't do the cleanup?
#   x focus needs to be on the treeview initially
#   * description label for information
#   * default rubberband box is too big in art editor
#   * Windows with rubberbands need to have the appropriate widgets' sizes
#     fixed so the regions are properly displayed (or rubberbands need to be
#     slaved to their parents to be resized properly [HARD])
#
# Technical debt:
#
#   * factor out the code in PhotoRecordViewer.__init__()
#      - need constants for the treeview columns
#   * factor out the rubberband overlay setup code in refresh_art_record()
#   * Pixmap passed from PhotoRecordViewer to PhotoRecordEditor needs to be
#     the held reference rather than a new one.  Update the widgets to take
#     either a filename or an existing pixmap.
#
# Functionality:
#
#   ArtRecordEditor:
#
#     * Population of window with ArtRecord's contents
#     * New record creation
#     * Record deletion
#     * Commiting a record needs to update the status indicating it happend
#
#   PhotoRecordEditor:
#
#     * Commiting a record needs to update the status indicating it happend
#
# Features:
#
#     * Indicator which region is associated with a given record (given it appears
#       hard-coded on Linux)
#
# UI Nits:
#
#   * tab order for ArtRecordEditor.
#   * sort the contents of the TreeView()'s
#   * [IN PROGRESS] tree view columns need to be sized properly
#   * relative sizing of stats box labels needs to be sized properly (and not
#     encroach on the selection view).
#   * do we need to set the content margins and spacing on every widget, or does
#     it propagate downward in a layout?

from functools import lru_cache, partial
import time

from PyQt5.QtCore import ( Qt, QItemSelectionModel, QRect, QRegExp, QSize,
                           QSortFilterProxyModel, QStringListModel )
from PyQt5.QtGui import QImage, QPalette, QPixmap, QStandardItemModel
from PyQt5.QtWidgets import ( QAbstractItemView, QAction, QApplication,
                              QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
                              QHeaderView, QLabel, QLineEdit, QListView,
                              QMainWindow, QMenu, QMessageBox, QPushButton,
                              QRubberBand, QScrollArea, QSizePolicy, QSpacerItem,
                              QTreeView, QVBoxLayout )

import GraffitiAnalysis.database as grafdb
import GraffitiAnalysis.widgets as grafwidgets

class RecordWindow( QMainWindow ):
    def __init__( self, window_size=None, close_callback=None ):
        """
        Constructs a RecordWindow object representing a basic window.  The
        window is not shown or explicitly positioned prior to the constructor
        returning.

        Takes 2 arguments:

          window_size     - Optional tuple of (width, height) in pixels
                            specifying the RecordEditor's window's size.  If
                            omitted, the window will be big enough to hold its
                            contents.
          close_callback  - Optional callback to invoke when the
                            RecordEditor's window is closed.  If omitted,
                            defaults to None and no callback will be invoked.

        Returns 1 value:

          self - The newly created RecordWindow object.

        """
        super().__init__()

        self.close_callback  = close_callback

        self.centralWidget   = None

        self.create_models()
        self.create_widgets()
        self.create_layout()
        self.create_menus()
        self.set_state()

        if self.centralWidget is not None:
            self.setCentralWidget( self.centralWidget )

        if window_size is not None:
            self.resize( *window_size )

    def create_models( self ):
        """
        Initializes the internal models needed for a RecordWindow.

        This will be invoked prior to widget creation and layout (see
        create_widgets() and create_layout()).

        Takes no arguments.

        Returns nothing.
        """

    def create_widgets( self ):
        """
        Creates the widgets needed for a RecordWindow.

        This will be invoked after model creation and prior to widget layout
        (see create_model() and create_layout()).

        Takes no arguments.

        Returns nothing.
        """

    def create_layout( self ):
        """
        Lays out the widgets within a RecordWindow.

        This will be invoked after models and widgets are created (see
        create_models() and create_widgets()).

        Takes no arguments.

        Returns nothing.
        """

    def create_menus( self ):
        """
        Creats the menus for a RecordWindow.

        This will be invoked after the models are created and widgets are laid
        out (see create_models(), create_widgets(), and create_layouts()).

        Takes no arguments.

        Returns nothing.
        """

    def set_state( self ):
        """
        Sets the initial state for a RecordWindow.

        This will be invoked after the models are created and widgets are laid
        out (see create_models(), create_widgets(), and create_layouts()).

        Takes no arguments.

        Returns nothing.
        """

    def closeEvent( self, event ):
        """
        Handles closing the window by calling the callback specified at window
        creation.

        Takes 1 argument:

          event - XXX: what is this?

        Returns nothing.
        """

        # run our callback if we have one.
        if self.close_callback is not None:
            self.close_callback()

class RecordEditor( RecordWindow ):
    """
    XXX: RecordEditor's have a record, a preview, and commit_record() method.
    """

    def __init__( self, record, preview_pixmap, window_size=None, close_callback=None, commit_callback=None ):
        """
        Constructs a RecordEditor object representing a record editor window.
        The window is not shown or explicitly positioned prior to the
        constructor returning.

        Takes 5 arguments:

          record          - Record object that will be edited by the window.
          preview_pixmap  - QPixmap of the photograph that the record is
                            associated with.
          window_size     - Optional tuple of (width, height) in pixels
                            specifying the RecordEditor's window's size.  If
                            omitted, the window will be big enough to hold its
                            contents.
          close_callback  - Optional callback to invoke when the
                            RecordEditor's window is closed.  If omitted,
                            defaults to None and no callback will be invoked.
          commit_callback - Optional callback to invoke when the RecordEditor
                            has commited changes to the underlying record.  If
                            omitted, defaults to None and no callback will be
                            invoked.

        Returns 1 value:

          self - The newly created RecordEditor object.

        """

        self.record          = record
        self.preview_pixmap  = preview_pixmap
        self.commit_callback = commit_callback

        super().__init__( window_size, close_callback )

    def commit_record( self ):
        """
        Updates the RecordEditor's internal record with user selected values
        before invoking the parent class' method.

        Takes no arguments.

        Returns nothing.
        """

        # run our callback if we have one.
        if self.commit_callback is not None:
            self.commit_callback()

class PhotoRecordViewer( RecordWindow ):
    """
    """

    def __init__( self ):
        """
        XXX
        """

        # set the state for the window.
        self.db     = grafdb.Database( "database.xml" )
        self.photos = self.db.get_photo_records()

        # map keeping track of the open photo editor windows.  each photo
        # record can only be edited by one window at a time.
        self.photo_record_editors = dict()

        # XXX: specify a callback to save the database.
        super().__init__( (800, 600), None )

        self.setWindowTitle( "Photo Record Viewer" )
        self.show()

    def create_models( self ):
        """
        Initializes the internal models needed for a PhotoRecordViewer.

        This will be invoked prior to widget creation and layout (see
        create_widgets() and create_layout()).

        Takes no arguments.

        Returns nothing.
        """

        # create a model of our photo records.
        #
        # NOTE: we keep photo id in the model so we can pull it from our
        #       selection and access the record's data.
        #
        self.photosModel = QStandardItemModel( 0, 3, self )

        self.photosModel.setHeaderData( 0, Qt.Horizontal, "Photo ID" )
        self.photosModel.setHeaderData( 1, Qt.Horizontal, "File Path" )
        self.photosModel.setHeaderData( 2, Qt.Horizontal, "State" )

        # walk through each of the photo records and insert a new item at the
        # beginning of the model's list.
        #
        # XXX: there has got to be a better way to insert things.  the
        #      QAbstractItemModel doesn't have an insert that grows.
        #      inserting QStandardItems explicitly turns our id into an
        #      empty string.  calling reversed() on the photos does not
        #      actually do what we want.
        for photo in self.photos:
            self.photosModel.insertRow( 0 )
            self.photosModel.setData( self.photosModel.index( 0, 0 ), photo["id"] )
            self.photosModel.setData( self.photosModel.index( 0, 1 ), photo["filename"] )
            self.photosModel.setData( self.photosModel.index( 0, 2 ), photo["state"] )

        # create the proxy model for filtering our data based on record
        # processing state.
        self.proxyPhotosModel = QSortFilterProxyModel()
        self.proxyPhotosModel.setFilterKeyColumn( 2 )
        self.proxyPhotosModel.setSourceModel( self.photosModel )

    def create_widgets( self ):
        """
        Creates the widgets needed for a PhotoRecordViewer.

        This will be invoked after model creation and prior to widget layout
        (see create_model() and create_layout()).

        Takes no arguments.

        Returns nothing.
        """

        self.selectionView = QTreeView()
        self.selectionView.setModel( self.proxyPhotosModel )
        self.selectionView.activated.connect( self.selectionActivation )
        self.selectionView.selectionModel().selectionChanged.connect( self.selectionChange )
        self.selectionView.setEditTriggers( QAbstractItemView.NoEditTriggers )
        self.selectionView.setAlternatingRowColors( True )
        self.selectionView.setColumnHidden( 0, True ) # hide the ID
        self.selectionView.setSizePolicy( QSizePolicy.Preferred, QSizePolicy.Preferred )
        self.selectionView.setSortingEnabled( True )
        self.selectionView.resizeColumnToContents( 1 )

        # configure the column headers.
        # XXX: these don't quite work.  stretching the last section prevents the
        #      columns from resizing at the user's request (which would be fine)
        #      though the default size is wonky.
        #
        #      specifying QHeaderView.{Stretch,ResizeToContents} disables any
        #      interactive or programmatic modification of the column sizes.
        #
#        self.selectionView.header().setStretchLastSection( True ) # have the state column fill space - XXX not quite what we want
#        self.selectionView.header().setSectionResizeMode( 0, QHeaderView.Stretch )
#        self.selectionView.header().setSectionResizeMode( 1, QHeaderView.ResizeToContents )
#        self.selectionView.header().setSectionResizeMode( 2, QHeaderView.Stretch )

#        self.selectionView.setAllColumnsShowFocus( True )
#        self.selectionView.keyPressEvent = self.keyPressEvent # XXX: don't do this, it eats keys

        # prevent the users from rearranging the columns.
        self.selectionView.header().setSectionsMovable( False )

        self.selectionBox = QComboBox()

        self.selectionBox.addItem( "all", "all" )
        for state in self.db.get_processing_states():
            self.selectionBox.addItem( state, state )

        self.selectionBox.activated.connect( self.selectionTypeActivation )

        self.selectionBoxLabel = QLabel( "&Processing Type:" )
        self.selectionBoxLabel.setBuddy( self.selectionBox )

        self.photoPreview = QLabel()

        self.photoPreview.setBackgroundRole( QPalette.Base )
        # XXX: why is a preferred size policy with a minimum size better than
        #      ignored with minimum?  the latter causes the image to overflow into
        #      the label area and hide it unless the window is resized.
        self.photoPreview.setSizePolicy( QSizePolicy.Preferred, QSizePolicy.Preferred )
        self.photoPreview.setScaledContents( True )
        self.photoPreview.setMinimumSize( 400, 300 )

        # XXX: change these defaults
        self.infoStateLabel      = QLabel()
        self.infoLocationLabel   = QLabel()
        self.infoAddressLabel    = QLabel()
        self.infoResolutionLabel = QLabel()
        self.infoCreatedLabel    = QLabel()
        self.infoModifiedLabel   = QLabel()
        self.infoTagsLabel       = QLabel()

    def create_layout( self ):
        """
        Lays out the widgets within a PhotoRecordViewer.

        This will be invoked after models and widgets are created (see
        create_models() and create_widgets()).

        Takes no arguments.

        Returns nothing.
        """

        # XXX: debugging layout
        self.setStyleSheet( "border: 1px solid black" )

        selection_layout = QVBoxLayout()
        selection_layout.setContentsMargins( 0, 0, 0, 0 )
        selection_layout.setSpacing( 0 )
        selection_layout.addWidget( self.selectionView )

        record_selection_box = QGroupBox()
        record_selection_box.setLayout( selection_layout )

        selection_type_layout = QHBoxLayout()
        selection_type_layout.setContentsMargins( 0, 0, 0, 0 )
        selection_type_layout.setSpacing( 0 )
        selection_type_layout.addWidget( self.selectionBoxLabel )
        selection_type_layout.addWidget( self.selectionBox )

        selection_type_box = QGroupBox()
        selection_type_box.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed ) # reduces the space needed.
        selection_type_box.setLayout( selection_type_layout )

        selection_layout.addWidget( selection_type_box )

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins( 0, 0, 0, 0 )
        info_layout.setSpacing( 0 )

        record_information_box = QGroupBox()
        record_information_box.setLayout( info_layout )

        stats_box    = QGroupBox()
        stats_layout = QGridLayout()
        stats_layout.setContentsMargins( 0, 0, 0, 0 )
        stats_layout.setSpacing( 0 )

        stats_layout.addWidget( QLabel( "State:" ),
                                0, 0 )
        stats_layout.addWidget( self.infoStateLabel,
                                0, 1 )

        stats_layout.addWidget( QLabel( "Location:" ),
                                1, 0 )
        stats_layout.addWidget( self.infoLocationLabel,
                                1, 1 )

        stats_layout.addWidget( QLabel( "Address:" ),
                                2, 0 )
        stats_layout.addWidget( self.infoAddressLabel,
                                2, 1 )

        stats_layout.addWidget( QLabel( "Resolution:" ),
                                3, 0 )
        stats_layout.addWidget( self.infoResolutionLabel,
                                3, 1 )

        stats_layout.addWidget( QLabel( "Created:" ),
                                4, 0 )
        stats_layout.addWidget( self.infoCreatedLabel,
                                4, 1 )

        stats_layout.addWidget( QLabel( "Modified:" ),
                                5, 0 )
        stats_layout.addWidget( self.infoModifiedLabel,
                                5, 1 )

        stats_layout.addWidget( QLabel( "Tags:" ),
                                6, 0 )
        stats_layout.addWidget( self.infoTagsLabel,
                                6, 1 )

        stats_box.setLayout( stats_layout )

        info_layout.addWidget( self.photoPreview )
        info_layout.addWidget( stats_box )

        main_layout = QHBoxLayout()
        main_layout.addWidget( record_selection_box )
        main_layout.addWidget( record_information_box )
        main_layout.setContentsMargins( 0, 0, 0, 0 )
        main_layout.setSpacing( 0 )

        self.centralWidget = QGroupBox()
        self.centralWidget.setLayout( main_layout )

    def create_menus( self ):
        """
        Creats the menus for a PhotoRecordViewer.

        This will be invoked after the models are created and widgets are laid
        out (see create_models(), create_widgets(), and create_layouts()).

        Takes no arguments.

        Returns nothing.
        """

        self.saveAct = QAction( "&Save", self, shortcut="Ctrl+S",
                                triggered=self.save_database )
        self.exitAct = QAction( "E&xit", self, shortcut="Ctrl+Q",
                                triggered=self.close )

        self.aboutAct = QAction( "&About", self, triggered=self.about )

        self.aboutQtAct = QAction( "About &Qt", self,
                                   triggered=QApplication.instance().aboutQt )

        self.fileMenu = QMenu( "&File", self )
        self.fileMenu.addAction( self.saveAct )
        self.fileMenu.addAction( self.exitAct )

        self.helpMenu = QMenu( "&Help", self )
        self.helpMenu.addAction( self.aboutAct )
        self.helpMenu.addAction( self.aboutQtAct )

        self.menuBar().addMenu( self.fileMenu )
        self.menuBar().addMenu( self.helpMenu )

    def set_state( self ):
        """
        Sets the initial state for a PhotoRecordViewer.

        This will be invoked after the models are created and widgets are laid
        out (see create_models(), create_widgets(), and create_layouts()).

        Takes no arguments.

        Returns nothing.
        """

        # select the first entry so we can use the keyboard for navigation.
        #
        # NOTE: since the first column of our view is hidden, we need to
        #       select the first visible column instead.
        #
        self.selectionView.setCurrentIndex( self.proxyPhotosModel.index( 0, 1 ) )

    def save_database( self ):
        """
        """

        # save the database back to the file that we loaded it from.
        self.db.save_database()

    def get_photo_id_from_selection( self ):
        """
        """

        # get our view's index of the data activated, then map it back to the
        # original model's index system so we can get the item's text.

        # take any of the selected indices (the entire visible row will be
        # returned) and map it back to original model's indices.
        proxy_index = self.selectionView.selectedIndexes()[0]
        index       = self.proxyPhotosModel.mapToSource( proxy_index )

        # get the ID column (which is hidden in the proxy's view) in the
        # original model.
        photo_id  = self.photosModel.itemFromIndex( index.sibling( index.row(), 0 ) ).text()

        return int( photo_id )

    def remove_photo_editor( self, photo_id ):

        print( "Removing photo ID={:d} from the edit list.".format( photo_id ) )
        self.photo_record_editors.pop( photo_id, None )

    def refresh_photo_record( self, photo_id ):
        print( "Need to refresh photo record #{:d}.".format( photo_id ) )

        photo_record = self.db.get_photo_records( photo_id )

        print( photo_record["filename"] )
        print( photo_record["id"] )
        print( photo_record["resolution"] )
        print( photo_record["state"] )
        print( "{:s} ({:d}): ({:d}, {:d}) [{:s}]".format( photo_record["filename"],
                                                          photo_record["id"],
                                                          *photo_record["resolution"],
                                                          photo_record["state"] ) )

    def closeEvent( self, event ):
        """
        """

        # prevent closing when we have open records.
        if len( self.photo_record_editors ) > 0:
            event.ignore()
            return
        elif self.db.are_data_dirty():
            # ask the user if they want to discard their changes.
            confirmation_dialog = QMessageBox()
            confirmation_dialog.setInformativeText( "Unsaved changes have been made.  Are you sure you want to exit?" )
            confirmation_dialog.setStandardButtons( QMessageBox.Ok | QMessageBox.Cancel )
            confirmation_dialog.setDefaultButton( QMessageBox.Cancel )

            result = confirmation_dialog.exec_()

            # nothing to do if we were told this was an accident.
            if result == QMessageBox.Cancel:
                event.ignore()
                return

        # time to go away.
        event.accept()

        super().closeEvent( event )

    def selectionChange( self, selected, deselected ):
        """
        """

        # we're not interested in deselection events.  these occur when the
        # user control clicks a selected entry and when the the proxy model
        # filters out the previously visible selection.
        if len( selected.indexes() ) == 0:
            return

        photo_id = self.get_photo_id_from_selection()

        self.preview_photo_record( photo_id )

    def selectionActivation( self ):
        """
        """

        # XXX: we can still receive a double click even if there isn't a selection
        #      select something, then ctrl-click it within the window...

        photo_id = self.get_photo_id_from_selection()

        # if we're already editing this record, then focus that window instead
        # of creating a new one.
        if photo_id in self.photo_record_editors:
            print( "Activating existing editor." )

            # make the window we already created active and take focus.
            #
            # XXX: does this properly handle all cases where windows are
            #      minimized or hidden? no it doesn't.
            #
            self.photo_record_editors[photo_id].setWindowState( Qt.WindowActive )
            return

        for photo in self.photos:
            if photo["id"] == photo_id:
                print( "Editing photo ID {:d}.".format( photo_id ) )

                # call our refresh method when this window commits changes to
                # the record of interest...
                commit_callback = partial( self.refresh_photo_record, photo_id )

                # ... and cleanup our state when finished editing.
                close_callback = partial( self.remove_photo_editor, photo_id )

                # XXX: there is a better way to pass the photo in.
                self.photo_record_editors[photo_id] = PhotoRecordEditor( self.db,
                                                                         photo,
                                                                         get_pixmap_from_image( photo["filename"] ),
                                                                         close_callback,
                                                                         commit_callback )
                self.photo_record_editors[photo_id].show()
                break

    def selectionTypeActivation( self ):
        """
        """

        selection_type = self.selectionBox.currentText()

        if selection_type == "all":
            self.proxyPhotosModel.setFilterWildcard( "*" )
        else:
            # NOTE: we should use a fixed string match though for some reason
            #       Qt thinks that fixed strings can match anywhere rather than
            #       being an exact match.
            regexp = QRegExp( "^" + selection_type + "$",
                              Qt.CaseInsensitive,
                              QRegExp.RegExp )
            self.proxyPhotosModel.setFilterRegExp( regexp )

        print( selection_type )

    def preview_photo_record( self, photo_id ):
        """
        """

        for photo in self.photos:
            if photo["id"] == photo_id:
                date_format = "%Y/%m/%d %H:%M:%S"

                pixmap = get_pixmap_from_image( photo["filename"] )

                self.photoPreview.setPixmap( pixmap.scaled( 400, 300, Qt.KeepAspectRatio ) )
                self.infoStateLabel.setText( photo["state"] )

                if photo["location"] is not None:
                    self.infoLocationLabel.setText( "({:f}, {:f})".format( *photo["location"] ) )
                else:
                    self.infoLocationLabel.setText( "Unknown!" )

                self.infoAddressLabel.setText( "Unknown!" )
                self.infoResolutionLabel.setText( "{:d} x {:d}".format( *photo["resolution"] ) )
                self.infoCreatedLabel.setText( time.strftime( date_format,
                                                              time.gmtime( photo["created_time"] ) ) )
                self.infoModifiedLabel.setText( time.strftime( date_format,
                                                              time.gmtime( photo["modified_time"] ) ) )

                if len( photo["tags"] ) > 0:
                    self.infoTagsLabel.setText( ", ".join( photo["tags"] ) )
                else:
                    self.infoTagsLabel.clear()

                break
        else:
            # could not find the photo, set some benign defaults.
            self.photoPreview.clear()
            self.infoStateLabel.clear()
            self.infoLocationLabel.clear()
            self.infoAddressLabel.clear()
            self.infoResolutionLabel.clear()
            self.infoCreatedLabel.clear()
            self.infoModifiedLabel.clear()
            self.infoTagsLabel.clear()

    def about( self ):
        QMessageBox.about( self, "About Record Editor",
                           "XXX: Things go here.")

    # XXX: delete me
    def keyPressEvent(self, event):
        key = event.key()
        mod = int(event.modifiers())
        print(
            "<{}> Key 0x{:x}/{}/ {} {} {}".format(
                self,
                key,
                event.text(),
                "  [+shift]" if event.modifiers() & Qt.SHIFT else "",
                "  [+ctrl]" if event.modifiers() & Qt.CTRL else "",
                "  [+alt]" if event.modifiers() & Qt.ALT else ""
            )
        )

class PhotoRecordEditor( RecordEditor ):
    """
    """
    # XXX: rearrange the methods - subclassed, event handlers, ours

    # XXX: review the calling convention.
    def __init__( self, db, photo_record, preview_pixmap, close_callback=None, commit_callback=None ):

        self.db          = db
        self.art_records = db.get_art_records( photo_record["id"] )

        # map tracking the open photo editor windows.  each photo record can
        # only be edited by one window at a time.
        self.art_record_editors = dict()

        super().__init__( photo_record, preview_pixmap, (800, 600), close_callback, commit_callback )

        self.setWindowTitle( "Photo Record Editor: {:s} [{:d}]".format( self.record["filename"],
                                                                        self.record["id"] ) )

    def create_models( self ):
        """
        Initializes the internal models needed for a PhotoRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        # create a model of our photo's art records.
        #
        # NOTE: we keep art id in the model so we can pull it from our
        #       selection and access the record's data.
        self.artModel = QStandardItemModel( 0, 2, self )

        self.artModel.setHeaderData( 0, Qt.Horizontal, "Art ID" )
        self.artModel.setHeaderData( 1, Qt.Horizontal, "State" )

        # walk through each of the photo records and insert a new item at the
        # beginning of the model's list.
        for art in self.art_records:
            self.artModel.insertRow( 0 )
            self.artModel.setData( self.artModel.index( 0, 0 ), art["id"] )
            self.artModel.setData( self.artModel.index( 0, 1 ), art["state"] )

        # create the proxy model for filtering our data based on record
        # processing state.
        self.proxyArtModel = QSortFilterProxyModel()
        self.proxyArtModel.setFilterKeyColumn( 1 )
        self.proxyArtModel.setSourceModel( self.artModel )

    def create_widgets( self ):
        """
        Creates the widgets needed for a PhotoRecordEditor.

        Takes no arguments.

        Returns nothing.
        """
        #    photo preview.
        self.photoPreview = grafwidgets.MultiRubberBandedPixmap( self.preview_pixmap,
                                                                 resolution=(600, 450) )

        # draw the art record regions.
        # XXX: factor this into a separate routine
        for art in self.art_records:
            if art["region"] is not None:
                self.photoPreview.add_band( art["id"], art["region"] )

        #    processing type.
        self.selectionBox = QComboBox()

        self.selectionBox.addItem( "all", "all" )
        for state in self.db.get_processing_states():
            self.selectionBox.addItem( state, state )

        self.selectionBox.activated.connect( self.selectionTypeActivation )

        self.selectionBoxLabel = QLabel( "&Processing Type:" )
        self.selectionBoxLabel.setBuddy( self.selectionBox )

        #   art record selection.
        #
        #   XXX: describe these.
        self.selectionView = QTreeView()
        self.selectionView.setModel( self.proxyArtModel )
        self.selectionView.activated.connect( self.selectionActivation )
        self.selectionView.selectionModel().selectionChanged.connect( self.recordSelectionChange )
        self.selectionView.setEditTriggers( QAbstractItemView.NoEditTriggers )
        self.selectionView.setAlternatingRowColors( True )
        self.selectionView.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.selectionView.setSortingEnabled( True )
        self.selectionView.header().setSectionsMovable( False )

        #   record addition and removal buttons.
        self.newRecordButton = QPushButton( "&New Record" )
        self.newRecordButton.clicked.connect( self.create_new_record )

        self.deleteRecordButton = QPushButton( "&Delete Record" )
        self.deleteRecordButton.clicked.connect( self.delete_record )

        # we shouldn't be able to push the delete button until we have a
        # record selected.
        self.deleteRecordButton.setEnabled( False )

        # XXX: need to add
        #
        #  * photo record state combo box
        #  * tag editor
        #  * description

    def create_layout( self ):
        """
        Lays out the widgets within a PhotoRecordEditor.

        Takes no arguments.

        Returns nothing.
        """
        # highlight all of our widgets so we can debug layouts.
        # XXX: debugging support.
        self.setStyleSheet( "border: 1px solid black" )

        #   vertical layout of the photo preview and everything else.
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins( 0, 0, 0, 0 )
        main_layout.setSpacing( 0 )

        #   horizontal layout of everything else
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins( 0, 0, 0, 0 )
        horizontal_layout.setSpacing( 0 )

        #   vertical layout for the selection and the selection type.
        selection_layout = QVBoxLayout()
        selection_layout.setContentsMargins( 0, 0, 0, 0 )
        selection_layout.setSpacing( 0 )

        #   selection type label/combo box.
        selection_type_layout = QHBoxLayout()
        selection_type_layout.setContentsMargins( 0, 0, 0, 0 )
        selection_type_layout.setSpacing( 0 )
        selection_type_layout.addWidget( self.selectionBoxLabel )
        selection_type_layout.addWidget( self.selectionBox )
        selection_type_box = QGroupBox()
        selection_type_box.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed ) # reduces the space needed.
        selection_type_box.setLayout( selection_type_layout )

        record_modification_layout = QHBoxLayout()
        record_modification_layout.setContentsMargins( 0, 0, 0, 0 )
        record_modification_layout.setSpacing( 0 )
        record_modification_layout.addWidget( self.newRecordButton )
        record_modification_layout.addWidget( self.deleteRecordButton )

        record_modification_box = QGroupBox()
        record_modification_box.setLayout( record_modification_layout )
        record_modification_box.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed ) # reduces the space needed.

        selection_layout.addWidget( self.selectionView )
        selection_layout.addWidget( selection_type_box )
        selection_layout.addWidget( record_modification_box )

        selection_box = QGroupBox()
        selection_box.setLayout( selection_layout )

        horizontal_layout.addWidget( selection_box )

        horizontal_box = QGroupBox()
        horizontal_box.setLayout( horizontal_layout )

        main_layout.addWidget( self.photoPreview )
        main_layout.setAlignment( self.photoPreview, Qt.AlignCenter ) # the preview should be centered.
        main_layout.addWidget( horizontal_box )

        self.centralWidget = QGroupBox()
        self.centralWidget.setLayout( main_layout )

    def create_menus( self ):
        """
        Creats the menus for a PhotoRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        self.closeAct = QAction( "&Close", self, shortcut="Ctrl+W",
                                 triggered=self.close )

        self.commitAct = QAction( "&Commit", self, shortcut="Ctrl+S",
                                  triggered=self.commit_record )

        self.windowMenu = QMenu( "&Window", self )
        self.windowMenu.addAction( self.commitAct )
        self.windowMenu.addAction( self.closeAct )

        self.menuBar().addMenu( self.windowMenu )

    def set_state( self ):
        """
        Sets the initial state for a PhotoRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        # select the first entry so we can use the keyboard for navigation.
        self.selectionView.setCurrentIndex( self.proxyArtModel.index( 0, 0 ) )

    def commit_record( self ):
        """
        Updates the PhotoRecordEditor's internal record with user selected
        values before invoking the parent class' method.

        Takes no arguments.

        Returns nothing.
        """
        print( "Commiting photo record #{:d}.".format( self.record["id"] ) )

        # update the record based on what's currently visible.
        print( "XXX: do this" )

        self.db.mark_data_dirty()

        super().commit_record()

    def get_art_id_from_selection( self ):
        """
        """

        # get our view's index of the data activated, then map it back to the
        # original model's index system so we can get the item's text.

        # take any of the selected indices (the entire visible row will be
        # returned) and map it back to original model's indices.
        proxy_index = self.selectionView.selectedIndexes()[0]
        index       = self.proxyArtModel.mapToSource( proxy_index )

        # get the ID column (which is hidden in the proxy's view) in the
        # original model.
        art_id  = self.artModel.itemFromIndex( index.sibling( index.row(), 0 ) ).text()

        return int( art_id )

    def create_new_record( self ):
        """
        """
        print( "Create a new art record for photo ID {:d}.".format( self.record["id"] ) )

        # create a new record in the database and keep track of it within the
        # editor.
        new_art_record = self.db.new_art_record( self.record["id"] )
        self.art_records.append( new_art_record )

        # add the record into the model so we can see it.
        self.artModel.insertRow( 0 )
        self.artModel.setData( self.artModel.index( 0, 0 ), new_art_record["id"] )
        self.artModel.setData( self.artModel.index( 0, 1 ), new_art_record["state"] )

        # edit the record as a convenience.
        self.edit_art_record( new_art_record["id"] )

    def delete_record( self ):
        """
        """

        art_id = self.get_art_id_from_selection()

        # if we're currently editing this record, then tell the user we're not
        # doing anything until they close the window.
        if art_id in self.art_record_editors:
            print( "Art record #{:d} is being edited.  Cannot delete an actively edited record.".format( art_id ) )
            return

        confirmation_dialog = QMessageBox()
        confirmation_dialog.setInformativeText( "Are you sure you want to remove art record #{:d}?".format( art_id ) )
        confirmation_dialog.setStandardButtons( QMessageBox.Ok | QMessageBox.Cancel )
        confirmation_dialog.setDefaultButton( QMessageBox.Cancel )
        result = confirmation_dialog.exec_()

        # nothing to do if we were told this was an accident.
        if result == QMessageBox.Cancel:
            return

        # find this record in the model by it's art identifier (there
        # can, and will, only be one) and update it's processing
        # state.
        index = self.artModel.match( self.artModel.index( 0, 0 ),
                                     Qt.DisplayRole,
                                     str( art_id ),
                                     1,
                                     Qt.MatchFixedString )[0]
        self.artModel.removeRow( index.row() )

        # remove the record from the database.
        self.db.delete_art_record( art_id )

        # and remove the rubberband from our photo.
        self.photoPreview.remove_band( art_id )

    def edit_art_record( self, art_id ):
        """
        """

        # if we're already editing this record, then focus that window instead
        # of creating a new one.
        if art_id in self.art_record_editors:
            print( "Activating existing editor." )

            # make the window we already created active and take focus.
            #
            # XXX: does this properly handle all cases where windows are
            #      minimized or hidden?
            #
            self.art_record_editors[art_id].setWindowState( Qt.WindowActive )
            return

        for art in self.art_records:
            if art["id"] == art_id:
                print( "Editing art ID {:d}.".format( art_id ) )

                # call our refresh method when this window commits changes to
                # the record of interest...
                commit_callback = partial( self.refresh_art_record, art_id )

                # ... and cleanup our state when finished editing.
                close_callback = partial( self.remove_art_editor, art_id )

                self.art_record_editors[art_id] = ArtRecordEditor( self.db,
                                                                   self.record["id"],
                                                                   art,
                                                                   self.preview_pixmap,
                                                                   close_callback,
                                                                   commit_callback )
                self.art_record_editors[art_id].show()
                break

    def remove_art_editor( self, art_id ):

        print( "Removing art ID={:d} from the edit list.".format( art_id ) )
        self.art_record_editors.pop( art_id, None )

    def refresh_art_record( self, art_id ):
        print( "Need to refresh art record #{:d}.".format( art_id ) )

        # XXX: factor this into a separate routine
        for art in self.art_records:
            if art["id"] == art_id:
                # find this record in the model by it's art identifier (there
                # can, and will, only be one) and update it's processing
                # state.
                index = self.artModel.match( self.artModel.index( 0, 0 ),
                                             Qt.DisplayRole,
                                             str( art_id ),
                                             1,
                                             Qt.MatchFixedString )[0]

                self.artModel.setData( index.sibling( index.row(), 1 ), art["state"] )

                # update this record's rubberband box.
                if art["region"] is not None:
                    self.photoPreview.add_band( art["id"], art["region"] )

                print( "    Type:         {:s}\n"
                       "    Artists:      {:s}\n"
                       "    Associations: {:s}\n"
                       "    Quality:      {:s}\n"
                       "    Size:         {:s}\n"
                       "    State:        {:s}\n"
                       "    Region:       {}\n".format( art["type"],
                                                        ", ".join( art["artists"] ),
                                                        ", ".join( art["associates"] ),
                                                        art["quality"],
                                                        art["size"],
                                                        art["state"],
                                                        art["region"] ) )
                break

    def recordSelectionChange( self, selected, deslected ):
        """
        """

        # determine which, if any, item is now selected.  then redraw all of
        # the regions.
        if len( selected.indexes() ) == 0:
            self.photoPreview.set_selection( None )

            # nothing is selected, so we can't delete anything.
            self.deleteRecordButton.setEnabled( False )
        else:
            self.photoPreview.set_selection( self.get_art_id_from_selection() )

            # now that something is selected, we have the opportunity to
            # delete it.
            self.deleteRecordButton.setEnabled( True )

        self.photoPreview.repaint()

    def selectionActivation( self ):
        """
        """

        # XXX: we can still receive a double click even if there isn't a selection
        #      select something, then ctrl-click it within the window...

        art_id = self.get_art_id_from_selection()

        self.edit_art_record( art_id )

    def selectionTypeActivation( self ):
        """
        """

        selection_type = self.selectionBox.currentText()

        if selection_type == "all":
            self.proxyArtModel.setFilterWildcard( "*" )
        else:
            # NOTE: we should use a fixed string match though for some reason
            #       Qt thinks that fixed strings can match anywhere rather than
            #       being an exact match.
            regexp = QRegExp( "^" + selection_type + "$",
                              Qt.CaseInsensitive,
                              QRegExp.RegExp )
            self.proxyArtModel.setFilterRegExp( regexp )

        print( selection_type )

    def closeEvent( self, event ):
        """
        """

        # prevent closing when we have open records.
        if len( self.art_record_editors ) > 0:
            event.ignore()
            return

        # time to go away.
        event.accept()

        super().closeEvent( event )

class ArtRecordEditor( RecordEditor ):
    """
    """

    # XXX: review the calling convention.
    def __init__( self, db, photo_id, art_record, preview_pixmap, close_callback=None, commit_callback=None ):

        self.db             = db
        self.photo_id       = photo_id

        # XXX: we only keep this around until we fix our resizing pixmap situation
        #      and can initialize it with an existing pixmap (preview_pixmap).
        self.photo_record   = self.db.get_photo_records( photo_id )
        print( "Photo record [{}]: {}".format( self.photo_id, self.photo_record ) )

        super().__init__( art_record, preview_pixmap, (800, 600), close_callback, commit_callback )

        self.setWindowTitle( "Art Record Editor: {:s} [{:d}, {:d}]".format( self.photo_record["filename"],
                                                                            self.photo_id,
                                                                            self.record["id"] ) )

    def create_models( self ):
        """
        Initializes the internal models needed for an ArtRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        artists_model     = QStringListModel( self.db.get_artists(), self )
        self.artistsModel = artists_model

    def create_widgets( self ):
        """
        Creates the widgets needed for an ArtRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        # create a preview of this record's photo.
        self.photoPreview = grafwidgets.RubberBandedPixmap( self.photo_record["filename"],
                                                            (600, 450) )
        self.photoPreview.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding ) # reduces the space needed.

        # overlay the interactive rubberband box to se
        if self.record["region"] is not None:
            normalized_geometry = self.record["region"]

            pixmap_size = self.photoPreview.pixmap().size()

            # map our normalized geometry to our pixmap's dimensions.
            geometry = QRect( round( normalized_geometry[0] * pixmap_size.width() ),
                              round( normalized_geometry[1] * pixmap_size.height() ),
                              round( normalized_geometry[2] * pixmap_size.width() ),
                              round( normalized_geometry[3] * pixmap_size.height() ) )

            # XXX: abusing the interface
            self.photoPreview.banded_region.setGeometry( geometry )
        else:
            # start the rubberband region covering the entirety of the photo.
            # this provides a sensible default if the user doesn't change it
            # before commiting the record.
            band_thickness = 4

            # XXX: abusing the interface
            self.photoPreview.banded_region.resize( self.photoPreview.geometry().width() - band_thickness,
                                                    self.photoPreview.geometry().height() - band_thickness )

        # create the combination boxes/line edits and their associated labels
        # that let the user edit this record.

        #  art type
        self.artTypeComboBox   = QComboBox()
        for art_type in self.db.get_art_types():
            self.artTypeComboBox.addItem( art_type, art_type )
        self.artTypeComboLabel = QLabel( "&Type:" )
        self.artTypeComboLabel.setBuddy( self.artTypeComboBox )

        #  art size
        self.artSizeComboBox   = QComboBox()
        for art_size in self.db.get_art_sizes():
            self.artSizeComboBox.addItem( art_size, art_size )
        self.artSizeComboLabel = QLabel( "&Size:" )
        self.artSizeComboLabel.setBuddy( self.artSizeComboBox )

        #  art quality
        self.artQualityComboBox   = QComboBox()
        for art_quality in self.db.get_art_qualities():
            self.artQualityComboBox.addItem( art_quality, art_quality )
        self.artQualityComboLabel = QLabel( "&Quality:" )
        self.artQualityComboLabel.setBuddy( self.artQualityComboBox )

        #  art date
        self.artDateLineEdit = QLineEdit( "" )
        self.artDateLabel    = QLabel( "&Date:" )
        self.artDateLabel.setBuddy( self.artDateLineEdit )

        #  record processing state
        self.artProcessingStateComboBox = QComboBox()
        for state in self.db.get_processing_states():
            self.artProcessingStateComboBox.addItem( state, state )
        self.artProcessingStateComboLabel = QLabel( "Stat&e:" )
        self.artProcessingStateComboLabel.setBuddy( self.artProcessingStateComboBox )

        # create the multi-selection views for the artists.

        #  artists
        self.artArtistsListView = QListView()
        self.artArtistsListView.setModel( self.artistsModel )
        self.artArtistsListView.setSelectionMode( QAbstractItemView.ExtendedSelection )
        self.artArtistsListView.setEditTriggers( QAbstractItemView.NoEditTriggers )

        self.artArtistsListLabel = QLabel( "&Artists:" )
        self.artArtistsListLabel.setBuddy( self.artArtistsListView )

        #  associates
        self.artAssociatesListView = QListView()
        self.artAssociatesListView.setModel( self.artistsModel )
        self.artAssociatesListView.setSelectionMode( QAbstractItemView.ExtendedSelection )
        self.artAssociatesListView.setEditTriggers( QAbstractItemView.NoEditTriggers )

        self.artAssociatesListLabel = QLabel( "Ass&ociates:" )
        self.artAssociatesListLabel.setBuddy( self.artAssociatesListView )

        #  vandals
        self.artVandalsListView = QListView()
        self.artVandalsListView.setModel( self.artistsModel )
        self.artVandalsListView.setSelectionMode( QAbstractItemView.ExtendedSelection )
        self.artVandalsListView.setEditTriggers( QAbstractItemView.NoEditTriggers )

        self.artVandalsListLabel = QLabel( "&Vandals:" )
        self.artVandalsListLabel.setBuddy( self.artVandalsListView )

    def create_layout( self ):
        """
        Lays out the widgets within an ArtRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        # highlight all of our widgets so we can debug layouts.
        # XXX: debugging support.
        self.setStyleSheet( "border: 1px solid black" )

        editing_layout = QGridLayout()
        editing_layout.addWidget( QLabel( "Art Record ID:" ),
                                  0, 0 )
        editing_layout.addWidget( QLabel( "{:d}".format( self.record["id"] ) ),
                                  0, 1 )

        editing_layout.addWidget( self.artTypeComboLabel,
                                  1, 0 )
        editing_layout.addWidget( self.artTypeComboBox,
                                  1, 1 )

        editing_layout.addWidget( self.artSizeComboLabel,
                                  2, 0 )
        editing_layout.addWidget( self.artSizeComboBox,
                                  2, 1 )

        editing_layout.addWidget( self.artQualityComboLabel,
                                  3, 0 )
        editing_layout.addWidget( self.artQualityComboBox,
                                  3, 1 )

        editing_layout.addWidget( self.artDateLabel,
                                  4, 0 )
        editing_layout.addWidget( self.artDateLineEdit,
                                  4, 1 )

        editing_layout.addWidget( self.artProcessingStateComboLabel,
                                  5, 0 )
        editing_layout.addWidget( self.artProcessingStateComboBox,
                                  5, 1 )

        editing_layout.addWidget( self.artArtistsListLabel,
                                  0, 3 )
        editing_layout.addWidget( self.artArtistsListView,
                                  1, 3,
                                  4, 1 )

        editing_layout.addWidget( self.artAssociatesListLabel,
                                  0, 5 )
        editing_layout.addWidget( self.artAssociatesListView,
                                  1, 5,
                                  4, 1 )

        editing_layout.addWidget( self.artVandalsListLabel,
                                  0, 7 )
        editing_layout.addWidget( self.artVandalsListView,
                                  1, 7,
                                  4, 1 )

        editing_box = QGroupBox()
        editing_box.setLayout( editing_layout )

        #   vertical layout of the photo preview and everything else.
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins( 0, 0, 0, 0 )
        main_layout.setSpacing( 0 )

        main_layout.addWidget( self.photoPreview )
        main_layout.setAlignment( self.photoPreview, Qt.AlignCenter ) # the preview should be centered.
        main_layout.addWidget( editing_box )

        self.centralWidget = QGroupBox()
        self.centralWidget.setLayout( main_layout )

    def create_menus( self ):
        """
        Creats the menus for an ArtRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        self.closeAct  = QAction( "C&lose", self, shortcut="Ctrl+W",
                                  triggered=self.close )

        self.commitAct = QAction( "&Commit", self, shortcut="Ctrl+S",
                                  triggered=self.commit_record )

        self.windowMenu = QMenu( "&Window", self )
        self.windowMenu.addAction( self.commitAct )
        self.windowMenu.addAction( self.closeAct )

        self.menuBar().addMenu( self.windowMenu )

    def set_state( self ):
        """
        Sets the initial state for an ArtRecordEditor.

        Takes no arguments.

        Returns nothing.
        """

        # XXX: better error checking for record types that aren't in the combo
        #      box? validate it when pulling from the db.
        self.artTypeComboBox.setCurrentIndex( self.artTypeComboBox.findText( self.record["type"] ) )
        self.artSizeComboBox.setCurrentIndex( self.artSizeComboBox.findText( self.record["size"] ) )
        self.artQualityComboBox.setCurrentIndex( self.artQualityComboBox.findText( self.record["quality"] ) )
        self.artDateLineEdit.setText( "" if self.record["date"] is None else self.record["date"] )
        self.artProcessingStateComboBox.setCurrentIndex( self.artProcessingStateComboBox.findText( self.record["state"] ) )

        # ensure that we start with an empty selection view.
        self.artArtistsListView.selectionModel().clear()
        self.artAssociatesListView.selectionModel().clear()
        self.artVandalsListView.selectionModel().clear()

        # walk through the model backing each of our artist selections and
        # select each one that is associated with the art.
        #
        # NOTE: each of the views uses the same model so we can iterate across
        #       any one's contents.
        #
        for artist_index, artist in enumerate( self.artArtistsListView.model().stringList() ):
            if artist in self.record["artists"]:
                self.artArtistsListView.selectionModel().select( self.artArtistsListView.model().index( artist_index ),
                                                                 QItemSelectionModel.Select )
            if artist in self.record["associates"]:
                self.artAssociatesListView.selectionModel().select( self.artAssociatesListView.model().index( artist_index ),
                                                                    QItemSelectionModel.Select )
            if artist in self.record["vandals"]:
                self.artVandalsListView.selectionModel().select( self.artVandalsListView.model().index( artist_index ),
                                                                 QItemSelectionModel.Select )

    def commit_record( self ):
        """
        Updates the ArtRecordEditor's internal record with user selected
        values before invoking the parent class' method.

        Takes no arguments.

        Returns nothing.
        """

        print( "Commiting art record #{:d}.".format( self.record["id"] ) )

        # update the record based on what's currently visible.
        self.record["type"]          = self.artTypeComboBox.currentText()
        self.record["size"]          = self.artSizeComboBox.currentText()
        self.record["quality"]       = self.artQualityComboBox.currentText()
        self.record["date"]          = self.artDateLineEdit.text()
        self.record["state"]         = self.artProcessingStateComboBox.currentText()
        self.record["modified_time"] = time.mktime( time.gmtime() )

        self.record["artists"]       = [artist.data() for artist in self.artArtistsListView.selectedIndexes()]
        self.record["associates"]    = [associate.data() for associate in self.artAssociatesListView.selectedIndexes()]
        self.record["vandals"]       = [vandal.data() for vandal in self.artVandalsListView.selectedIndexes()]

        # update the region.
        normalized_geometry = self.photoPreview.get_region_geometry( True )

        self.record["region"] = normalized_geometry.getRect()

        self.db.mark_data_dirty()

        super().commit_record()

@lru_cache( maxsize=16 )
def get_pixmap_from_image( filename ):
    """
    """
    return QPixmap.fromImage( QImage( filename ) )

if __name__ == '__main__':

    import sys

    app = QApplication( sys.argv )
    photo_record_editor = PhotoRecordViewer()
    photo_record_editor.show()
    sys.exit( app.exec_() )
