# -*- coding: utf-8 -*-
# Copyright © 2012 R.F. Smith <rsmith@xs4all.nl>. All rights reserved.
# $Date$
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

# Check this code with 'pylint -r n brep.py'

'''Reading triangulated models.'''

__version__ = '$Revision$'[11:-2]

import struct


def fromstl(fname):
    '''Prepare for processing an STL file.
    
    Arguments:
    fname -- file to read the STL file from.

    Returns:
    A tuple: (name, nf, reader)
    name -- the name of the STL object
    nf   -- the numbers of facets in the object
    reader -- a generator for the facets.
    '''
    with open(fname, 'r') as stlfile:
        data = stlfile.read()
    if data.find('vertex', 120) == -1: # Binary file format
        name, nf1 = struct.unpack("=80sI", data[0:84])
        name = name.replace("solid ", "")
        name = name.strip('\x00 \t\n\r')
        if len(name) == 0:
            name = "unknown"
        data = data[84:]
        facetsz = len(data)
        nf2 = facetsz / 50
        if nf1 != nf2:
            raise ValueError("Number of facets doesn't match file size.")
        items = [data[n:n+50] for n in range(0, facetsz, 50)]
        reader = _readbinary(items)
    else: # Text file format
        items = [s.strip() for s in data.split()]
        try:
            sn = items.index("solid")+1
            en = items.index("facet")
        except:
            raise ValueError("Not an STL file.")
        if sn == en:
            name = 'unknown'
        else:
            name = ' '.join(items[sn:en])
        nf1 = items.count('facet')
        del items[0:en]
        reader = _readtext(items)
    return name, nf1, reader


def allfacets(reader, verbose=False):
    '''Convenience function to read all facets in one go.

    Arguments:
    reader -- generator for the facets
    verbose -- wether to print the status messages generated by reader

    Returns:
    A list of facets, each of which is a tuple (a,b,c,n) where a,b,c
    are the 3-tuples of the coordinates of the vertices, and n is a
    normalized 3-tuple containing the normal vector of the facet.
    '''
    fl = []
    for stat, facet in reader:
        if verbose:
            print stat
        if facet:
            fl.append(facet)
    return fl


def _readbinary(items=None):
    '''Process the contents of a binary STL file as a
    generator.

    Arguments:
    items -- file data minus header split into 50-byte blocks.

    Yields:
    A tuple (status, facet)
    status -- string describing the status of the conversion of the
              facet
    facet  -- A tuple (a, b, c, n), where a,b and c are vertices and n
              is the normalized normal vector, or None.
    '''
    # Process the items
    for cnt, i in enumerate(items):
        f1x, f1y, f1z, f2x, f2y, f2z, f3x, f3y, f3z = \
        struct.unpack("=12x9f2x", i)
        a = (f1x, f1y, f1z)
        b = (f2x, f2y, f2z)
        c = (f3x, f3y, f3z)
        u = _sub(b, a)
        v = _sub(c, b)
        n = _cross(u, v)
        status = 'facet {} OK'.format(cnt+1)
        try:
            n  = _norm(n)
        except ValueError:
            status = 'skipped degenerate facet {}.'.format(cnt+1)
            yield status, None
        yield status, (a, b, c, n)


def _readtext(items=None):
    '''Process the contents of a text STL file as a
    generator.

    Arguments:
    items -- stripped lines of the text STL file

    Yields:
    A tuple (status, facet)
    status -- string describing the status of the conversion of the
              facet
    facet  -- A tuple (a, b, c, n), where a,b and c are vertices and n
              is the normalized normal vector, or None.
    '''
    # Items now begins with "facet"
    cnt = 0
    while items[0] == "facet":
        a = (float(items[8]), float(items[9]), float(items[10]))
        b = (float(items[12]), float(items[13]), float(items[14]))
        c = (float(items[16]), float(items[17]), float(items[18]))
        u = _sub(b, a)
        v = _sub(c, b)
        n = _cross(u, v)
        del items[:21]
        cnt += 1
        status = 'facet {} OK'.format(cnt)
        try:
            n  = _norm(n)
        except ValueError:
            status = 'skipped degenerate facet {}.'.format(cnt)
            yield status, None
        yield status, (a, b, c, n)


def _add(a, b):
    '''Calculate and return a+b.
    
    Arguments
    a -- 3-tuple of floats
    b -- 3-tuple of floats
    '''
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def _sub(a, b):
    '''Calculate and return a-b.
    
    Arguments
    a -- 3-tuple of floats
    b -- 3-tuple of floats
    '''
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _cross(a, b):
    '''Calculate and return the cross product of a and b.
    
    Arguments
    a -- 3-tuple of floats
    b -- 3-tuple of floats
    '''
    return (a[1]*b[2] - a[2]*b[1], 
            a[2]*b[0] - a[0]*b[2], 
            a[0]*b[1] - a[1]*b[0])


def _norm(a):
    '''Calculate and return the normalized a.
    
    Arguments
    a -- 3-tuple of floats
    '''
    L = (a[0]**2 + a[1]**2 + a[2]**2)**0.5
    if L == 0.0:
        raise ValueError('zero-length normal vector')
    return (a[0]/L, a[1]/L, a[2]/L)


# Built-in test.
if __name__ == '__main__':
    print "===== begin of text file ====="
    fn = "test/cube.stl"
    print "===== end of text file ====="
    print "===== begin of binary file ====="
    fn = "test/ad5-rtm-light.stl"
    print "===== end of binary file ====="
