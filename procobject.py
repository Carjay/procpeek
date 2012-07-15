#!/usr/bin/env python

# Copyright (c) 2012, Carsten Juttner <carjay@gmx.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the owner nor the names of its contributors may
#      be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import logging
import re
import sys

# logger used for all objects
_logger = logging.getLogger("procpeek")


class SMaps(object):
    # parsed from first line
    saddr = None # start address of mapped RAM
    eaddr = None # end address (the address following saddr which is NOT accessible anymore)
    canread  = None
    canwrite = None
    canexecute = None
    isprivate = None
    offset = None # e.g. for memory mapped files this is the offset into the file
    device = None # e.g. for memory mapped this is the device the file is residing on
    inode = None # inode for memory mapped files
    name  = None # descriptive name, e.g. [heap] or a file name like /usr/lib/libc.so
    
    # entries taken directly from proc
    size  = None # size of mapping
    rss   = None #
    pss   = None # proportional set size, "process' share of rss"
    shared_clean = None
    shared_dirty = None
    private_clean = None
    private_dirty = None
    referenced    = None
    anonymous     = None
    anonhugepages = None
    swap          = None
    kernelpagesize = None
    mmupagesize    = None
    locked         = None

    # static size helper
    _sizemap = {
            "kB"    : 1<<10,
    }

    def __setattr__(self, attr, val):
        # we override these to convert strings to integer
        if attr in ["inode",
                    "size", "rss", "pss",
                    "shared_clean",  "shared_dirty", "private_clean", "private_dirty",
                    "referenced", "anonymous", "anonhugepages", "swap",
                    "kernelpagesize", "mmupagesize", "locked"
                    ]:
            splitval = val.strip().split()
            if len(splitval) > 2:
                _logger.warning("unexpected value for attribute '%s': '%s'" % (attr, val))
            else:
                try:
                    val = int(splitval[0])
                except ValueError:
                    warning("unable to convert size expression for attribute '%s': '%s'" % (attr,val))
                # apply multiplier if necessary
                if len(splitval) == 2:
                    if splitval[1] not in self._sizemap:
                        _logger.warning("size expression not in sizemap for attribute '%s': '%s'" % (attr, val))
                    else:
                        val *= self._sizemap[splitval[1]]
        if attr == "offset":
            val = int(val,16)
        
        object.__setattr__(self, attr, val)
   



class ProcObject:
    """
        class to hold information from a proc entry
    """
    pid = None
    smapslist = None # holds current mappings as SMaps instances (sorted by startaddress)

    def __init__(self, pid):
        """
            pid - the pid to parse
            note that this will implicitly execute a parse
        """
        self.pid = pid
        self.reparse()


    def reparse(self):
        """
            rescan proc entries to update pid information
        """
        self.smapslist = []
        
        smaps = None
        try:
            fh = open("/proc/%d/smaps" % self.pid)
            smaps = fh.read()
        except IOError, e:
            _logger.error("unable to open proc entry for pid %d to get smaps" % self.pid)
            raise IOError, "unable to open proc entry for pid %d to get smaps" % self.pid

        its = re.split("([a-fA-F0-9]+\-[a-fA-F0-9]+ )", smaps, flags = re.DOTALL)
        entries = list(its)
        if entries[0] != '':
            _logger.error("Warning: unexpected start text in smaps: '%s'" % entries[0])
        entrycnt = len(entries[1:]) / 2

        if len(entries[1:]) % 2: # should not happen as even a superfluous separator at the end leads to an extra empty string
            _logger.error("Warning: unexpected number of entries %d" % len(entries[1:]))

        # first pass, internal "close to metal" representation, arranged in pairs due to the separator
        rangemap = dict() # startaddr pointing to [ range, dictionary of keys ]

        for i in range(entrycnt):
            entrylines = entries[(2*i)+2].splitlines()
            startaddr, endaddr = [ int(x.strip(),16) for x in entries[(2*i)+1].split('-') ]
            newentry = [ endaddr-startaddr, dict() ]
            newentry[1]['saddr'] = startaddr
            newentry[1]['eaddr'] = endaddr
            newentry[1]['description'] = entrylines[0]
            for line in entrylines[1:]:
                key,value = [ x.strip() for x in line.split(':') ]
                newentry[1][key] = value
            rangemap[startaddr] = newentry

        # second pass, fill the SMaps structure
        for e in sorted(rangemap):
            sm = SMaps()
            # translate into a SMaps entry
            entrydict = rangemap[e][1]
            for k in entrydict.keys():
                if k == 'description':
                    desc = entrydict[k]
                    m = re.match("(.)(.)(.)(.)\s+([0-9a-fA-F]+)\s+(.+?)\s+(\d+)\s*(.*)", desc)
                    if m:
                        r,w,x,p,sm.offset,sm.device,sm.inode,sm.name = m.groups()
                        for expectedtrue, expectedfalse, flag, varname in [
                                            ('r', '-', r, 'canread'),
                                            ('w', '-', w, 'canwrite'),
                                            ('x', '-', x, 'canexecute'),
                                            ('p', 's', p, 'isprivate'),
                                        ]:
                            if flag == expectedtrue:
                                sm.__setattr__(varname, True)
                            elif flag == expectedfalse:
                                sm.__setattr__(varname, False)
                            else:
                                _logger.warning("unrecognized protection %s-flag in '%s'" % (expected, desc))
                    else:
                        _logger.warning("unhandled description line: '%s'" % desc)
                    pass # special case
                elif k.lower() in sm.__class__.__dict__: # must be in the class definition
                    sm.__setattr__(k.lower(), entrydict[k])
                else:
                    _logger.warning("name %s not found, need to add support for it" % k)
            self.smapslist.append(sm)



if __name__ == '__main__':
    pass

