#!/usr/bin/env python

# Broken:
#
# Technical debt:
#
#   * factor out the code in PhotoRecordViewer.__init__()
#
# Functionality:
#
#   ArtRecordEditor:
#
#     * Commiting a record needs to update the status indicating it happend
#
#   PhotoRecordEditor:
#
#     * Commiting a record needs to update the status indicating it happend
#
# Features:
#
#
# UI Nits:
#
#   * sort the contents of the TreeView()'s
#   * relative sizing of stats box labels needs to be sized properly (and not
#     encroach on the selection view).
#   * do we need to set the content margins and spacing on every widget, or does
#     it propagate downward in a layout?

from functools import lru_cache
import os
import subprocess
import time

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import GraffitiAnalysis.database as grafdb
import GraffitiAnalysis.widgets as grafwidgets

# constant for the default role value used when accessing the data() method
# of a QStandardItem.
DATA_ROLE = Qt.UserRole + 1

class LineEditDialog( QDialog ):
    """
    Creates a dialog containing a labeled QLineEdit widget and a pair
    of buttons to accept the input or dismiss it.  The resulting
    dialog should be .exec_()'d so the result can be acquired with
    acceptance returning LineEditDialog.ACCEPTED and dismissal
    returning LineEditDialog.CANCELLED.
    """

    # constants for cancelling and accepting the line edit dialog.
    CANCELLED = 0
    ACCEPTED  = 1

    def __init__( self, label="Input:", title="User Input" ):
        """
        Initializes a LineEditDialog with a label, its companiion line
        edit, and a pair of buttons; one for accepting the dialog and
        one for dismissing it.

        Takes 1 argument:

          label - Optional string specifying the label to show next to the
                  QLineEdit widget.  If omitted, defaults to a generic
                  input string.
          title - Optional string specifying the dialog's window title.
                  If omitted, defaults to a generic string.

        Returns nothing.

        """

        super().__init__()

        self.setWindowTitle( title )

        self.artist_edit = QLineEdit( self )
        okay_button      = QPushButton( "&Okay" )
        cancel_button    = QPushButton( "&Cancel" )

        # prevent our buttons from stretching if the dialog is resized to
        # get more room in the line edit.
        okay_button.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        cancel_button.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )

        # layout the line edit on one row, and the buttons on another.
        layout = QGridLayout( self )
        layout.addWidget( QLabel( label ),  0, 0 )
        layout.addWidget( self.artist_edit, 0, 1 )
        layout.addWidget( okay_button,      1, 0 )
        layout.addWidget( cancel_button,    1, 1 )

        okay_button.clicked.connect( self.accept )
        cancel_button.clicked.connect( self.reject )

class RecordWindow( QMainWindow ):
    DEFAULT_H_SIZE = 800
    DEFAULT_V_SIZE = 600

    def __init__( self, window_size=QSize( DEFAULT_H_SIZE, DEFAULT_V_SIZE ) ):
        """
        Constructs a RecordWindow object representing a basic window.  The
        window is not shown or explicitly positioned prior to the constructor
        returning.

        Takes 1 argument:

          window_size     - Optional QSize specifying the RecordEditor's
                            window's size.  If omitted, the window will be
                            big enough to hold its contents.

        Returns 1 value:

          self - The newly created RecordWindow object.

        """
        super().__init__()

        self.centralWidget = None
        self.window_size   = window_size

        self.create_models()
        self.create_widgets()
        self.create_layout()
        self.create_menus()
        self.set_state()

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
        Creates the menus for a RecordWindow.

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

    def sizeHint( self ):
        """
        Provides the recommended size for this window in a way that allows Qt
        the final say on how large/small the actual size should be.

        Returns 1 value:

          QSize - containing the suggested width and height.

        """
        return self.window_size

