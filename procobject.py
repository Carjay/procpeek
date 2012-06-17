#!/usr/bin/env python

import re

class ProcObject:
    """
        class to hold information from a proc entry
    """
    pid = None
    
    def __init__(self, pid):
        """
            pid is the pid to scan
        """
        self.pid = pid
        self.rescan()
    

    def rescan(self):
        """
            rescan proc entries
        """
        smaps = None
        try:
            fh = open("/proc/%d/smaps" % self.pid)
            smaps = fh.read()
        except IOError, e:
            raise ValueError, "unable to open proc entry to get smaps"

        its = re.split("([a-fA-F0-9]+\-[a-fA-F0-9]+ )", smaps, flags = re.DOTALL)
        entries = list(its)
        if entries[0] != '':
            print("Warning: unexpected start text in smaps: '%s'" % entries[0])
        entrycnt = len(entries[1:]) / 2
        print len(entries[1:])
        if len(entries[1:]) % 2: # should not happen as even a superfluous separator at the end leads to an extra empty string
            print("Warning: unexpected number of entries %d" % len(entries[1:]))

        # arranged in pairs due to the separator
        rangemap = dict() # startaddr pointing to [ range, dictionary of keys]
        for i in range(entrycnt):
            entrylines = entries[(2*i)+2].splitlines()
            startaddr, endaddr = [ int(x.strip(),16) for x in entries[(2*i)+1].split('-') ]
            print startaddr, endaddr, endaddr-startaddr
            newentry = [ endaddr-startaddr, dict() ]
            newentry[1]['description'] = entrylines[0]
            for line in entrylines[1:]:
                key,value = [ x.strip() for x in line.split(':') ]
                newentry[1][key] = value
            rangemap[startaddr] = newentry
            print newentry

    def dump(self):
        return "ok"



if __name__ == '__main__':
    pass

