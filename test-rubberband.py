#!/usr/bin/env python

# Tests out the GraffitiAnalysis package's widgets module's rubberbanded
# pixmap widget.  This constructs a main window that displays an image with a
# rubberband on it and a button that prints the region's geometry when
# clicked.
#
# Original code and idea came from here though was here:
#
#   https://stackoverflow.com/questions/19066804/implementing-resize-handles-on-qrubberband-is-qsizegrip-relevant
#
# With a full project here:
#
#   https://gist.github.com/Riateche/6743108
#
# Though was ada

from GraffitiAnalysis.widgets import RubberBandedResizingPixmap

from PyQt5.QtWidgets import ( QApplication, QGroupBox, QLabel, QMainWindow,
                              QPushButton, QVBoxLayout )

class MainWindow( QMainWindow ):
    def __init__( self, filename=None ):
        super().__init__()

        if filename is None:
            filename = "images/P9400919.JPG"

        main_box    = QGroupBox()
        main_box.setStyleSheet( "border: 1px solid red" )

        main_layout = QVBoxLayout( main_box )
        main_layout.addWidget( QLabel( "Above" ) )

        pixmap = RubberBandedResizingPixmap( filename )
        self.banded_region = pixmap.get_banded_region()
        main_layout.addWidget( pixmap )

        button = QPushButton( "Coordinates" )
        button.clicked.connect( self.print_coordinates )
        main_layout.addWidget( button )

        self.setCentralWidget( main_box )
        self.setWindowTitle( "Rubberband Box Test" )

    def print_coordinates( self ):
        print( "Region at {} sized {}.".format( self.banded_region.pos(),
                                                self.banded_region.geometry() ) )


if __name__ == '__main__':
    import sys

    app = QApplication( sys.argv )

    if len( sys.argv ) > 1:
        filename = sys.argv[1]
    else:
        filename = None

    main_window = MainWindow( filename )
    main_window.show()
    sys.exit( app.exec_() )
