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
import os
import subprocess
import time

from PyQt5.QtCore import ( Qt, QItemSelectionModel, QRect, QRegExp, QSize,
                           QSortFilterProxyModel, QStringListModel )
from PyQt5.QtGui import QImage, QPalette, QPixmap, QStandardItemModel, QTransform
from PyQt5.QtWidgets import ( QAbstractItemView, QAction, QApplication,
                              QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
                              QHeaderView, QLabel, QLineEdit, QListView,
                              QMainWindow, QMenu, QMessageBox, QPushButton,
                              QRubberBand, QScrollArea, QSizePolicy, QSpacerItem,
                              QTreeView, QVBoxLayout )

import GraffitiAnalysis.database as grafdb
import GraffitiAnalysis.widgets as grafwidgets

def get_exif_timestamp( file_name ):
    """
    Extracts the creation time from a file containing Exif metadata and
    returns it as seconds since the Epoch.  The 0th IFD's DateTime field is
    used for the creation time.

    Raises ValueError if the specified file's Exif metadata cannot be parsed.

    Takes 1 argument:

      file_name - Path to the file to extract the timestamp from.

    Returns 1 value:

      timestamp - Seconds since the Epoch when the file was created.

    """

    import piexif

    exif_data = piexif.load( file_name )
    exif_str  = exif_data["0th"][piexif.ImageIFD.DateTime].decode( "utf-8" )

    # convert "YYYY:MM:DD hh:mm:ss" into a tuple that we can pass to
    # time.mktime().
    exif_date, exif_time = (map( lambda x: x.split( ":" ), exif_str.split() ))
    exif_date            = tuple( map( int, exif_date ) )
    exif_time            = tuple( map( int, exif_time ) )

    # note that we don't have the day of year/month information.  we also
    # want a non-DST timestamp.
    return time.mktime( (*exif_date, *exif_time, 0, 0, 0) )

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

    def __init__( self, database_file_name=None ):
        """
        XXX
        """

        if database_file_name is None:
            database_file_name = "database.xml"

        # set the state for the window.
        self.db     = grafdb.Database( database_file_name )
        self.photos = self.db.get_photo_records()

        # map keeping track of the open photo editor windows.  each photo
        # record can only be edited by one window at a time.
        self.photo_record_editors = dict()

        # QLabel containing the currently previewed pixmap.  we keep what we
        # loaded so we have the original rather than a scaled copy stored
        # within the photoPreview widget.
        self.preview_pixmap = None

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

        # informational labels for the photo record.
        self.infoStateLabel    = QLabel()
        self.infoSummaryLabel  = QLabel()
        self.infoLocationLabel = QLabel()
        self.infoTakenLabel    = QLabel()
        self.infoTagsLabel     = QLabel()

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

        stats_layout.addWidget( QLabel( "Art Records:" ),
                                1, 0 )
        stats_layout.addWidget( self.infoSummaryLabel,
                                1, 1 )

        stats_layout.addWidget( QLabel( "Location:" ),
                                2, 0 )
        stats_layout.addWidget( self.infoLocationLabel,
                                2, 1 )

        stats_layout.addWidget( QLabel( "Taken:" ),
                                3, 0 )
        stats_layout.addWidget( self.infoTakenLabel,
                                3, 1 )

        stats_layout.addWidget( QLabel( "Tags:" ),
                                4, 0 )
        stats_layout.addWidget( self.infoTagsLabel,
                                4, 1 )

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
        Returns the identifier from the current selection.

        Takes no arguments.

        Returns 1 value:

          identifier - Identifier of the current selection.  Returns None if
                       there isn't a current selection.

        """

        # get our view's index of the data activated, then map it back to the
        # original model's index system so we can get the item's text.

        current_selection = self.selectionView.selectedIndexes()
        if len( current_selection ) == 0:
            return None

        # take any of the selected indices (the entire visible row will be
        # returned) and map it back to original model's indices.
        proxy_index = current_selection[0]
        index       = self.proxyPhotosModel.mapToSource( proxy_index )

        # get the ID column (which is hidden in the proxy's view) in the
        # original model.
        photo_id  = self.photosModel.itemFromIndex( index.sibling( index.row(), 0 ) ).text()

        return int( photo_id )

    def remove_photo_editor( self, photo_id ):

        print( "Removing photo ID={:d} from the edit list.".format( photo_id ) )
        self.photo_record_editors.pop( photo_id, None )

    def refresh_photo_record( self, photo_id ):

        # update the model's information about this record's state.
        for photo in self.photos:
            if photo["id"] == photo_id:
                # find this record in the model by it's photo identifier
                # (there can, and will, only be one) and update it's
                # processing state.
                index = self.photosModel.match( self.photosModel.index( 0, 0 ),
                                                Qt.DisplayRole,
                                                str( photo_id ),
                                                1,
                                                Qt.MatchFixedString )[0]

                self.photosModel.setData( index.sibling( index.row(), 2 ), photo["state"] )

        # update the preview of this record if it's currently selected.
        # otherwise the next time it is selected we'll see the new changes.
        if photo_id == self.get_photo_id_from_selection():
            self.preview_photo_record( photo_id )

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
        photo_id = self.get_photo_id_from_selection()

        # we're not interested in deselection events.  these occur when the
        # user control clicks a selected entry and when the the proxy model
        # filters out the previously visible selection.
        if photo_id is None:
            return

        self.preview_photo_record( photo_id )

    def selectionActivation( self ):
        """
        """

        photo_id = self.get_photo_id_from_selection()
        if photo_id is None:
            #
            # NOTE: we can still receive a double click even if there isn't a
            #       selection (e.g. select something, then ctrl-click it
            #       within the double click window) so I think it's best to
            #       ignore that case here.
            #
            return

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

                self.photo_record_editors[photo_id] = PhotoRecordEditor( self.db,
                                                                         photo,
                                                                         self.preview_pixmap,
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

                # figure out if we have a file on disk we can load.
                #
                # NOTE: not sure what the best timestamp in this case is,
                #       though setting it to the Epoch seems better than other
                #       choices (now, the file's creation/modification
                #       timestamps, etc).
                #
                # XXX: we need to be careful and handle the data with non-GMT
                #      timestamps properly.  this won't be encoded in the files
                #      but needs to be handled during insert into the database.
                #
                if os.path.isfile( photo["filename"] ):
                    try:
                        pixmap    = get_pixmap_from_image( photo["filename"] )
                        exif_time = get_exif_timestamp( photo["filename"] )

                        # orient our picture to be right-side up if need be.
                        #
                        # NOTE: this can cause the window to resize because a 4:3
                        #       picture rotated 90 degrees will become 3:4 which will
                        #       be scaled to fit within the original 4:3 frame.
                        #
                        if photo["rotation"] != 0:
                            rotation_matrix = QTransform()
                            rotation_matrix.rotate( 360 - photo["rotation"] )

                            pixmap = pixmap.transformed( rotation_matrix )

                    except:
                        exif_time = 0
                else:
                    pixmap    = QPixmap()
                    exif_time = 0

                # count the number of child art records in each of the
                # processing states.
                reviewed_count     = 0
                unreviewed_count   = 0
                needs_review_count = 0
                record_count       = 0

                for art in self.db.get_art_records( photo_id ):
                    if art["state"] == "reviewed":
                        reviewed_count += 1
                    elif art["state"] == "unreviewed":
                        unreviewed_count += 1
                    elif art["state"] == "needs_review":
                        needs_review_count += 1

                    record_count += 1

                # keep track of the current pixmap and scale it for our
                # preview.
                self.preview_pixmap = pixmap
                self.photoPreview.setPixmap( self.preview_pixmap.scaled( 600, 450, Qt.KeepAspectRatio ) )

                # update the labels.
                self.infoStateLabel.setText( photo["state"] )
                self.infoSummaryLabel.setText( "{:d} record{:s} ({:2d}/{:2d}/{:2d})".format( record_count,
                                                                                             "" if record_count == 1 else "s",
                                                                                             reviewed_count,
                                                                                             unreviewed_count,
                                                                                             needs_review_count ) )

                if photo["location"] is not None:
                    self.infoLocationLabel.setText( "({:8.5f}, {:8.5f})".format( *photo["location"] ) )
                else:
                    self.infoLocationLabel.setText( "Unknown!" )

                self.infoTakenLabel.setText( time.strftime( date_format,
                                                            time.gmtime( exif_time ) ) )

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
            self.infoTakenLabel.clear()
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

        #   art record summary labels.
        self.artTypeLabel       = QLabel()
        self.artTypeLabel.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.artSizeLabel       = QLabel()
        self.artSizeLabel.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.artQualityLabel    = QLabel()
        self.artQualityLabel.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.artDateLabel       = QLabel()
        self.artDateLabel.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.artArtistsLabel    = QLabel()
        self.artAssociatesLabel = QLabel()
        self.artVandalsLabel    = QLabel()
        self.artTagsLabel       = QLabel()

        #   photo record processing state.
        self.photoProcessingStateComboBox = QComboBox()
        for state in self.db.get_processing_states():
            self.photoProcessingStateComboBox.addItem( state, state )
        self.photoProcessingStateComboBox.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        self.photoProcessingStateComboLabel = QLabel( "Stat&e:" )
        self.photoProcessingStateComboLabel.setBuddy( self.photoProcessingStateComboBox )

        #   photo record tags.
        #
        # NOTE: our accelerator is chosen to match the ArtRecordEditor's
        #       accelerator.
        #
        self.photoTagsLineEdit = QLineEdit( "" )
        self.photoTagsLabel    = QLabel( "Ta&gs:" )
        self.photoTagsLabel.setBuddy( self.photoTagsLineEdit )

        # XXX: need to add
        #
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

        #   art record creation/deletion buttons.
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
        selection_box.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed ) # reduces the space needed.

        #   selected art record information and photo record editing widgets.
        info_and_edit_layout = QGridLayout()
        info_and_edit_layout.setContentsMargins( 0, 0, 0, 0 )
        info_and_edit_layout.setSpacing( 0 )

        # XXX: the layout of these labels is *awful*.  need to fix this.
        art_header_label = QLabel( "<b>Art Record:</b>" )
        art_header_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( art_header_label,
                                        0, 0 )

        type_label = QLabel( "Type:" )
        type_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( type_label,
                                        1, 0 )
        info_and_edit_layout.addWidget( self.artTypeLabel,
                                        1, 1 )

        size_label = QLabel( "Size:" )
        size_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( size_label,
                                        2, 0 )
        info_and_edit_layout.addWidget( self.artSizeLabel,
                                        2, 1 )

        quality_label = QLabel( "Quality:" )
        quality_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( quality_label,
                                        3, 0 )
        info_and_edit_layout.addWidget( self.artQualityLabel,
                                        3, 1 )

        date_label = QLabel( "Date:" )
        date_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( date_label,
                                        4, 0 )
        info_and_edit_layout.addWidget( self.artDateLabel,
                                        4, 1 )

        artists_label = QLabel( "Artists:" )
        artists_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( artists_label,
                                        1, 2 )
        info_and_edit_layout.addWidget( self.artArtistsLabel,
                                        1, 3 )

        associates_label = QLabel( "Associates:" )
        associates_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( associates_label,
                                        2, 2 )
        info_and_edit_layout.addWidget( self.artAssociatesLabel,
                                        2, 3 )

        vandals_label = QLabel( "Vandals:" )
        vandals_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( vandals_label,
                                        3, 2 )
        info_and_edit_layout.addWidget( self.artVandalsLabel,
                                        3, 3 )

        tags_label = QLabel( "Tags:" )
        tags_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( tags_label,
                                        4, 2 )
        info_and_edit_layout.addWidget( self.artTagsLabel,
                                        4, 3 )

        photo_header_label = QLabel( "<b>Photo Record:</b>" )
        photo_header_label.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( photo_header_label,
                                        5, 0 )

        self.photoProcessingStateComboLabel.setSizePolicy( QSizePolicy.Fixed,
                                                           QSizePolicy.Fixed )
        info_and_edit_layout.addWidget( self.photoProcessingStateComboLabel,
                                        6, 0 )
        info_and_edit_layout.addWidget( self.photoProcessingStateComboBox,
                                        6, 1 )

        info_and_edit_layout.addWidget( self.photoTagsLabel,
                                        7, 0 )
        info_and_edit_layout.addWidget( self.photoTagsLineEdit,
                                        7, 1,
                                        1, 3 )

        art_stats_box = QGroupBox()
        art_stats_box.setLayout( info_and_edit_layout )

        horizontal_layout.addWidget( selection_box )
        horizontal_layout.addWidget( art_stats_box )

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

        self.closeAct = QAction( "&Close Window", self, shortcut="Ctrl+W",
                                 triggered=self.close )

        self.commitAct = QAction( "&Commit Photo Record", self, shortcut="Ctrl+S",
                                  triggered=lambda: self.commit_record( update_photo_state=True ) )

        self.editAct = QAction( "&Edit Image", self, shortcut="Ctrl+E",
                                triggered=self.run_image_editor )
        self.viewAct = QAction( "&View Image", self, shortcut="Ctrl+V",
                                triggered=self.run_image_viewer )

        self.windowMenu = QMenu( "&Window", self )
        self.windowMenu.addAction( self.commitAct )
        self.windowMenu.addAction( self.editAct )
        self.windowMenu.addAction( self.viewAct )
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

        # set the processing state combination box to this record's state.
        combo_index = self.photoProcessingStateComboBox.findText( self.record["state"] )
        self.photoProcessingStateComboBox.setCurrentIndex( combo_index )

    def commit_record( self, update_photo_state=True ):
        """
        Updates the PhotoRecordEditor's internal record with user selected
        values before invoking the parent class' method.

        Takes 1 argument:

          update_photo_state - Optional flag indicating whether the photo
                               record's state should be commited.  If False,
                               the state is not actually commited, but the
                               parent class' method is invoked to signal
                               a change related to the record (e.g. a child
                               art record has been added or removed).  If
                               omitted, defaults to True.

        Returns nothing.
        """

        # update the record based on what's currently visible if requested.
        if update_photo_state:
            self.record["state"] = self.photoProcessingStateComboBox.currentText()
            self.record["tags"]  = list( map( lambda x: x.strip(),
                                              self.photoTagsLineEdit.text().split( ", " ) ) )

            self.db.mark_data_dirty()

        super().commit_record()

    def get_art_id_from_selection( self ):
        """
        Returns the identifier from the current selection.

        Takes no arguments.

        Returns 1 value:

          identifier - Identifier of the current selection.  Returns None if
                       there isn't a current selection.

        """

        # get our view's index of the data activated, then map it back to the
        # original model's index system so we can get the item's text.

        current_selection = self.selectionView.selectedIndexes()
        if len( current_selection ) == 0:
            return None

        # take any of the selected indices (the entire visible row will be
        # returned) and map it back to original model's indices.
        proxy_index = current_selection[0]
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

        # signal our parent that we have updated state.
        self.commit_record( update_photo_state=False )

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

        # signal our parent that we have updated state.
        self.commit_record( update_photo_state=False )

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

                # if record we're updating is the one that is selected, also
                # update the preview so that the photo and labels are correct.
                if art_id == self.get_art_id_from_selection():
                    self.preview_art_record( art_id )

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

    def preview_art_record( self, art_id ):
        """
        Updates the window to preview the specified art identifier.  The photo
        preview is updated to highlight the associated art record's region and
        the information labels are set to the record's contents.

        Previewing an unknown art record is silently ignored without updating
        widgets.

        Takes 1 argument:

          art_id - Art record identifier to preview.

        Returns nothing.
        """
        # find the currently selected record.
        for art_record in self.art_records:
            if art_record["id"] == art_id:
                record = art_record
                break
        else:
            # we couldn't find a record with the specified identifier, so go
            # home without doing anything.
            return

        # set the new selection on our photo preview.
        self.photoPreview.set_selection( art_id )

        # update the labels.
        self.artTypeLabel.setText( art_record["type"] )
        self.artSizeLabel.setText( art_record["size"] )
        self.artQualityLabel.setText( art_record["quality"] )
        self.artDateLabel.setText( art_record["date"] )
        self.artArtistsLabel.setText( ", ".join( art_record["artists"] ) )
        self.artAssociatesLabel.setText( ", ".join( art_record["associates"] ) )
        self.artVandalsLabel.setText( ", ".join( art_record["vandals"] ) )
        self.artTagsLabel.setText( ", ".join( art_record["tags"] ) )

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
            art_id = self.get_art_id_from_selection()

            self.preview_art_record( art_id )

            # now that something is selected, we have the opportunity to
            # delete it.
            self.deleteRecordButton.setEnabled( True )

        self.photoPreview.repaint()

    def selectionActivation( self ):
        """
        """

        art_id = self.get_art_id_from_selection()
        if art_id is None:
            #
            # NOTE: we can still receive a double click even if there isn't a
            #       selection (e.g. select something, then ctrl-click it
            #       within the double click window) so I think it's best to
            #       ignore that case here.
            #
            return

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

    def run_image_viewer( self ):
        """
        Runs an image viewer on the record's associated image.  The viewer is
        started asynchronously and is not tracked in any way.

        NOTE: This is currently hardcoded to use feh for image viewing and
              cannot be configured.

        Takes no arguments.

        Returns nothing.

        """

        # XXX: hardcoded program name and image size.
        subprocess.Popen( ["feh", "-dZ", "-g", "800x600", self.record["filename"]] )

    def run_image_editor( self ):
        """
        Runs an image editor on the record's associated image.  The editor is
        started asynchronously and is not tracked in any way.

        NOTE: This is currently hardcoded to use GIMP for image manipulation
              and cannot be configured.

        Takes no arguments.

        Returns nothing.

        """

        # XXX: hardcoded program name and image size.
        subprocess.Popen( ["gimp", "-adfs", self.record["filename"]] )

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
        self.photoPreview = grafwidgets.RubberBandedPixmap( self.preview_pixmap,
                                                            (600, 450) )
        self.photoPreview.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding ) # reduces the space needed.

        pixmap_size = self.photoPreview.pixmap().size()

        # overlay the interactive rubberband box.
        if self.record["region"] is not None:
            # use an existing region.
            normalized_geometry = self.record["region"]
        else:
            # create a new region that spans the entirety of the photo.
            #
            # NOTE: we fake a normalized geometry that starts a single pixel
            #       into the pixmap runs the entirety of both dimensions.
            #
            width_offset  = 1 / pixmap_size.width()
            height_offset = 1 / pixmap_size.height()

            normalized_geometry = [width_offset,
                                   height_offset,
                                   1.0,
                                   1.0]

        # map our normalized geometry to our pixmap's dimensions.
        geometry = QRect( round( normalized_geometry[0] * pixmap_size.width() ),
                          round( normalized_geometry[1] * pixmap_size.height() ),
                          round( normalized_geometry[2] * pixmap_size.width() ),
                          round( normalized_geometry[3] * pixmap_size.height() ) )

        # XXX: abusing the interface
        self.photoPreview.banded_region.setGeometry( geometry )

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

        #  line editor for tags.
        self.artTagsLineEdit = QLineEdit( "" )
        self.artTagsLabel    = QLabel( "Ta&gs:" )
        self.artTagsLabel.setBuddy( self.artTagsLineEdit )

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

        # 1st
        editing_layout.addWidget( self.artTypeComboLabel,
                                  1, 0 )
        editing_layout.addWidget( self.artTypeComboBox,
                                  1, 1 )

        # 2nd
        editing_layout.addWidget( self.artSizeComboLabel,
                                  2, 0 )
        editing_layout.addWidget( self.artSizeComboBox,
                                  2, 1 )

        # 3rd
        editing_layout.addWidget( self.artQualityComboLabel,
                                  3, 0 )
        editing_layout.addWidget( self.artQualityComboBox,
                                  3, 1 )

        # 4th
        editing_layout.addWidget( self.artProcessingStateComboLabel,
                                  4, 0 )
        editing_layout.addWidget( self.artProcessingStateComboBox,
                                  4, 1 )

        # 5th
        editing_layout.addWidget( self.artArtistsListLabel,
                                  0, 3 )
        editing_layout.addWidget( self.artArtistsListView,
                                  1, 3,
                                  4, 1 )

        # 6th
        editing_layout.addWidget( self.artAssociatesListLabel,
                                  0, 5 )
        editing_layout.addWidget( self.artAssociatesListView,
                                  1, 5,
                                  4, 1 )

        # 7th
        editing_layout.addWidget( self.artVandalsListLabel,
                                  0, 7 )
        editing_layout.addWidget( self.artVandalsListView,
                                  1, 7,
                                  4, 1 )

        # 8th
        editing_layout.addWidget( self.artTagsLabel,
                                  6, 0 )
        editing_layout.addWidget( self.artTagsLineEdit,
                                  6, 1,
                                  1, 7 )

        # 9th
        editing_layout.addWidget( self.artDateLabel,
                                  5, 0 )
        editing_layout.addWidget( self.artDateLineEdit,
                                  5, 1 )


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
        self.artTagsLineEdit.setText( "" if len( self.record["tags"] ) == 0 else ", ".join( self.record["tags"] ) )

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
        self.record["tags"]          = list( map( lambda x: x.strip(),
                                                  self.artTagsLineEdit.text().split( ", " ) ) )

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

    # use a specific database if one was provided on the command line.
    if len( sys.argv ) > 1:
        database_file_name = sys.argv[1]
    else:
        database_file_name = None

    photo_record_editor = PhotoRecordViewer( database_file_name )
    photo_record_editor.show()
    sys.exit( app.exec_() )
