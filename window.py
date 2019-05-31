import os
import subprocess
import sys

from PyQt5 import QtWidgets, QtCore
from unipath import Path

from dialogs import OpenDialog
from editor import Editor, Highlighter
from preview import Preview, PDFPane
from tree import Tree

import traceback
import json

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        # super(MainWindow, self).__init__(parent)
        if sys.platform == 'darwin':
            # Workaround for Qt issue on OS X that causes QMainWindow to
            # hide when adding QToolBar, see
            # https://bugreports.qt-project.org/browse/QTBUG-4300
            super(MainWindow, self).__init__(
                parent,
                QtCore.Qt.MacWindowToolBarButtonHint
            )
        else:
            super(MainWindow, self).__init__(parent)
        
    def setup_app(self):
        self.setupActions()
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.tree = Tree()
        self.editor = Editor()
        self.highlighter = Highlighter(self.editor.document(), 'rst')
        

        self.tab_widget = QtWidgets.QTabWidget()
        self.preview = Preview()
        self.pdf_pane = PDFPane()
        self.tab_widget.addTab(self.preview, "HTML")
        self.tab_widget.addTab(self.pdf_pane, "PDF")

        self.file_path = None
        self.output_html_path = None

        self.setCentralWidget(splitter)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.editor)

        splitter.addWidget(self.tab_widget)
        
        splitter.setSizes([300, 950, 1350])

        self.setWindowTitle("Sphinx Docs Editor")
        self.createMenus()
        self.createToolBars()
        self.resize(300 + 950 + 1350, 1400)
        
        try:
            with open('./config.json', 'r') as f:
                c = json.load(f)
            path = c['last_folder']
            self.openFolder(path)
        except:
            pass

    def setupActions(self):
        """
            Set up the top menu actions and keyboard shortcuts.
        """

        # File Menu --------------------------------------------------
        self.openAction = QtWidgets.QAction(
            # QtWidgets.QIcon(":/images/open.png"),
            "&Open File",
            self,
            shortcut="Ctrl+O",
            statusTip="Open File",
            triggered=self.openFile
        )

        self.openFolderAction = QtWidgets.QAction(
            # QtWidgets.QIcon(":/images/open.png"),
            "Open Folder",
            self,
            shortcut="Ctrl+Shift+O",
            statusTip="Open Folder",
            triggered=self.openFolder
        )

        self.saveAction = QtWidgets.QAction(
            # QtWidgets.QIcon(":/images/save.png"),
            "&Save File",
            self,
            shortcut="Ctrl+S",
            statusTip="Save File",
            triggered=self.saveFile
        )

        self.saveAsAction = QtWidgets.QAction(
            # QtWidgets.QIcon(":/images/save.png"),
            "Save As File",
            self,
            shortcut="Ctrl+Shift+S",
            statusTip="Save File As...",
            triggered=self.saveFileAs
        )

        self.quitAction = QtWidgets.QAction(
            # QtWidgets.QIcon(':/images/save.png'),
            "&Quit",
            self,
            shortcut="Ctrl+Q",
            statusTip="Quit",
            triggered=self.close
        )

        # Build Menu --------------------------------------------------

        self.buildHTMLAction = QtWidgets.QAction(
            "Build &HTML",
            self,
            shortcut="Ctrl+B",
            statusTip="Build HTML",
            triggered=self.buildHTML
        )

        self.buildPDFAction = QtWidgets.QAction(
            "Build &PDF",
            self,
            shortcut="Ctrl+Shift+B",
            statusTip="Build PDF",
            triggered=self.buildPDF
        )
        self.selectFontAction = QtWidgets.QAction(
            "Select Font", self, triggered=self.openFontDialog
        )

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.openFolderAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.saveAsAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAction)
        self.buildMenu = self.menuBar().addMenu("&Build")
        self.buildMenu.addAction(self.buildHTMLAction)
        self.buildMenu.addAction(self.buildPDFAction)

    def createToolBars(self):
        self.fileToolBar = self.addToolBar("File")
        self.fileToolBar.addAction(self.openAction)
        self.fileToolBar.addAction(self.openFolderAction)
        self.fileToolBar.addAction(self.saveAction)
        self.fileToolBar.addAction(self.selectFontAction)
        # self.fileToolBar.addAction(self.saveAsAction)
        # self.fileToolBar.addAction(self.quitAction)
        self.buildToolBar = self.addToolBar("Build")
        self.buildToolBar.addAction(self.buildHTMLAction)
        self.buildToolBar.addAction(self.buildPDFAction)
        

    def openFile(self, path=None):
        """
            Ask the user to open a file via the Open File dialog.
            Then open it in the tree, editor, and HTML preview windows.
        """
        if not path:
            dialog = OpenDialog()
            dialog.set_folders_only(False)
            path = dialog.getOpenFileName(
                self,
                "Open File",
                '',
                "ReStructuredText Files (*.rst *.txt)"
            )

        if path:
            file_path = Path(path[0])
            filename = file_path.name
            tree_dir = file_path.parent.absolute()
            self.handleFileChanged(tree_dir, filename)

    def saveFile(self):
        if self.file_path:
            text = self.editor.toPlainText()
            try:
                f = open(self.tree.get_current_item_path(), "w")
                f.write(text)
                f.close()
                self.buildHTML()
            except IOError:
                QtWidgets.QMessageBox.information(
                    self,
                    "Unable to open file: %s" % self.file_path.absolute()
                )

    def saveFileAs(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Save File As',
            '',
            "ReStructuredText Files (*.rst *.txt)"
        )
        if filename:
            text = self.editor.toPlainText()
            try:
                f = open(filename, "w")
                f.write(text)
                f.close()
                self.buildHTML()
            except IOError:
                QtWidgets.QMessageBox.information(
                    self,
                    "Unable to open file: %s" % filename
                )

    def openFolder(self, path=None):
        """
            Ask the user to open a folder (directory) via
            the Open Folder dialog. Then open it in the tree,
            editor, and HTML preview windows.
        """
        if not path:
            dialog = OpenDialog()
            dialog.set_folders_only(True)
            path = dialog.getExistingDirectory(self, "Open Folder", '')

        if path:
            self.handleFileChanged(path)#, filename='index.rst')
            with open('./config.json', 'r') as f:
                c = json.load(f)
            c['last_folder'] = path
            with open('./config.json', 'w') as f:
                json.dump(c, f)
    
    def openFontDialog(self):
        font = QtWidgets.QFontDialog.getFont(self.editor.font())
        if font[1]:
            font = font[0]
            font.setFixedPitch(True)
            self.editor.setFont(font)
            with open('./config.json', 'r') as f:
                c = json.load(f)
            c['font_family'] = font.family()
            c['font_size'] = font.pointSize()
            with open('./config.json', 'w') as f:
                json.dump(c, f)

    def handleFileChanged(self, dir, filename=None):
        """
            This is called whenever the active file is changed.
            It sets the tree, editor, and preview panes to the new file.
        """
        if not filename:
            # TODO: find first rst file if index.rst doesn't exist.
            filename = "index.rst"
        self.file_path = Path(dir, filename)
        file_stem = str(self.file_path.stem)
        #html_str = "build/html/{0}.html".format(file_stem)

        #self.output_html_path = Path(dir, html_str).absolute()
        
        # Load the directory containing the file into the tree.
        self.tree.load_from_dir(dir)
        
        if not self.file_path.endswith('.rst'):
            try:
                html_path = os.path.dirname(os.path.relpath(self.tree.get_current_item_path(), dir + '/source'))
                self.output_html_path = "{0}/build/html/{1}/{2}".format(dir, html_path, filename)
                print(self.output_html_path)
                self.preview.load_html(self.output_html_path)
            except:
                print(traceback.format_exc())
            return
        
        # Load the file into the editor
        self.editor.open_file(self.tree.get_current_item_path())
        try:
            html_path = os.path.dirname(os.path.relpath(self.tree.get_current_item_path(), dir + '/source'))
            self.output_html_path = "{0}/build/html/{1}/{2}.html".format(dir, html_path, file_stem)
        except:
            pass
        #print(self.tree.get_current_item_path())
        
        # Load corresponding HTML file from pre-built Sphinx docs
        self.preview.load_html(self.output_html_path)

    def buildHTML(self):
        """
        Builds the .html version of the active file and reloads
        it in the preview pane.
        """

        # TODO: make this configurable via a dialog
        os.chdir(self.file_path.parent)
        proc = subprocess.Popen(
            ["make", "clean"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        for line in proc.stdout:
            print("stdout: " + str(line.rstrip(), encoding='utf8'))
        print('----------------')
        proc = subprocess.Popen(
            ["make", "html"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        proc.wait()
        for line in proc.stdout:
            print("stdout: " + str(line.rstrip(), encoding='utf8'))

        # Load corresponding HTML file from newly-built Sphinx docs
        self.preview.load_html(self.output_html_path)

    def buildPDF(self):
        """
        Builds the .pdf version of the active file.
        """

        # TODO: get this working
        # TODO: make this configurable via a dialog
        os.chdir(self.file_path.parent)
        proc = subprocess.Popen(
            ["make", "latexpdf"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        proc.wait()
        for line in proc.stdout:
            print("stdout: " + line.rstrip())
