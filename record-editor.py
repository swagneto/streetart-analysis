#!/usr/bin/env python

# Todo:
#
#   * X'ing out of art record editor doesn't do the cleanup?
#   * sort the contents of the treeview
#   ~ tree view columns need to be sized properly
#   * relative sizing of stats box labels needs to be sized properly (and not
#     encroach on the selection view)
#   x focus needs to be on the treeview initially
#   * factoring out the code in PhotoRecordViewer.__init__()
#      * need constants for the treeview columns
#   * description label for information
#   * tab order for art record editor
#   * commiting a record -> update the status indicating it happend
#   * default rubberband box is too big in art editor
#   * rubberbands need to be slaved to their parents to be resized properly
#   * region coordinates need to be normalized to dimensions

from functools import lru_cache, partial
import time

from PyQt5.QtCore import Qt, QRect, QRegExp, QSize, QSortFilterProxyModel, QStringListModel
from PyQt5.QtGui import QImage, QPalette, QPixmap, QStandardItemModel
from PyQt5.QtWidgets import ( QAbstractItemView, QAction, QApplication,
                              QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
                              QHeaderView, QLabel, QLineEdit, QListView,
                              QMainWindow, QMenu, QMessageBox, QPushButton,
                              QRubberBand, QScrollArea, QSizePolicy, QSpacerItem,
                              QTreeView, QVBoxLayout )

import GraffitiAnalysis.database as grafdb
import GraffitiAnalysis.widgets as grafwidgets

class PhotoRecordViewer( QMainWindow ):
    def __init__( self ):
        """
        Main window constructor.
        """

        super().__init__()

        # set the state for the window.
        self.db     = grafdb.Database( None )
        self.photos = self.db.get_photo_records()

        # map keeping track of the open photo editor windows.  each photo
        # record can only be edited by one window at a time.
        self.photo_record_editors = dict()

        ################## create models ################

        # create a model of our photo records.
        #
        # NOTE: we keep photo id in the model so we can pull it from our
        #       selection and access the record's data.
        photos_model = QStandardItemModel( 0, 3, self )

        photos_model.setHeaderData( 0, Qt.Horizontal, "Photo ID" )
        photos_model.setHeaderData( 1, Qt.Horizontal, "File Path" )
        photos_model.setHeaderData( 2, Qt.Horizontal, "State" )

        # walk through each of the photo records and insert a new item at the
        # beginning of the model's list.
        for photo in self.photos:
            photos_model.insertRow( 0 )
            photos_model.setData( photos_model.index( 0, 0 ), photo["id"] )
            photos_model.setData( photos_model.index( 0, 1 ), photo["filename"] )
            photos_model.setData( photos_model.index( 0, 2 ), photo["state"] )

        self.photosModel = photos_model

        # create the proxy model for filtering our data based on record state
        proxy_model = QSortFilterProxyModel()
        proxy_model.setFilterKeyColumn( 2 )
        proxy_model.setSourceModel( photos_model )
        self.proxyPhotosModel = proxy_model

        #############################

        ###################### create widgets ########################

        # XXX: factor these
        selection_view     = QTreeView()
        self.selectionView = selection_view
        selection_view.setModel( proxy_model )
        selection_view.activated.connect( self.selectionActivation )
        selection_view.selectionModel().selectionChanged.connect( self.selectionChange )
        selection_view.setEditTriggers( QAbstractItemView.NoEditTriggers )
        selection_view.setAlternatingRowColors( True )
        selection_view.setColumnHidden( 0, True ) # hide the ID
        selection_view.setSizePolicy( QSizePolicy.Preferred, QSizePolicy.Preferred )
        selection_view.setSortingEnabled( True )
        selection_view.resizeColumnToContents( 1 )

        # configure the column headers.
        # XXX: these don't quite work.  stretching the last section prevents the
        #      columns from resizing at the user's request (which would be fine)
        #      though the default size is wonky.
        #
        #      specifying QHeaderView.{Stretch,ResizeToContents} disables any
        #      interactive or programmatic modification of the column sizes.
        #
