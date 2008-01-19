"""The qskope script visualizes the structure of PyFFI structures and arrays."""

# ***** BEGIN LICENSE BLOCK *****
#
# Copyright (c) 2007-2008, Python File Format Interface
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials provided
#      with the distribution.
#
#    * Neither the name of the Python File Format Interface
#      project nor the names of its contributors may be used to endorse
#      or promote products derived from this software without specific
#      prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENCE BLOCK *****

from PyQt4 import QtGui, QtCore

from PyFFI.Bases.Basic import BasicBase
from PyFFI.Bases.Struct import StructBase
from PyFFI.Bases.Array import Array

from PyFFI.NIF import NifFormat
from PyFFI.CGF import CgfFormat

# implementation references:
# http://doc.trolltech.com/4.3/model-view-programming.html
# http://doc.trolltech.com/4.3/model-view-model-subclassing.html
class BaseModel(QtCore.QAbstractItemModel):
    """General purpose model for access to data loaded with PyFFI."""
    # column definitions
    NUM_COLUMNS = 3
    COL_TYPE  = 0
    COL_NAME  = 1
    COL_VALUE = 2

    def __init__(self, parent = None, blocks = None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        # this list stores the blocks in the view
        # is a list of NiObjects for the nif format, and a list of Chunks for
        # the cgf format
        self.blocks = blocks

    def flags(self, index):
        if not index.isValid():
            return 0
        return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEnabled
                                   | QtCore.Qt.ItemIsSelectable)

    def data(self, index, role):
        """Return the data of model index in a particular role."""
        # check if the index is valid
        if not index.isValid():
            return QtCore.QVariant()
        # check if the role is supported
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        # get the data for display
        data = index.internalPointer()
        if index.column() == self.COL_NAME:
            return QtCore.QVariant() #(data._name)
        elif index.column() == self.COL_TYPE:
            return QtCore.QVariant(data.__class__.__name__)
        elif index.column() == self.COL_VALUE and isinstance(data, BasicBase):
                return QtCore.QVariant(str(data.getValue()))
        else:
            return QtCore.QVariant()

    def headerData(self, section, orientation, role):
        if (orientation == QtCore.Qt.Horizontal
            and role == QtCore.Qt.DisplayRole):
            if section == self.COL_TYPE:
                return QtCore.QVariant("Type")
            elif section == self.COL_NAME:
                return QtCore.QVariant("Name")
            if section == self.COL_VALUE:
                return QtCore.QVariant("Value")
        return QtCore.QVariant()

    def rowCount(self, parent = QtCore.QModelIndex()):
        if not parent.isValid():
            # top level: one row for each block
            return len(self.blocks)
        else:
            return 0
            ## TODO fix this once parenting works
            # get the parent data
            parentData = parent.internalPointer()
            if isinstance(parentData, StructBase):
                # one row per attribute
                return len(parentData._attributeList)
                # one row per item
            elif isinstance(parentData, Array):
                return len(parentData)

    def columnCount(self, parent = QtCore.QModelIndex()):
        return self.NUM_COLUMNS

    def index(self, row, column, parent):
        """Create an index to item (row, column) of object parent.
        Internal pointers consist of the StructBase or Array instance."""
        # check if we have such index
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        # check if the parent is valid
        if not parent.isValid():
            # parent is not valid, so we need a top-level object
            # return the index with row'th block as internal pointer
            data = self.blocks[row]
        else:
            # parent is valid, so we need to go get the row'th attribute
            # get the parent pointer
            parentData = parent.internalPointer()
            if isinstance(parentData, StructBase):
                data = getattr(parentData,
                               "_%s_value_"
                               % parentData._attributeList[row].name)
            elif isinstance(parentData, Array):
                # get the "raw" list item
                data = list.__getitem__(parentData, row)
        index = self.createIndex(row, column, data)
        return index

    def parent(self, index):
        return QtCore.QModelIndex()

        ## TODO implement _ui functions in BasicBase, StructBase, and Array
        data = index.internalPointer()
        parentData = data._uiGetParent()
        if parentData is None:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(parentData._uiGetRow(), 0, parentData)

if __name__ == "__main__":
    import sys
    global app, model

    stream = open(sys.argv[1], "rb")
    version, user_version = NifFormat.getVersion(stream)
    if version < 0:
        print("not a nif file or version not supported")
        exit
    
    app = QtGui.QApplication(sys.argv)
    view = QtGui.QTreeView()
    model = BaseModel(blocks = NifFormat.read(stream, version, user_version,
                                              rootsonly = False))
    view.setModel(model)
    view.setWindowTitle("QSkope")
    view.show()
    sys.exit(app.exec_())