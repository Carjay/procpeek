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


import os
import getopt
import sys
import logging

from enable.api import Component, ComponentEditor, Container
from traits.api import HasTraits, Instance
from traitsui.api import Item, View, InstanceEditor, Group

from chaco.api import ArrayDataSource, ArrayPlotData, BarPlot, DataRange1D, LabelAxis, Plot ,\
                        LinearMapper, LogMapper, OverlayPlotContainer, PlotAxis, add_default_axes, add_default_grids
from chaco.tools.api import ZoomTool, PanTool

from numpy import linspace, sin

class MyPlot(HasTraits):
    plot = Instance(Container)
    
    traits_view = View( Group(
                            Item('plot', editor = ComponentEditor(), resizable = True)
                        ),
                        resizable = True, width = 800, height = 600
                      )
        
    
    def __init__(self, smaps, *args, **kwargs):
        super(MyPlot, self).__init__(*args, **kwargs)

        indexdata = []
        startdata = []
        stopdata   = []

        lastval = 0
        for mem in smaps:
            if mem.size != 0:
                print mem.canread, mem.canwrite
                indexdata.append(mem.canread << 0 | mem.canwrite << 1 | mem.isprivate << 2)
                startdata.append(lastval)
                stopdata.append(lastval + mem.size)
                lastval += mem.size
                print mem.size

        indexsrc = ArrayDataSource(data = indexdata)
        startsrc = ArrayDataSource(data = startdata)
        stopsrc   = ArrayDataSource(data = stopdata)

        idxrange = [min(indexdata),max(indexdata)]
        valrange = [min(startdata),max(stopdata)]

        indexmapper = LinearMapper(range=DataRange1D(ArrayDataSource(idxrange)))
        valuemapper = LinearMapper(range=DataRange1D(ArrayDataSource(valrange)))

        barlist = []
        barlist.append(self.drawBar(indexsrc, indexmapper, startsrc, valuemapper, 0xc09090, stopsrc))
        #barlist.append(self.drawBar(indexsrc, indexmapper, rsssrc, valuemapper, 0xffa0a0))
        #barlist.append(self.drawBar(idxs, indexmapper, start, valuemapper, 0x0000ff, stop))

        bottom_axis = PlotAxis(barlist[0], orientation='bottom', tick_label_formatter = lambda x : str(x))
        barlist[0].underlays.append(bottom_axis)
        
        modelist = []
        for i in range(8):
            mstr = ""
            mstr += ['r','-'][i&1==0]
            mstr += ['w','-'][i&2==0]
            mstr += ['p','s'][i&4==0]
            modelist.append(mstr)
        
        vaxis1 = LabelAxis(barlist[0], orientation='left',
                                title="Mode",
                                positions = range(len(modelist)),
                                labels=modelist,
                                tick_interval = 1)
        #vaxis2 = LabelAxis(barlist[0], orientation='right',
        #                           title="Map Name",
        #                           positions = range(idx),
        #                           labels=["%s" % os.path.basename(x) for x in namedata])
        barlist[0].underlays.append(vaxis1)
        #barlist[0].underlays.append(vaxis2)
        barlist[0].tools.append(ZoomTool(barlist[0]))
        barlist[0].tools.append(PanTool(barlist[0]))
        
        #add_default_axes(plot, orientation = 'v')
        add_default_grids(barlist[0], orientation = 'v')

        container = OverlayPlotContainer(bgcolor = "white")
        for p in barlist:
            p.padding = [200, 200, 20, 30]
            p.bgcolor = "white"
            container.add(p)

        self.plot = container


    def drawBar(self, indexsrc, indexmapper, valuesrc, valuemapper, color, startval = None):
       
        return BarPlot(index = indexsrc, value = valuesrc,
                       index_mapper = indexmapper,
                       value_mapper = valuemapper,
                       starting_value = startval,
                       line_color = 0x202020,
                       fill_color = color,
                       bar_width = 1.0,
                       orientation = 'v')



logging.basicConfig(format = "%(asctime)s: %(module)s:%(funcName)s: %(message)s")
plog = logging.getLogger("procpeek")
plog.setLevel(logging.INFO)
info, warning, error = plog.info, plog.warning, plog.error

from procobject import ProcObject, SMaps


def sizeformat(number):
    n = float(number)
    if n / (1<<40) > 1.0:
        return "%.02f TiB" % (n/(1<<40))
    if n / (1<<30) > 1.0:
        return "%.02f GiB" % (n/(1<<30))
    if n / (1<<20) > 1.0:
        return "%.02f MiB" % (n/(1<<20))
    if n / (1<<10) > 1.0:
        return "%.02f kiB" % (n/(1<<10))
    else:
        return "%.02f B" % (n)


def main():
    pid = None
    
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "p:", ["pid="] )
        for opt, optarg in opts:
            if opt == "-p" or opt == "--pid":
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
        info("pid %d %s" % (pid, '#' * 40))
        try:
            po = ProcObject(pid)
            smaps = po.smapslist

            pl = MyPlot(smaps)
            pl.configure_traits()
            return

            totalsize = 0
            rsssize = 0
            psssize = 0
            lastaddr = 0
            for mem in smaps:
                if mem.size != 0: # and (not mem.name or mem.name.count("heap") or mem.name.count("stack")):
                    #if (mem.saddr - lastaddr) != 0:
                    #    info("gap: %s" % (sizeformat(mem.saddr - lastaddr)))
                    lastaddr = mem.eaddr
                    if mem.canread:
                        prot = ['','r'][mem.canread>0] + ['','w'][mem.canwrite>0] + ['','x'][mem.canexecute>0] + ['s','p'][mem.isprivate>0]
                        info("page 0x%x (%s) %d '%s' %f%% resident" % (mem.saddr, prot, mem.size, mem.name, float(mem.rss*100.0)/mem.size))
                    #else:
                    #    realsize = mem.eaddr - mem.saddr
                    #    info("guard: %s %s %s %s %s %s %s" % (hex(mem.saddr), realsize, mem.size, mem.name, mem.rss, mem.pss, mem.anonymous))
        except IOError:
            info("unable to open proc infos for pid %d" % pid)


try:
    main()
except KeyboardInterrupt:
    pass