#        selection_view.header().setStretchLastSection( True ) # have the state column fill space - XXX not quite what we want
#        selection_view.header().setSectionResizeMode( 0, QHeaderView.Stretch )
#        selection_view.header().setSectionResizeMode( 1, QHeaderView.ResizeToContents )
#        selection_view.header().setSectionResizeMode( 2, QHeaderView.Stretch )

#        self.selectionView.setAllColumnsShowFocus( True )
 #       self.selectionView.keyPressEvent = self.keyPressEvent # XXX: don't do this, it eats keys

        # prevent the users from rearranging the columns.
        selection_view.header().setSectionsMovable( False )

        selection_box     = QComboBox()
        self.selectionBox = selection_box

        selection_box.addItem( "all", "all" )
        for state in self.db.get_processing_states():
            selection_box.addItem( state, state )

        selection_box.activated.connect( self.selectionTypeActivation )

        selection_box_label = QLabel( "&Processing Type:" )
        selection_box_label.setBuddy( selection_box )

        photo_preview     = QLabel()
        self.photoPreview = photo_preview

        photo_preview.setBackgroundRole( QPalette.Base )
        # XXX: why is a preferred size policy with a minimum size better than
        #      ignored with minimum?  the latter causes the image to overflow into
        #      the label area and hide it unless the window is resized.
        photo_preview.setSizePolicy( QSizePolicy.Preferred, QSizePolicy.Preferred )
        photo_preview.setScaledContents( True )
        photo_preview.setMinimumSize( 400, 300 )

        # XXX: change these defaults
        self.infoStateLabel      = QLabel()
        self.infoLocationLabel   = QLabel()
        self.infoAddressLabel    = QLabel()
        self.infoResolutionLabel = QLabel()
        self.infoCreatedLabel    = QLabel()
        self.infoModifiedLabel   = QLabel()
        self.infoTagsLabel       = QLabel()

        self.infoStateLabel.setStyleSheet( "border: 2px solid black" )

        # select the first entry.
        #
        # NOTE: we have to do this after all widgets are created, otherwise
        #       we are likely to crash.
        #
        # XXX: if this is commented out
        #selection_view.setCurrentIndex( proxy_model.index( 0, 0 ) )
        #self.selectionView.setFocus( True )

        ##################### lay widgets out ######################

        # create layout
        selection_layout = QVBoxLayout()
        selection_layout.setContentsMargins( 0, 0, 0, 0 )
        selection_layout.setSpacing( 0 )

        selection_layout.addWidget( selection_view )

        # XXX: don't need to be stored as global state
        self.recordSelectionBox = QGroupBox()
        self.recordSelectionBox.setLayout( selection_layout )
        self.recordSelectionBox.setStyleSheet( "border: 2px solid black" )

        selection_type_layout = QHBoxLayout()
        selection_type_layout.setContentsMargins( 0, 0, 0, 0 )
        selection_type_layout.setSpacing( 0 )
        selection_type_layout.addWidget( selection_box_label )
        selection_type_layout.addWidget( selection_box )
        selection_type_box = QGroupBox()
        selection_type_box.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed ) # reduces the space needed.
        selection_type_box.setLayout( selection_type_layout )

        selection_layout.addWidget( selection_type_box )

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins( 0, 0, 0, 0 )
        info_layout.setSpacing( 0 )

        self.recordInformationBox = QGroupBox()
        self.recordInformationBox.setLayout( info_layout )
        self.recordInformationBox.setStyleSheet( "border: 2px solid black" )

        stats_box    = QGroupBox()
        stats_layout = QGridLayout()
        stats_layout.setContentsMargins( 0, 0, 0, 0 )
        stats_layout.setSpacing( 0 )

        stats_layout.addWidget( QLabel( "State:" ), 0, 0 )
        stats_layout.addWidget( self.infoStateLabel, 0, 1 )

        stats_layout.addWidget( QLabel( "Location:" ), 1, 0 )
        stats_layout.addWidget( self.infoLocationLabel, 1, 1 )

        stats_layout.addWidget( QLabel( "Address:" ), 2, 0 )
        stats_layout.addWidget( self.infoAddressLabel, 2, 1 )

        stats_layout.addWidget( QLabel( "Resolution:" ), 3, 0 )
        stats_layout.addWidget( self.infoResolutionLabel, 3, 1 )

        stats_layout.addWidget( QLabel( "Created:" ), 4, 0 )
        stats_layout.addWidget( self.infoCreatedLabel, 4, 1 )

        stats_layout.addWidget( QLabel( "Modified:" ), 5, 0 )
        stats_layout.addWidget( self.infoModifiedLabel, 5, 1 )

        stats_layout.addWidget( QLabel( "Tags:" ), 6, 0 )
        stats_layout.addWidget( self.infoTagsLabel, 6, 1 )

        stats_box.setLayout( stats_layout )

        info_layout.addWidget( photo_preview )
        info_layout.addWidget( stats_box )

        ###############################


        main_layout = QHBoxLayout()
        main_layout.addWidget( self.recordSelectionBox )
        main_layout.addWidget( self.recordInformationBox )
        main_layout.setContentsMargins( 0, 0, 0, 0 )
        main_layout.setSpacing( 0 )

        main_box = QGroupBox()
        main_box.setLayout( main_layout )

        self.setCentralWidget( main_box )

        self.createActions()
        self.createMenus()

        self.setWindowTitle( "Photo Record Editor" )
        self.resize( 800, 600 )

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

        photo_record = self.db.get_photo_records( [photo_id] )[0]

        print( photo_record["filename"] )
        print( photo_record["id"] )
        print( photo_record["resolution"] )
        print( photo_record["state"] )
        print( "{:s} ({:d}): ({:d}, {:d}) [{:s}]".format( photo_record["filename"],
                                                          photo_record["id"],
                                                          *photo_record["resolution"],
                                                          photo_record["state"] ) )

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
            #      minimized or hidden?
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
                self.infoLocationLabel.setText( "({:f}, {:f})".format( *photo["location"] ) )
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

    def createActions( self ):
        self.exitAct = QAction( "E&xit", self, shortcut="Ctrl+Q",
                                triggered=self.close )

        self.aboutAct = QAction( "&About", self, triggered=self.about )

        self.aboutQtAct = QAction( "About &Qt", self,
                                   triggered=QApplication.instance().aboutQt )

    def createMenus( self ):
        self.fileMenu = QMenu( "&File", self )
        self.fileMenu.addAction( self.exitAct )

        self.helpMenu = QMenu( "&Help", self )
        self.helpMenu.addAction( self.aboutAct )
        self.helpMenu.addAction( self.aboutQtAct )

        self.menuBar().addMenu( self.fileMenu )
        self.menuBar().addMenu( self.helpMenu )

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

