#!/usr/bin/env python

import os
import re
import sys
import getopt

from procobject import ProcObject


def main():
    pid = None
    
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "p:", ["pid=", "size"] )
        for opt, optarg in opts:
            if opt == "p" or opt == "--pid":
                try:
                    pid = int(optarg)
                except ValueError:
                    print("Error: pid must be a number")
                    return
            else:
                print("Error: unhandled option '%s'" % (opt))

    except getopt.GetoptError, e:
        print("Error in arguments: %s" % str(e))

    if pid:
        po = ProcObject(pid)


try:
    main()
except KeyboardInterrupt:
    pass

