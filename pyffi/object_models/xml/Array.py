"""Implements class for arrays."""

# --------------------------------------------------------------------------
# ***** BEGIN LICENSE BLOCK *****
#
# Copyright (c) 2007-2009, Python File Format Interface
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
# ***** END LICENSE BLOCK *****
# --------------------------------------------------------------------------

# note: some imports are defined at the end to avoid problems with circularity

import weakref

from pyffi.utils.graph import DetailNode, EdgeFilter

class _ListWrap(list, DetailNode):
    """A wrapper for list, which uses getValue and setValue for
    getting and setting items of the basic type."""

    def __init__(self, element_type, parent = None):
        self._parent = weakref.ref(parent) if parent else None
        self._elementType = element_type
        # we link to the unbound methods (that is, self.__class__.xxx
        # instead of self.xxx) to avoid circular references!!
        if issubclass(element_type, BasicBase):
            self._getItemHook = self.__class__.getBasicItem
            self._setItemHook = self.__class__.setBasicItem
            self._iterItemHook = self.__class__.iterBasicItem
        else:
            self._getItemHook = self.__class__.getItem
            self._setItemHook = self.__class__._notImplementedHook
            self._iterItemHook = self.__class__.iterItem

    def __getitem__(self, index):
        return self._getItemHook(self, index)

    def __setitem__(self, index, value):
        return self._setItemHook(self, index, value)

    def __iter__(self):
        return self._iterItemHook(self)

    def __contains__(self, value):
        # ensure that the "in" operator uses self.__iter__() rather than
        # list.__iter__()
        for elem in self.__iter__():
            if elem == value:
                return True
        return False

    def _notImplementedHook(self, *args):
        """A hook for members that are not implemented."""
        raise NotImplementedError

    def iterBasicItem(self):
        """Iterator which calls C{getValue()} on all items. Applies when
        the list has BasicBase elements."""
        for elem in list.__iter__(self):
            yield elem.getValue()

    def iterItem(self):
        """Iterator over all items. Applies when the list does not have
        BasicBase elements."""
        for elem in list.__iter__(self):
            yield elem

    def getBasicItem(self, index):
        """Item getter which calls C{getValue()} on the C{index}'d item."""
        return list.__getitem__(self, index).getValue()

    def setBasicItem(self, index, value):
        """Item setter which calls C{setValue()} on the C{index}'d item."""
        return list.__getitem__(self, index).setValue(value)

    def getItem(self, index):
        """Regular item getter, used when the list does not have BasicBase
        elements."""
        return list.__getitem__(self, index)

    # DetailNode

    def getDetailChildNodes(self, edge_filter=EdgeFilter()):
        """Yield children."""
        return (item for item in list.__iter__(self))

    def getDetailChildNames(self, edge_filter=EdgeFilter()):
        """Yield child names."""
        return ("[%i]" % row for row in xrange(list.__len__(self)))