class PhotoRecordEditor( QMainWindow ):
    """
    """

    def __init__( self, db, photo_record, close_callback=None, commit_callback=None ):
        """
        """

        super().__init__()

        # track our state.
        self.db                = db
        self.photo_record      = photo_record

        self.close_callback    = close_callback
        self.commit_callback   = commit_callback

        self.art_records       = db.get_art_records( photo_record["id"] )

        self.art_regions       = dict()

        # map keeping track of the open photo editor windows.  each photo
        # record can only be edited by one window at a time.
        self.art_record_editors = dict()

        ################## create models ################

        # create a model of our photo's art records.
        #
        # NOTE: we keep art id in the model so we can pull it from our
        #       selection and access the record's data.
        art_model = QStandardItemModel( 0, 2, self )

        art_model.setHeaderData( 0, Qt.Horizontal, "Art ID" )
        art_model.setHeaderData( 1, Qt.Horizontal, "State" )

        # walk through each of the photo records and insert a new item at the
        # beginning of the model's list.
        for art in self.art_records:
            art_model.insertRow( 0 )
            art_model.setData( art_model.index( 0, 0 ), art["id"] )
            art_model.setData( art_model.index( 0, 1 ), art["state"] )

        self.artModel = art_model

        # create the proxy model for filtering our data based on record state
        proxy_model = QSortFilterProxyModel()
        proxy_model.setFilterKeyColumn( 1 )
        proxy_model.setSourceModel( art_model )
        self.proxyArtModel = proxy_model

        # create our widgets.

        #    photo preview.
        pixmap = get_pixmap_from_image( photo_record["filename"] )
        self.photoPreview = QLabel()
        self.photoPreview.setPixmap( pixmap.scaled( 600, 450, Qt.KeepAspectRatio ) )

        # draw the art record regions.
        for art in self.art_records:
            if art["region"] is not None:
                geometry = art["region"]
                size     = (geometry[2] - geometry[0] + 1,
                            geometry[3] - geometry[1] + 1)
                rubber_band = QRubberBand( QRubberBand.Rectangle, self.photoPreview )

                rubber_band.move( geometry[0], geometry[1] )
                rubber_band.resize( size[0], size[1] )
                rubber_band.show()

                self.art_regions[art["id"]] = rubber_band

        #    processing type.
        selection_box     = QComboBox()
        self.selectionBox = selection_box

        selection_box.addItem( "all", "all" )
        for state in self.db.get_processing_states():
            selection_box.addItem( state, state )

        selection_box.activated.connect( self.selectionTypeActivation )

        selection_box_label = QLabel( "&Processing Type:" )
        selection_box_label.setBuddy( selection_box )

        selection_view     = QTreeView()
        self.selectionView = selection_view
        selection_view.setModel( proxy_model )
        selection_view.activated.connect( self.selectionActivation )
        selection_view.selectionModel().selectionChanged.connect( self.selectionChange )
        selection_view.setEditTriggers( QAbstractItemView.NoEditTriggers )
        selection_view.setAlternatingRowColors( True )
        selection_view.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed )
        selection_view.setSortingEnabled( True )
        selection_view.header().setSectionsMovable( False )

        # XXX: need to add
        #
        #  * photo record state combo box
        #  * tag editor
        #  * description

        # create our layouts.

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
        selection_type_layout.addWidget( selection_box_label )
        selection_type_layout.addWidget( selection_box )
        selection_type_box = QGroupBox()
        selection_type_box.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed ) # reduces the space needed.
        selection_type_box.setLayout( selection_type_layout )

        #   record addition and removal buttons.
        new_record_button = QPushButton( "&New Record" )
        new_record_button.clicked.connect( self.create_new_record )
        delete_record_button = QPushButton( "&Delete Record" )
        delete_record_button.clicked.connect( self.delete_record )
        delete_record_button.setEnabled( False )
        self.deleteRecordButton = delete_record_button

        record_modification_layout = QHBoxLayout()
        record_modification_layout.setContentsMargins( 0, 0, 0, 0 )
        record_modification_layout.setSpacing( 0 )
        record_modification_layout.addWidget( new_record_button )
        record_modification_layout.addWidget( delete_record_button )

        record_modification_box = QGroupBox()
        record_modification_box.setLayout( record_modification_layout )
        record_modification_box.setSizePolicy( QSizePolicy.Fixed, QSizePolicy.Fixed ) # reduces the space needed.

        selection_layout.addWidget( selection_view )
        selection_layout.addWidget( selection_type_box )
        selection_layout.addWidget( record_modification_box )

        selection_box = QGroupBox()
        selection_box.setLayout( selection_layout )
        selection_box.setStyleSheet( "border: 2px solid black" )

        horizontal_layout.addWidget( selection_box )

        horizontal_box = QGroupBox()
        horizontal_box.setLayout( horizontal_layout )

        main_layout.addWidget( self.photoPreview )
        main_layout.setAlignment( self.photoPreview, Qt.AlignCenter ) # the preview should be centered.
        main_layout.addWidget( horizontal_box )

        main_box = QGroupBox()
        main_box.setLayout( main_layout )

        # create the menu bars.
        self.createActions()
        self.createMenus()

        # wire up our window contents, set a title, and an initial size.
        self.setCentralWidget( main_box )
        self.setWindowTitle( "Photo Record Editor: {:s} [{:d}]".format( photo_record["filename"],
                                                                        photo_record["id"] ) )
        self.resize( 800, 600 )

    def createActions( self ):
        self.closeAct = QAction( "&Close", self, shortcut="Ctrl+W",
                                 triggered=self.close )

        self.commitAct = QAction( "&Commit", self, shortcut="Ctrl+S",
                                  triggered=self.commitRecord )

    def createMenus( self ):
        self.windowMenu = QMenu( "&Window", self )
        self.windowMenu.addAction( self.commitAct )
        self.windowMenu.addAction( self.closeAct )

        self.menuBar().addMenu( self.windowMenu )

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
        print( "Create a new art record for photo ID {:d}.".format( self.photo_record["id"] ) )

    def delete_record( self ):
        """
        """

        art_id = self.get_art_id_from_selection()

        print( "Deleting art record #{:d}.".format( art_id ) )

    def remove_art_editor( self, art_id ):

        print( "Removing art ID={:d} from the edit list.".format( art_id ) )
        self.art_record_editors.pop( art_id, None )

    def refresh_art_record( self, art_id ):
        print( "Need to refresh art record #{:d}.".format( art_id ) )

        for art in self.art_records:
            if art["id"] == art_id:
                if art["region"] is not None:
                    # remove an existing rubber band associated with this record if
                    # we have one.
                    if art["id"] in self.art_regions:
                        self.art_regions[art["id"]].hide()
                        # XXX: do we need to delete this?

                    # pull our normalized geometry.  note that this is a tuple rather
                    # than a QRect()/QRectF() object.
                    normalized_geometry = art["region"]

                    pixmap_size = self.photoPreview.pixmap().size()

                    # map our normalized geometry to our pixmap's dimensions.
                    geometry = QRect( round( normalized_geometry[0] * pixmap_size.width() ),
                                      round( normalized_geometry[1] * pixmap_size.height() ),
                                      round( normalized_geometry[2] * pixmap_size.width() ),
                                      round( normalized_geometry[3] * pixmap_size.height() ) )

                    rubber_band = QRubberBand( QRubberBand.Rectangle, self.photoPreview )
                    rubber_band.setGeometry( geometry )
                    rubber_band.show()

                    self.art_regions[art["id"]] = rubber_band

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

    def selectionActivation( self ):
        """
        """

        # XXX: we can still receive a double click even if there isn't a selection
        #      select something, then ctrl-click it within the window...

        art_id = self.get_art_id_from_selection()

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
                                                                   self.photo_record,
                                                                   art,
                                                                   close_callback,
                                                                   commit_callback )
                self.art_record_editors[art_id].show()
                break

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

    def selectionChange( self, selected, deselected ):
        """
        """

        # we're not interested in deselection events.  these occur when the
        # user control clicks a selected entry and when the the proxy model
        # filters out the previously visible selection.
        print( "Handle the deselection case properly when we have art record regions" )

        if len( selected.indexes() ) == 0:
            # nothing is selected, so we can't delete anything.
            self.deleteRecordButton.setEnabled( False )
            return
        else:
            self.deleteRecordButton.setEnabled( True )

        art_id = self.get_art_id_from_selection()

        print( "Preview art record #{:d}.".format( art_id ) )

        #self.preview_photo_record( photo_id )

    def closeEvent( self, event ):
        """
        Handles closing the window by calling the callback specified at window
        creation.
        """

        # run our callback if we have one.
        if self.close_callback is not None:
            self.close_callback()

    def commitRecord( self ):
        """
        """

        # update the record based on what's currently visible.
        print( "XXX: do this" )

        print( "Commiting photo record #{:d}.".format( self.photo_record["id"] ) )

        # run our callback if we have one.
        if self.commit_callback is not None:
            self.commit_callback()