class RecordEditor( RecordWindow ):
    """
    XXX: RecordEditor's have a record, a preview, and commit_record() method.
    """

    # signal emitted when a RecordEditor's closeEvent is triggered.
    closed    = pyqtSignal( int )

    # signal emitted when a user triggers the commit action
    committed = pyqtSignal( int )

    def __init__( self, record, preview_pixmap, window_size=None ):
        """
        Constructs a RecordEditor object representing a record editor window.
        The window is not shown or explicitly positioned prior to the
        constructor returning.

        Takes 3 arguments:

          record          - Record object that will be edited by the window.
                            Must contain an "id" field.
          preview_pixmap  - QPixmap of the photograph that the record is
                            associated with.
          window_size     - Optional tuple of (width, height) in pixels
                            specifying the RecordEditor's window's size.  If
                            omitted, the window will be big enough to hold its
                            contents.

        Returns 1 value:

          self - The newly created RecordEditor object.

        """

        self.record          = record
        self.preview_pixmap  = preview_pixmap

        super().__init__( window_size )

    def commit_record( self ):
        """
        Updates the RecordEditor's internal record with user selected values
        before invoking the parent class' method.

        Takes no arguments.

        Returns nothing.
        """
        # notify any listeners of the ID of the record committed.
        self.committed.emit( self.record["id"] )

    def closeEvent( self, event ):
        """
        Handles closing the window by calling the callback specified at window
        creation.

        Takes 1 argument:

          event - QCloseEvent used to accept or reject the close event.

        Returns nothing.
        """
        # notify any listeners that this RecordEditor has been closed.
        self.closed.emit( self.record["id"] )

# XXX: refactor into widgets.py?
class SelectionView( QTableView ):
    """

    """
    def __init__( self, parent=None ):
        """

        """
        super().__init__( parent )

        self.setSelectionBehavior( QAbstractItemView.SelectRows )
        self.setSelectionMode( QAbstractItemView.SingleSelection )
        self.setEditTriggers( QAbstractItemView.NoEditTriggers )
        self.setAlternatingRowColors( True )
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize( self.verticalHeader().fontMetrics().height() + 2 )
        self.setSortingEnabled( True )

        # prevent the users from rearranging the columns.
        self.horizontalHeader().setSectionsMovable( False )

        # have the last column fill the remaining space of the table
        # XXX: for some reason in ArtRecordViewer this doesn't take
        #      until you manually adjust the horizontal header,
        #      another weird QMainWindow side effect?
        self.horizontalHeader().setStretchLastSection( True )

    def sizeHint( self ):
        """
        Provides a size suitable for viewing the table with all its columns
        resized to their contents.

        Takes no arguments.

        Return 1 value:

          QSize - containing the suggested width and height.

        """
        default = super().sizeHint()

        if self.model():
            self.resizeColumnsToContents()

            width = self.horizontalHeader().length()

            if self.verticalScrollBar().isVisible():
                width += self.verticalScrollBar().width()

            width += self.frameWidth() * 2

            # add some padding to ensure horizontal scroll bar
            # doesn't appear by default.
            # XXX: need to figure out why this is needed when
            #      setLastSectionStretch is True
            width += 7

            return QSize( max( width, default.width() ), default.height() )
        else:
            return default