class Array(_ListWrap):
    """A general purpose class for 1 or 2 dimensional arrays consisting of
    either BasicBase or StructBase elements."""

    def __init__(
        self,
        element_type = None,
        element_type_template = None,
        element_type_argument = None,
        count1 = None, count2 = None,
        parent = None):
        """Initialize the array type.

        :param element_type: The class describing the type of each element.
        :param element_type_template: If the class takes a template type
            argument, then this argument describes the template type.
        :param element_type_argument: If the class takes a type argument, then
            it is described here.
        :param count1: An C{Expression} describing the count (first dimension).
        :param count2: Either ``None``, or an C{Expression} describing the
            second dimension count.
        :param parent: The parent of this instance, that is, the instance this
            array is an attribute of."""
        if count2 is None:
            _ListWrap.__init__(self,
                               element_type = element_type, parent = parent)
        else:
            _ListWrap.__init__(self,
                               element_type = _ListWrap, parent = parent)
        self._elementType = element_type
        self._parent = weakref.ref(parent) if parent else None
        self._elementTypeTemplate = element_type_template
        self._elementTypeArgument = element_type_argument
        self._count1 = count1
        self._count2 = count2

        if self._count2 == None:
            for i in xrange(self._len1()):
                elem_instance = self._elementType(
                        template = self._elementTypeTemplate,
                        argument = self._elementTypeArgument,
                        parent = self)
                self.append(elem_instance)
        else:
            for i in xrange(self._len1()):
                elem = _ListWrap(element_type = element_type, parent = self)
                for j in xrange(self._len2(i)):
                    elem_instance = self._elementType(
                            template = self._elementTypeTemplate,
                            argument = self._elementTypeArgument,
                            parent = elem)
                    elem.append(elem_instance)
                self.append(elem)

    def _len1(self):
        """The length the array should have, obtained by evaluating
        the count1 expression."""
        if self._parent is None:
            return self._count1.eval()
        else:
            return self._count1.eval(self._parent())

    def _len2(self, index1):
        """The length the array should have, obtained by evaluating
        the count2 expression."""
        if self._count2 == None:
            raise ValueError('single array treated as double array (bug?)')
        if self._parent is None:
            expr = self._count2.eval()
        else:
            expr = self._count2.eval(self._parent())
        if isinstance(expr, (int, long)):
            return expr
        else:
            return expr[index1]

    def deepcopy(self, block):
        """Copy attributes from a given array which needs to have at least as
        many elements (possibly more) as self."""
        if self._count2 == None:
            for i in xrange(self._len1()):
                attrvalue = self[i]
                if isinstance(attrvalue, StructBase):
                    attrvalue.deepcopy(block[i])
                elif isinstance(attrvalue, Array):
                    attrvalue.updateSize()
                    attrvalue.deepcopy(block[i])
                else:
                    self[i] = block[i]
        else:
            for i in xrange(self._len1()):
                for j in xrange(self._len2(i)):
                    attrvalue = self[i][j]
                    if isinstance(attrvalue, StructBase):
                        attrvalue.deepcopy(block[i][j])
                    elif isinstance(attrvalue, Array):
                        attrvalue.updateSize()
                        attrvalue.deepcopy(block[i][j])
                    else:
                        self[i][j] = block[i][j]

    # string of the array
    def __str__(self):
        text = '%s instance at 0x%08X\n' % (self.__class__, id(self))
        if self._count2 == None:
            for i, element in enumerate(list.__iter__(self)):
                if i > 16:
                    text += "etc...\n"
                    break
                text += "%i: %s" % (i, element)
                if text[-1:] != "\n":
                    text += "\n"
        else:
            k = 0
            for i, elemlist in enumerate(list.__iter__(self)):
                for j, elem in enumerate(list.__iter__(elemlist)):
                    if k > 16:
                        text += "etc...\n"
                        break
                    text += "%i, %i: %s" % (i, j, elem)
                    if text[-1:] != "\n":
                        text += "\n"
                    k += 1
                if k > 16:
                    break
        return text

    def updateSize(self):
        """Update the array size. Call this function whenever the size
        parameters change in C{parent}."""
        ## TODO also update row numbers
        old_size = len(self)
        new_size = self._len1()
        if self._count2 == None:
            if new_size < old_size:
                del self[new_size:old_size]
            else:
                for i in xrange(new_size-old_size):
                    elem = self._elementType(
                        template = self._elementTypeTemplate,
                        argument = self._elementTypeArgument)
                    self.append(elem)
        else:
            if new_size < old_size:
                del self[new_size:old_size]
            else:
                for i in xrange(new_size-old_size):
                    self.append(_ListWrap(self._elementType))
            for i, elemlist in enumerate(list.__iter__(self)):
                old_size_i = len(elemlist)
                new_size_i = self._len2(i)
                if new_size_i < old_size_i:
                    del elemlist[new_size_i:old_size_i]
                else:
                    for j in xrange(new_size_i-old_size_i):
                        elem = self._elementType(
                            template = self._elementTypeTemplate,
                            argument = self._elementTypeArgument)
                        elemlist.append(elem)

    def read(self, stream, **kwargs):
        """Read array from stream."""
        # parse arguments
        self._elementTypeArgument = kwargs.get('argument')
        # check array size
        len1 = self._len1()
        if len1 > 2000000:
            raise ValueError('array too long (%i)' % len1)
        del self[0:self.__len__()]
        # read array
        if self._count2 == None:
            for i in xrange(len1):
                elem = self._elementType(
                    template = self._elementTypeTemplate,
                    argument = self._elementTypeArgument,
                    parent = self)
                elem.read(stream, **kwargs)
                self.append(elem)
        else:
            for i in xrange(len1):
                len2i = self._len2(i)
                if len2i > 2000000:
                    raise ValueError('array too long (%i)' % len2i)
                elemlist = _ListWrap(self._elementType, parent = self)
                for j in xrange(len2i):
                    elem = self._elementType(
                        template = self._elementTypeTemplate,
                        argument = self._elementTypeArgument,
                        parent = elemlist)
                    elem.read(stream, **kwargs)
                    elemlist.append(elem)
                self.append(elemlist)

    def write(self, stream, **kwargs):
        """Write array to stream."""
        self._elementTypeArgument = kwargs.get('argument')
        len1 = self._len1()
        if len1 != self.__len__():
            raise ValueError('array size (%i) different from to field \
describing number of elements (%i)'%(self.__len__(),len1))
        if len1 > 2000000:
            raise ValueError('array too long (%i)' % len1)
        if self._count2 == None:
            for elem in list.__iter__(self):
                elem.write(stream, **kwargs)
        else:
            for i, elemlist in enumerate(list.__iter__(self)):
                len2i = self._len2(i)
                if len2i != elemlist.__len__():
                    raise ValueError("array size (%i) different from to field \
describing number of elements (%i)"%(elemlist.__len__(),len2i))
                if len2i > 2000000:
                    raise ValueError('array too long (%i)' % len2i)
                for elem in list.__iter__(elemlist):
                    elem.write(stream, **kwargs)

    def fixLinks(self, **kwargs):
        """Fix the links in the array by calling C{fixLinks} on all elements
        of the array."""
        if not self._elementType._hasLinks:
            return
        for elem in self._elementList():
            elem.fixLinks(**kwargs)

    def getLinks(self, **kwargs):
        """Return all links in the array by calling C{getLinks} on all elements
        of the array."""
        links = []
        if not self._elementType._hasLinks:
            return links
        for elem in self._elementList():
            links.extend(elem.getLinks(**kwargs))
        return links

    def getStrings(self, **kwargs):
        """Return all strings in the array by calling C{getStrings} on all
        elements of the array."""
        strings = []
        if not self._elementType._hasStrings:
            return strings
        for elem in self._elementList():
            strings.extend(elem.getStrings(**kwargs))
        return strings

    def getRefs(self, **kwargs):
        """Return all references in the array by calling C{getRefs} on all
        elements of the array."""
        links = []
        if not self._elementType._hasLinks:
            return links
        for elem in self._elementList():
            links.extend(elem.getRefs(**kwargs))
        return links

    def getSize(self, **kwargs):
        """Calculate the sum of the size of all elements in the array."""
        return sum(
            (elem.getSize(**kwargs) for elem in self._elementList()), 0)

    def getHash(self, **kwargs):
        """Calculate a hash value for the array, as a tuple."""
        hsh = []
        for elem in self._elementList():
            hsh.append(elem.getHash(**kwargs))
        return tuple(hsh)

    def replaceGlobalNode(self, oldbranch, newbranch, **kwargs):
        """Calculate a hash value for the array, as a tuple."""
        for elem in self._elementList():
            elem.replaceGlobalNode(oldbranch, newbranch, **kwargs)

    def _elementList(self, **kwargs):
        """Generator for listing all elements."""
        if self._count2 is None:
            for elem in list.__iter__(self):
                yield elem
        else:
            for elemlist in list.__iter__(self):
                for elem in list.__iter__(elemlist):
                    yield elem

from pyffi.object_models.xml.Basic import BasicBase
from pyffi.object_models.xml.Struct import StructBase