class ArtRecordEditor( QMainWindow ):
    """
    """

    def __init__( self, db, photo_record, art_record, close_callback=None, commit_callback=None ):
        """
        """

        super().__init__()

        # track our state.
        self.db                = db
        self.photo_record      = photo_record
        self.art_record        = art_record
        self.close_callback    = close_callback
        self.commit_callback   = commit_callback

        # create our artists model.
        artists_model = QStringListModel( db.get_artists(), self )
        self.artistsModel = artists_model

        # create our widgets.
        self.setStyleSheet( "border: 1px solid black" )

        #    photo preview.
        self.photoPreview = grafwidgets.RubberBandedResizingPixmap( photo_record["filename"] )
        self.photoPreview.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding ) # reduces the space needed.

        if art_record["region"] is not None:
            region = art_record["region"]
            size   = (region[2] - region[0] + 1,
                      region[3] - region[1] + 1)

            self.photoPreview.banded_region.move( region[0], region[1] )
            self.photoPreview.banded_region.resize( size[0], size[1] )
        else:
            # start the rubberband region covering the entirety of the photo.
            # this provides a sensible default if the user doesn't change it
            # before commiting the record.
            band_thickness = 4

            self.photoPreview.banded_region.resize( self.photoPreview.geometry().width() - band_thickness,
                                                    self.photoPreview.geometry().height() - band_thickness )

        type_combo_box       = QComboBox()
        self.artTypeComboBox = type_combo_box
        for art_type in db.get_art_types():
            type_combo_box.addItem( art_type, art_type )

        type_combo_label     = QLabel( "&Type:" )
        type_combo_label.setBuddy( type_combo_box )

        size_combo_box       = QComboBox()
        self.artSizeComboBox = size_combo_box
        for art_size in db.get_art_sizes():
            size_combo_box.addItem( art_size, art_size )

        size_combo_label     = QLabel( "&Size:" )
        size_combo_label.setBuddy( size_combo_box )

        quality_combo_box       = QComboBox()
        self.artQualityComboBox = quality_combo_box
        for art_quality in db.get_art_qualities():
            quality_combo_box.addItem( art_quality, art_quality )

        quality_combo_label     = QLabel( "&Quality:" )
        quality_combo_label.setBuddy( quality_combo_box )

        date_line_edit       = QLineEdit( "" )
        self.artDateLineEdit = date_line_edit
        date_label           = QLabel( "&Date:" )
        date_label.setBuddy( date_line_edit )

        state_combo_box = QComboBox()
        self.artProcessingStateComboBox = state_combo_box
        for state in db.get_processing_states():
            state_combo_box.addItem( state, state )

        state_combo_label = QLabel( "Stat&e:" )
        state_combo_label.setBuddy( state_combo_box )

        artists_list_view = QListView()
        self.artArtistsListView = artists_list_view
        artists_list_view.setModel( artists_model )
        artists_list_view.setSelectionMode( QAbstractItemView.ExtendedSelection )
        artists_list_view.setEditTriggers( QAbstractItemView.NoEditTriggers )
        artists_list_label = QLabel( "&Artists:" )
        artists_list_label.setBuddy( artists_list_view )

        associates_list_view = QListView()
        self.artAssociatesListView = associates_list_view
        associates_list_view.setModel( artists_model )
        associates_list_view.setSelectionMode( QAbstractItemView.ExtendedSelection )
        associates_list_view.setEditTriggers( QAbstractItemView.NoEditTriggers )
        associates_list_label = QLabel( "Ass&ociates:" )
        associates_list_label.setBuddy( associates_list_view )

        vandals_list_view = QListView()
        self.artVandalsListView = vandals_list_view
        vandals_list_view.setModel( artists_model )
        vandals_list_view.setSelectionMode( QAbstractItemView.ExtendedSelection )
        vandals_list_view.setEditTriggers( QAbstractItemView.NoEditTriggers )
        vandals_list_label = QLabel( "&Vandals:" )
        vandals_list_label.setBuddy( vandals_list_view )

        # create our layouts.
        editing_layout = QGridLayout()
        editing_layout.addWidget( QLabel( "Art Record ID:" ),
                                  0, 0 )
        editing_layout.addWidget( QLabel( "{:d}".format( art_record["id"] ) ),
                                  0, 1 )

        editing_layout.addWidget( type_combo_label,
                                  1, 0 )
        editing_layout.addWidget( self.artTypeComboBox,
                                  1, 1 )

        editing_layout.addWidget( size_combo_label,
                                  2, 0 )
        editing_layout.addWidget( self.artSizeComboBox,
                                  2, 1 )

        editing_layout.addWidget( quality_combo_label,
                                  3, 0 )
        editing_layout.addWidget( self.artQualityComboBox,
                                  3, 1 )

        editing_layout.addWidget( date_label,
                                  4, 0 )
        editing_layout.addWidget( self.artDateLineEdit,
                                  4, 1 )

        editing_layout.addWidget( state_combo_label,
                                  5, 0 )
        editing_layout.addWidget( self.artProcessingStateComboBox,
                                  5, 1 )

        editing_layout.addWidget( artists_list_label,
                                  0, 3 )
        editing_layout.addWidget( artists_list_view,
                                  1, 3,
                                  4, 1 )

        editing_layout.addWidget( associates_list_label,
                                  0, 5 )
        editing_layout.addWidget( associates_list_view,
                                  1, 5,
                                  4, 1 )

        editing_layout.addWidget( vandals_list_label,
                                  0, 7 )
        editing_layout.addWidget( vandals_list_view,
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

        main_box = QGroupBox()
        main_box.setLayout( main_layout )

        # create the menu bars.
        self.createActions()
        self.createMenus()

        # wire up our window contents, set a title, and an initial size.
        self.setCentralWidget( main_box )
        self.setWindowTitle( "Art Record Editor: {:s} [{:d}, {:d}]".format( photo_record["filename"],
                                                                            photo_record["id"],
                                                                            art_record["id"] ) )
        self.resize( 800, 600 )

    def closeEvent( self, event ):
        """
        Handles closing the window by calling the callback specified at window
        creation.
        """

        # run our callback if we have one.
        if self.close_callback is not None:
            self.close_callback()

    def commitRecord( self ):
        """
        """

        # update the record based on what's currently visible.
        self.art_record["type"]          = self.artTypeComboBox.currentText()
        self.art_record["size"]          = self.artSizeComboBox.currentText()
        self.art_record["quality"]       = self.artQualityComboBox.currentText()
        self.art_record["date"]          = self.artDateLineEdit.text()
        self.art_record["state"]         = self.artProcessingStateComboBox.currentText()
        self.art_record["modified_time"] = time.mktime( time.gmtime() )

        self.art_record["artists"]       = [artist.data() for artist in self.artArtistsListView.selectedIndexes()]
        self.art_record["associates"]    = [associate.data() for associate in self.artAssociatesListView.selectedIndexes()]
        self.art_record["vandals"]       = [vandal.data() for vandal in self.artVandalsListView.selectedIndexes()]

        # update the region.
        normalized_geometry = self.photoPreview.get_region_geometry( True )

        self.art_record["region"] = normalized_geometry.getRect()

        print( "Commiting art record #{:d}.".format( self.art_record["id"] ) )

        # run our callback if we have one.
        if self.commit_callback is not None:
            self.commit_callback()

    def createActions( self ):
        self.closeAct = QAction( "C&lose", self, shortcut="Ctrl+W",
                                 triggered=self.close )

        self.commitAct = QAction( "&Commit", self, shortcut="Ctrl+S",
                                  triggered=self.commitRecord )

    def createMenus( self ):
        self.windowMenu = QMenu( "&Window", self )
        self.windowMenu.addAction( self.commitAct )
        self.windowMenu.addAction( self.closeAct )

        self.menuBar().addMenu( self.windowMenu )

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