class PhotoRecordViewer( RecordWindow ):
    """
    """

    # identifiers for columns in selection model.
    ID_COLUMN = 0
    PATH_COLUMN = 1
    STATE_COLUMN = 2
    NUM_COLUMNS = 3

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
        super().__init__( window_size=QSize( 1024, 768 ) )

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
        self.photosModel = QStandardItemModel( len(self.photos), self.NUM_COLUMNS, self )

        self.photosModel.setHeaderData( self.ID_COLUMN, Qt.Horizontal, "Photo ID" )
        self.photosModel.setHeaderData( self.PATH_COLUMN, Qt.Horizontal, "File Path" )
        self.photosModel.setHeaderData( self.STATE_COLUMN, Qt.Horizontal, "State" )

        # walk through each of the photo records and insert a new item at the
        # beginning of the model's list.
        for index, photo in enumerate(self.photos):
            id_item       = QStandardItem( photo["id"] )
            filename_item = QStandardItem( photo["filename"] )
            state_item    = QStandardItem( photo["state"] )

            id_item.setData( int( photo["id"] ) )
            filename_item.setData( photo["filename"] )
            state_item.setData( photo["state"] )

            self.photosModel.setItem( index, self.ID_COLUMN, id_item )
            self.photosModel.setItem( index, self.PATH_COLUMN, filename_item )
            self.photosModel.setItem( index, self.STATE_COLUMN, state_item )

        # create the proxy model for filtering our data based on record
        # processing state.
        self.proxyPhotosModel = QSortFilterProxyModel()
        self.proxyPhotosModel.setFilterKeyColumn( self.STATE_COLUMN )
        self.proxyPhotosModel.setSourceModel( self.photosModel )

    def create_widgets( self ):
        """
        Creates the widgets needed for a PhotoRecordViewer.

        This will be invoked after model creation and prior to widget layout
        (see create_model() and create_layout()).

        Takes no arguments.

        Returns nothing.
        """

        self.selectionView = SelectionView()
        self.selectionView.setModel( self.proxyPhotosModel )
        self.selectionView.activated.connect( self.selectionActivation )
        self.selectionView.selectionModel().selectionChanged.connect( self.selectionChange )
        self.selectionView.setColumnHidden( self.ID_COLUMN, True ) # hide the ID

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

        # dock widget which will hold the selection layout once created
        # in create_layout, for now it gets an empty widget.
        self.selection_dock = QDockWidget()
        self.selection_dock.setFeatures( QDockWidget.DockWidgetMovable )
        self.selection_dock.setWidget( QWidget() )

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

        selection_type_layout = QHBoxLayout()
        selection_type_layout.setContentsMargins( 0, 0, 0, 0 )
        selection_type_layout.setSpacing( 0 )
        selection_type_layout.addWidget( self.selectionBoxLabel )
        selection_type_layout.addWidget( self.selectionBox )
        selection_type_layout.setStretchFactor( self.selectionBox, 1 )

        selection_layout.addLayout( selection_type_layout )
        selection_layout.setStretchFactor( self.selectionView, 1 )

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins( 0, 0, 0, 0 )
        info_layout.setSpacing( 0 )

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

        info_layout.addWidget( self.photoPreview )
        info_layout.addLayout( stats_layout )
        info_layout.setStretchFactor( self.photoPreview, 1 )

        self.centralWidget = QWidget()
        self.centralWidget.setLayout( info_layout )

        self.selection_dock.widget().setLayout( selection_layout )

        self.addDockWidget( Qt.LeftDockWidgetArea, self.selection_dock )

        self.setCentralWidget( self.centralWidget )

    def create_menus( self ):
        """
        Creates the menus for a PhotoRecordViewer.

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
        self.selectionView.setCurrentIndex( self.proxyPhotosModel.index( 0, self.PATH_COLUMN ) )

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
        photo_id = self.photosModel.itemFromIndex( index.sibling( index.row(), self.ID_COLUMN ) ).data()

        return photo_id

    @pyqtSlot( int )
    def remove_photo_editor( self, photo_id ):
        """
        Slot invoked when a spawned PhotoRecordEditor is closed by the user.
        The corresponding entry in the tracking dictionary is removed.

        Takes 1 argument.

          photo_id - ID corresponding to the photo in the now closed
                     PhotoRecordEditor.

        Returns nothing.
        """

        print( "Removing photo ID={:d} from the edit list.".format( photo_id ) )
        self.photo_record_editors.pop( photo_id, None )

    @pyqtSlot( int )
    def refresh_photo_record( self, photo_id ):
        """
        Slot invoked when a photo record has been committed in a
        PhotoRecordEditor and whose state needs to be refreshed within
        our model.

        Takes 1 argument.

          photo_id - ID corresponding to the photo just committed.

        Returns nothing.
        """

        # update the model's information about this record's state.
        for photo in self.photos:
            if photo["id"] == photo_id:
                # find this record in the model by it's photo identifier
                # (there can, and will, only be one) and update it's
                # processing state.
                index = self.photosModel.match( self.photosModel.index( 0, self.ID_COLUMN ),
                                                DATA_ROLE,
                                                photo_id,
                                                1,
                                                Qt.MatchExactly )[0]

                self.photosModel.setData( index.sibling( index.row(), self.STATE_COLUMN ), photo["state"] )
                break

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
            confirmation_dialog.setInformativeText( "Unsaved changes have been made.  "
                                                    "Are you sure you want to exit?" )
            confirmation_dialog.setStandardButtons( QMessageBox.Ok | QMessageBox.Cancel )
            confirmation_dialog.setDefaultButton( QMessageBox.Cancel )

            result = confirmation_dialog.exec_()

            # nothing to do if we were told this was an accident.
            if result == QMessageBox.Cancel:
                event.ignore()
                return

        # time to go away.
        event.accept()

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

                self.photo_record_editors[photo_id] = PhotoRecordEditor( self.db,
                                                                         photo,
                                                                         self.preview_pixmap )

                # call our refresh method when this window commits changes to
                # the record of interest...
                self.photo_record_editors[photo_id].committed.connect( self.refresh_photo_record )

                # ... and cleanup our state when finished editing.
                self.photo_record_editors[photo_id].closed.connect( self.remove_photo_editor )

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
                    pixmap = get_pixmap_from_image( photo["filename"] )

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
                else:
                    pixmap    = QPixmap()

                exif_time = photo["photo_time"]

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

    # identifiers for the columns of our model.
    ID_COLUMN    = 0
    STATE_COLUMN = 1
    NUM_COLUMNS  = 2

    # XXX: review the calling convention.
    def __init__( self, db, photo_record, preview_pixmap ):

        self.db          = db
        self.art_records = db.get_art_records( photo_record["id"] )

        # map tracking the open photo editor windows.  each photo record can
        # only be edited by one window at a time.
        self.art_record_editors = dict()

        super().__init__( photo_record, preview_pixmap, QSize(800, 600) )

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
        self.artModel = QStandardItemModel( len( self.art_records ),
                                            self.NUM_COLUMNS, self )

        self.artModel.setHeaderData( self.ID_COLUMN, Qt.Horizontal, "Art ID" )
        self.artModel.setHeaderData( self.STATE_COLUMN, Qt.Horizontal, "State" )

        # walk through each of the photo records and insert a new item at the
        # beginning of the model's list.
        for index, art in enumerate( self.art_records ):
            id_item = QStandardItem( str( art["id"] ) )
            state_item = QStandardItem( art["state"] )

            id_item.setData( art["id"] )
            state_item.setData( art["state"] )

            self.artModel.setItem( index, self.ID_COLUMN, id_item )
            self.artModel.setItem( index, self.STATE_COLUMN, state_item )

        # create the proxy model for filtering our data based on record
        # processing state.
        self.proxyArtModel = QSortFilterProxyModel()
        self.proxyArtModel.setFilterKeyColumn( self.STATE_COLUMN )
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
        self.selectionView = SelectionView()
        self.selectionView.setModel( self.proxyArtModel )
        self.selectionView.activated.connect( self.selectionActivation )
        self.selectionView.selectionModel().selectionChanged.connect( self.recordSelectionChange )

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

        #   art record creation/deletion buttons.
        record_modification_layout = QHBoxLayout()
        record_modification_layout.setContentsMargins( 0, 0, 0, 0 )
        record_modification_layout.setSpacing( 0 )
        record_modification_layout.addWidget( self.newRecordButton )
        record_modification_layout.addWidget( self.deleteRecordButton )

        selection_layout.addWidget( self.selectionView )
        selection_layout.addLayout( selection_type_layout )
        selection_layout.addLayout( record_modification_layout )
        selection_layout.setStretchFactor( self.selectionView, 1 )

        #   selected art record information and photo record editing widgets.
        info_and_edit_layout = QGridLayout()
        info_and_edit_layout.setContentsMargins( 0, 0, 0, 0 )
        info_and_edit_layout.setSpacing( 0 )

        # XXX: the layout of these labels is *awful*.  need to fix this.
        art_header_label = QLabel( "<b>Art Record:</b>" )
        info_and_edit_layout.addWidget( art_header_label,
                                        0, 0, 1, 4 )

        type_label = QLabel( "Type:" )
        info_and_edit_layout.addWidget( type_label,
                                        1, 0 )
        info_and_edit_layout.addWidget( self.artTypeLabel,
                                        1, 1 )

        size_label = QLabel( "Size:" )
        info_and_edit_layout.addWidget( size_label,
                                        2, 0 )
        info_and_edit_layout.addWidget( self.artSizeLabel,
                                        2, 1 )

        quality_label = QLabel( "Quality:" )
        info_and_edit_layout.addWidget( quality_label,
                                        3, 0 )
        info_and_edit_layout.addWidget( self.artQualityLabel,
                                        3, 1 )

        date_label = QLabel( "Date:" )
        info_and_edit_layout.addWidget( date_label,
                                        4, 0 )
        info_and_edit_layout.addWidget( self.artDateLabel,
                                        4, 1 )

        artists_label = QLabel( "Artists:" )
        info_and_edit_layout.addWidget( artists_label,
                                        1, 2 )
        info_and_edit_layout.addWidget( self.artArtistsLabel,
                                        1, 3 )

        associates_label = QLabel( "Associates:" )
        info_and_edit_layout.addWidget( associates_label,
                                        2, 2 )
        info_and_edit_layout.addWidget( self.artAssociatesLabel,
                                        2, 3 )

        vandals_label = QLabel( "Vandals:" )
        info_and_edit_layout.addWidget( vandals_label,
                                        3, 2 )
        info_and_edit_layout.addWidget( self.artVandalsLabel,
                                        3, 3 )

        tags_label = QLabel( "Tags:" )
        info_and_edit_layout.addWidget( tags_label,
                                        4, 2 )
        info_and_edit_layout.addWidget( self.artTagsLabel,
                                        4, 3 )

        photo_header_label = QLabel( "<b>Photo Record:</b>" )
        info_and_edit_layout.addWidget( photo_header_label,
                                        5, 0, 1, 4 )

        info_and_edit_layout.addWidget( self.photoProcessingStateComboLabel,
                                        6, 0 )
        info_and_edit_layout.addWidget( self.photoProcessingStateComboBox,
                                        6, 1 )

        info_and_edit_layout.addWidget( self.photoTagsLabel,
                                        7, 0 )
        info_and_edit_layout.addWidget( self.photoTagsLineEdit,
                                        7, 1,
                                        1, 3 )

        horizontal_layout.addLayout( selection_layout )
        horizontal_layout.addLayout( info_and_edit_layout )
        horizontal_layout.setStretchFactor( info_and_edit_layout, 1 )

        main_layout.addWidget( self.photoPreview )
        main_layout.setAlignment( self.photoPreview, Qt.AlignCenter ) # the preview should be centered.
        main_layout.addLayout( horizontal_layout )

        self.centralWidget = QWidget()
        self.centralWidget.setLayout( main_layout )

        self.setCentralWidget( self.centralWidget )

    def create_menus( self ):
        """
        Creates the menus for a PhotoRecordEditor.

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
        self.selectionView.setCurrentIndex( self.proxyArtModel.index( 0, self.ID_COLUMN ) )

        # set the processing state combination box to this record's state.
        combo_index = self.photoProcessingStateComboBox.findText( self.record["state"] )
        self.photoProcessingStateComboBox.setCurrentIndex( combo_index )

        self.photoTagsLineEdit.setText( "" if len( self.record["tags"] ) == 0 else ", ".join( self.record["tags"] ) )

    def commit_record( self, update_photo_state=True ):
        """
        Updates the PhotoRecordEditor's internal record with user selected
        values before invoking the parent class' method.

        Takes 1 argument:

          update_photo_state - Optional flag indicating whether the photo
                               record's state should be committed.  If False,
                               the state is not actually committed, but the
                               parent class' method is invoked to signal
                               a change related to the record (e.g. a child
                               art record has been added or removed).  If
                               omitted, defaults to True.

        Returns nothing.
        """

        # update the record based on what's currently visible if requested.
        if update_photo_state:
            self.record["modified_time"] = time.mktime( time.gmtime() )
            self.record["state"]         = self.photoProcessingStateComboBox.currentText()
            self.record["tags"]          = list( map( lambda x: x.strip(),
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
        art_id = self.artModel.itemFromIndex( index.sibling( index.row(), self.ID_COLUMN ) ).data()

        return art_id

    def create_new_record( self ):
        """
        """
        print( "Create a new art record for photo ID {:d}.".format( self.record["id"] ) )

        # create a new record in the database and keep track of it within the
        # editor.
        new_art_record = self.db.new_art_record( self.record["id"] )
        self.art_records.append( new_art_record )

        # add the record into the model so we can see it.
        id_item    = QStandardItem( str( new_art_record["id"] ) )
        state_item = QStandardItem( new_art_record["state"] )

        id_item.setData( new_art_record["id"] )
        state_item.setData( new_art_record["state"] )

        self.artModel.appendRow( [id_item, state_item] )

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
        index = self.artModel.match( self.artModel.index( 0, self.ID_COLUMN ),
                                     DATA_ROLE,
                                     art_id,
                                     1,
                                     Qt.MatchExactly )[0]
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

                self.art_record_editors[art_id] = ArtRecordEditor( self.db,
                                                                   self.record["id"],
                                                                   art,
                                                                   self.preview_pixmap )

                # call our refresh method when this window commits changes to
                # the record of interest...
                self.art_record_editors[art_id].committed.connect( self.refresh_art_record )

                # ... and cleanup our state when finished editing.
                self.art_record_editors[art_id].closed.connect( self.remove_art_editor )

                self.art_record_editors[art_id].show()
                break

    @pyqtSlot( int )
    def remove_art_editor( self, art_id ):
        """
        Slot invoked when a spawned ArtRecordEditor is closed by ther user.
        The corresponding entry in the tracking dictionary is removed.

        Takes 1 argument.

          art_id - ID corresponding to the art in the now closed
                   ArtRecordEditor.

        Returns nothing.
        """

        print( "Removing art ID={:d} from the edit list.".format( art_id ) )
        self.art_record_editors.pop( art_id, None )

    @pyqtSlot( int )
    def refresh_art_record( self, art_id ):
        """
        Slot invoked when an art record has been committed in an
        ArtRecordEditor and whose state needs to be refreshed within
        our model.

        Takes 1 argument.

          art_id - ID corresponding to the art record just committed.

        Returns nothing.
        """

        print( "Need to refresh art record #{:d}.".format( art_id ) )

        # XXX: factor this into a separate routine
        for art in self.art_records:
            if art["id"] == art_id:
                # find this record in the model by it's art identifier (there
                # can, and will, only be one) and update it's processing
                # state.
                index = self.artModel.match( self.artModel.index( 0, self.ID_COLUMN ),
                                             DATA_ROLE,
                                             art_id,
                                             1,
                                             Qt.MatchExactly )[0]

                self.artModel.setData( index.sibling( index.row(), self.STATE_COLUMN ),
                                       art["state"] )

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
        self.artTypeLabel.setText( record["type"] )
        self.artSizeLabel.setText( record["size"] )
        self.artQualityLabel.setText( record["quality"] )
        self.artDateLabel.setText( record["date"] )
        self.artArtistsLabel.setText( ", ".join( record["artists"] ) )
        self.artAssociatesLabel.setText( ", ".join( record["associates"] ) )
        self.artVandalsLabel.setText( ", ".join( record["vandals"] ) )
        self.artTagsLabel.setText( ", ".join( record["tags"] ) )

    def recordSelectionChange( self, selected, deselected ):
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

        # make sure we emit our closed signal.
        super().closeEvent(event)

        # time to go away.
        event.accept()

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
    def __init__( self, db, photo_id, art_record, preview_pixmap ):

        self.db             = db
        self.photo_id       = photo_id

        # XXX: we only keep this around until we fix our resizing pixmap situation
        #      and can initialize it with an existing pixmap (preview_pixmap).
        self.photo_record   = self.db.get_photo_records( photo_id )
        print( "Photo record [{}]: {}".format( self.photo_id, self.photo_record ) )

        super().__init__( art_record, preview_pixmap, QSize(800, 600) )

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

        #   vertical layout of the photo preview and everything else.
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins( 0, 0, 0, 0 )
        main_layout.setSpacing( 0 )

        main_layout.addWidget( self.photoPreview )
        main_layout.setAlignment( self.photoPreview, Qt.AlignCenter ) # the preview should be centered.
        main_layout.addLayout( editing_layout )
        main_layout.setStretchFactor( self.photoPreview, 1 )

        self.centralWidget = QGroupBox()
        self.centralWidget.setLayout( main_layout )

        self.setCentralWidget( self.centralWidget )

    def create_menus( self ):
        """
        Creates the menus for an ArtRecordEditor.

        Takes no arguments.

        Returns nothing.
        """
        # XXX: for whatever reason, closing the window via menu action
        # when there are more than two QMainWindow instances causes
        # a hard crash. Left in for now since shortcut works fine,
        # but a refactor is necessary to get Record/Art viewer to be
        # QWidget decendents, rather than QMainWindow.
        self.closeAct  = QAction( "C&lose", self, shortcut="Ctrl+W",
                                   triggered=self.close )

        self.commitAct = QAction( "&Commit", self, shortcut="Ctrl+S",
                                  triggered=self.commit_record )

        self.windowMenu = QMenu( "&Window", self )
        self.windowMenu.addAction( self.commitAct )
        self.windowMenu.addAction( self.closeAct )

        self.newArtistAct = QAction( "New &Artist", self, shortcut="Ctrl+A",
                                     triggered=self.new_artist )
        self.databaseMenu = QMenu( "&Database", self )
        self.databaseMenu.addAction( self.newArtistAct )

        self.menuBar().addMenu( self.windowMenu )
        self.menuBar().addMenu( self.databaseMenu )

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

        print( "Committing art record #{:d}.".format( self.record["id"] ) )

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

    def new_artist( self ):
        """
        Prompts the user for a new artist name and inserts it into the
        database.  If the new artist does not already exist in the database
        it is inserted into the artists model.

        Takes no arguments.

        Returns nothing.

        """

        artist_name_dialog = LineEditDialog( "Artist name:",
                                             "New Artist Input" )
        result             = artist_name_dialog.exec_()

        # nothing to do if we were told this was an accident.
        if result == LineEditDialog.CANCELLED:
            print( "Cancelled" )
            return

        new_artist = artist_name_dialog.artist_edit.text().strip()

        if len( new_artist ) == 0:
            print( "No artist was supplied.  Ignoring." )
            return

        # see if this artist already exists in the database.
        try:
            self.db.new_artist( new_artist )
        except NameError:
            # XXX: better way to convey this
            print( "'{:s}' is already in the database.".format( new_artist ) )
            return

        # identify the new artist's position within the database's list and
        # update model to match.
        artists_list     = self.db.get_artists()
        new_artist_index = artists_list.index( new_artist )

        self.artistsModel.insertRow( new_artist_index )
        self.artistsModel.setData( self.artistsModel.index( new_artist_index ),
                                   new_artist )

    def closeEvent( self, event ):
        """
        """

        # make sure our closed signal is emitted.
        super().closeEvent( event )

        event.accept()

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
