from PyQt5 import QtCore, QtWidgets, QtGui
from pygments import highlight
from pygments.lexers import *
from pygments.formatter import Formatter
import json

def hex2QColor(c):
    r=int(c[0:2],16)
    g=int(c[2:4],16)
    b=int(c[4:6],16)
    return QtGui.QColor(r,g,b)
    


class QFormatter(Formatter):
    
    def __init__(self):
        Formatter.__init__(self)
        self.data=[]
        
        # Create a dictionary of text styles, indexed
        # by pygments token names, containing QTextCharFormat
        # instances according to pygments' description
        # of each style
        
        self.styles={}
        for token, style in self.style:
            qtf=QtGui.QTextCharFormat()

            if style['color']:
                qtf.setForeground(hex2QColor(style['color'])) 
            if style['bgcolor']:
                qtf.setBackground(hex2QColor(style['bgcolor'])) 
            if style['bold']:
                qtf.setFontWeight(QtGui.QFont.Bold)
            if style['italic']:
                qtf.setFontItalic(True)
            if style['underline']:
                qtf.setFontUnderline(True)
            self.styles[str(token)]=qtf
    
    def format(self, tokensource, outfile):
        global styles
        # We ignore outfile, keep output in a buffer
        self.data=[]
        
        # Just store a list of styles, one for each character
        # in the input. Obviously a smarter thing with
        # offsets and lengths is a good idea!
        
        for ttype, value in tokensource:
            l=len(value)
            t=str(ttype)                
            self.data.extend([self.styles[t],]*l)


class Highlighter(QtGui.QSyntaxHighlighter):

    def __init__(self, parent, mode):
        QtGui.QSyntaxHighlighter.__init__(self, parent)        
        # Keep the formatter and lexer, initializing them 
        # may be costly.
        self.formatter=QFormatter()
        self.lexer=get_lexer_by_name(mode)
        
    def highlightBlock(self, text):
        """Takes a block, applies format to the document. 
        according to what's in it.
        """
        
        # I need to know where in the document we are,
        # because our formatting info is global to
        # the document
        cb = self.currentBlock()
        p = cb.position()

        # The \n is not really needed, but sometimes  
        # you are in an empty last block, so your position is
        # **after** the end of the document.
        text=self.document().toPlainText()
        
        # Yes, re-highlight the whole document.
        # There **must** be some optimizacion possibilities
        # but it seems fast enough.
        highlight(text,self.lexer,self.formatter)
        
        # Just apply the formatting to this block.
        # For titles, it may be necessary to backtrack
        # and format a couple of blocks **earlier**.
        for i in range(len(text)):
            try:
                self.setFormat(i,1,self.formatter.data[p+i])
            except IndexError:
                pass
        
        # I may need to do something about this being called
        # too quickly.


class LineNumberArea(QtWidgets.QWidget):
    def __init__(self, editor):
        QtWidgets.QWidget.__init__(self, parent=editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QtCore.QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)
        

class Editor(QtWidgets.QPlainTextEdit):
    ARROW_MARKER_NUM = 8
    
    def __init__(self, parent=None):
        super(Editor, self).__init__(parent)
        self.setMinimumWidth(550)
        try:
            font = QtGui.QFont()
            with open('./config.json', 'r') as f:
                config = json.load(f)
            fam = config['font_family']
            fsize = config['font_size']
            
            font.setFamily(fam)
            font.setPointSize(fsize)
            self.setFont(font)
        except:
            pass
        
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    def open_file(self, file_path):
        inFile = QtCore.QFile(file_path)#.absolute())
        if inFile.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
            text = inFile.readAll()
        
            try:
                # Python v3.
                text = str(text, encoding='utf8')
            except TypeError:
                # Python v2.
                text = str(text)
        
            self.setPlainText(text)
            
    def lineNumberAreaPaintEvent(self, event):
        painter = QtGui.QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QtCore.Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber();
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QtCore.Qt.black)
                painter.drawText(0, top, self.lineNumberArea.width(), 
                    self.fontMetrics().height(),
                    QtCore.Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def lineNumberAreaWidth(self):
        digits = len(str(self.blockCount()))
        space = 3 + self.fontMetrics().width('9')*digits
        return space

    def resizeEvent(self, event):
        QtWidgets.QPlainTextEdit.resizeEvent(self, event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    @QtCore.pyqtSlot(int)
    def updateLineNumberAreaWidth(self, newBlockCount):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0);

    @QtCore.pyqtSlot()
    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()
            lineColor = QtGui.QColor(QtCore.Qt.yellow).lighter(160)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    @QtCore.pyqtSlot(QtCore.QRect, int)
    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)


