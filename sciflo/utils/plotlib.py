#!/bin/env python

import sys, math
import Numeric as N
import matplotlib
matplotlib.use('Agg', warn=False)
import matplotlib.pylab as M
try:
   from matplotlib.toolkits.basemap import Basemap
except:
   from mpl_toolkits.basemap import Basemap

def echo2(*s): sys.stderr.write(' '.join(map(str, s)) + '\n')
def warn(*s):  echo2('plotlib:', *s)
def die(*s):   warn('Error,',  *s); sys.exit()

CmdOptions = {'MCommand':  ['title', 'xlabel', 'ylabel',  'xlim', 'ylim', 'show'],
              'plot':      ['label', 'linewidth', 'legend', 'axis'],
              'map.plot':  ['label', 'linewidth', 'axis'],              
              'savefig':   ['dpi', 'orientation']
              }


def imageMap(lons, lats, data, outFile=None,
             bordersFromData=1, borders=[0., -90., 360., 90.],
             projection='cyl', makeFigure=False,
             meridians=[0, 360, 60], parallels=[-60, 90, 30],
             **options
             ):
    ensureItems(options, {'xlabel': 'Longitude (deg)', 'ylabel': 'Latitude (deg)', \
                     'title': 'An Image Map', 'dpi': 300})
    if bordersFromData:
        borders = [lons[0], lats[0], lons[-1], lats[-1]]
    m = Basemap(borders[0], borders[1], borders[2], borders[3], \
                projection=projection, lon_0=N.average([lons[0], lons[-1]]))

    if makeFigure: f = M.figure(figsize=(10,m.aspect*10)).add_axes([0.1,0.1,0.8,0.8],frameon=True)
    x, y = m(*M.meshgrid(lons,lats))
    levels, colls = m.contourf(x,y,data, 30,cmap=M.cm.jet,colors=None)

    m.drawcoastlines()
    m.drawmeridians(range(meridians[0], meridians[1], meridians[2]), labels=[0,0,0,1], linestyle='-')
    m.drawparallels(range(parallels[0], parallels[1], parallels[2]), labels=[1,1,1,1], linestyle='-')
    evalKeywordCmds(options)
    if outFile: M.savefig(outFile)

# all of these calls below are handled by the evalKeywordCmds line above
#    M.xlim(0,360)
#    M.xlabel(xlabel)
#    M.ylabel(ylabel)
#    M.colorbar()
#    M.title(title)
#    M.show()


def marksOnMap(lons, lats, markerType='bo', outFile=None,
              borders=[0., -90., 360., 90.],
              projection='cyl', makeFigure=False,
              meridians=[0, 360, 60], parallels=[-60, 90, 30],
              **options
               ):
    ensureItems(options, {'xlabel': 'Longitude (deg)', 'ylabel': 'Latitude (deg)', \
                          'title': 'Markers on a Map', 'dpi': 300})
    m = Basemap(borders[0], borders[1], borders[2], borders[3], \
                projection=projection, lon_0=N.average([lons[0], lons[-1]]))

    if makeFigure: f = M.figure(figsize=(10,m.aspect*10)).add_axes([0.1,0.1,0.8,0.8],frameon=True)
    m.plot(lons, lats, markerType, **validCmdOptions(options, CmdOptions['map.plot']))

    m.drawcoastlines()
    m.drawmeridians(range(meridians[0], meridians[1], meridians[2]), labels=[0,0,0,1], linestyle='-')
    m.drawparallels(range(parallels[0], parallels[1], parallels[2]), labels=[1,1,1,1], linestyle='-')
    evalKeywordCmds(options)
    if outFile: M.savefig(outFile)


def plotColumns(specs, groupBy=None, outFile=None, rmsDiffFrom=None, floatFormat=None,
                colors='bgrcmyk', markers='+x^svD<4>3', **options):
    if groupBy:
        plotColumnsGrouped(specs, groupBy, outFile, rmsDiffFrom, floatFormat,
                           colors, markers, **options)
    else:
        plotColumnsSimple(specs, outFile, rmsDiffFrom, floatFormat,
                          colors, markers, **options)


def plotColumnsSimple(specs, outFile=None, rmsDiffFrom=None, floatFormat=None,
                colors='bgrcmyk', markers='+x^svD<4>3', **options):
    """Plot olumns of numbers from one or more data files.
    Each plot spec. contains a filename and a list of labelled columns:
      e.g., ('file1', 'xlabel:1,ylabel1:4,ylabel2:2,ylabel3:13)
    Bug:  For the moment, only have 7 different colors and 10 different markers.
    """
    ensureItems(options, {'legend': True})
    ydataMaster = None
    for spec in specs:
        file, columns = spec          # each spec is a (file, columnList) pair
        columns = columns.split(',')  # each columnList is a comma-separated list of named columns
        # Each named column is a colon-separated pair or triple 'label:integer[:style]'
        # Column indices are one-based.
        # Styles are concatenated one-char flags like 'go' for green circles or
        # 'kx-' for black X's with a line.
        fields = N.array([map(floatOrMiss, line.split()) for line in open(file, 'r')])
        xcol = columns.pop(0)  # first column in list is the x axis
        xlabel, xcol, xstyle = splitColumnSpec(xcol)
        xdata = fields[:,xcol-1]
        markIndex = 0
        for ycol in columns:
            ylabel, ycol, ystyle = splitColumnSpec(ycol)
            if ystyle is None: ystyle = colors[markIndex] + markers[markIndex]            
            ydata = fields[:,ycol-1]  # all other columns are multiple y plots
            if rmsDiffFrom:
                if ydataMaster is None:
                    ydataMaster = ydata    # kludge: must be first ycol in first file
                    ylabelMaster = ylabel
                else:
                    s = diffStats(ylabelMaster, ydataMaster, ylabel, ydata)
                    print >>sys.stderr, s.format(floatFormat)
                    n, mean, sigma, min, max, rms = s.calc()
                    ylabel = ylabel + ' ' + floatFormat % rms
            M.plot(xdata, ydata, ystyle, label=ylabel)
            markIndex += 1
    evalKeywordCmds(options)
    if outFile: M.savefig(outFile)    


def plotColumnsGrouped(specs, groupBy, outFile=None, rmsDiffFrom=None, floatFormat=None,
                colors='bgrcmyk', markers='+x^svD<4>3', **options):
    """Plot olumns of numbers from one or more data files.
    Each plot spec. contains a filename and a list of labelled columns:
      e.g., ('file1', 'xlabel:1,ylabel1:4,ylabel2:2,ylabel3:13)
    Bug:  For the moment, only have 7 different colors and 10 different markers.
    """
    ensureItems(options, {'legend': True})
    ydataMaster = None
    for spec in specs:
        file, columns = spec          # each spec is a (file, columnList) pair
        columns = columns.split(',')  # each columnList is a comma-separated list of named columns
        # Each named column is a colon-separated pair or triple 'label:integer[:style]'
        # Column indices are one-based.
        # Styles are concatenated one-char flags like 'go' for green circles or
        # 'kx-' for black X's with a line.
        fields = N.array([map(floatOrMiss, line.split()) for line in open(file, 'r')])
        xcol = columns.pop(0)  # first column in list is the x axis
        xlabel, xcol, xstyle = splitColumnSpec(xcol)
        xdata = fields[:,xcol-1]
        markIndex = 0
        for ycol in columns:
            ylabel, ycol, ystyle = splitColumnSpec(ycol)
            if ystyle is None: ystyle = colors[markIndex] + markers[markIndex]            
            ydata = fields[:,ycol-1]  # all other columns are multiple y plots
            if rmsDiffFrom:
                if ydataMaster is None:
                    ydataMaster = ydata    # kludge: must be first ycol in first file
                    ylabelMaster = ylabel
                else:
                    s = diffStats(ylabelMaster, ydataMaster, ylabel, ydata)
                    print >>sys.stderr, s.format(floatFormat)
                    n, mean, sigma, min, max, rms = s.calc()
                    ylabel = ylabel + ' ' + floatFormat % rms
            M.plot(xdata, ydata, ystyle, label=ylabel)
            markIndex += 1
    evalKeywordCmds(options)
    if outFile: M.savefig(outFile)    


def plotTllv(inFile, markerType='kx', outFile=None, groupBy=None, **options):
    """Plot the lat/lon locations of pointes from a time/lat/lon/value file."""
    fields = N.array([map(float, line.split()) for line in open(inFile, 'r')])
    lons = fields[:,2]; lats = fields[:,1]
    marksOnMap(lons, lats, markerType, outFile, \
               title='Lat/lon plot of '+inFile, **options)


def plotVtecAndJasonTracks(gtcFiles, outFile=None, names=None, makeFigure=True, show=False, **options):
    """Plot GAIM climate and assim VTEC versus JASON using at least two 'gc' files.
    First file is usually climate file, and rest are assim files.
    """
    ensureItems(options, {'title': 'GAIM vs. JASON for '+gtcFiles[0], \
                          'xlabel': 'Geographic Latitude (deg)', 'ylabel': 'VTEC (TECU)'})
    if 'show' in options:
        show = True
        del options['show']
    M.subplot(211)
    gtcFile = gtcFiles.pop(0)
    name = 'clim_'
    if names: name = names.pop(0)
    specs = [(gtcFile, 'latitude:2,jason:6,gim__:8,%s:13,iri__:10' % name)]
    name = 'assim'
    for i, gtcFile in enumerate(gtcFiles):
        label = name
        if len(gtcFiles) > 1: label += str(i+1)
        specs.append( (gtcFile, 'latitude:2,%s:13' % label) )
    plotColumns(specs, rmsDiffFrom='jason', floatFormat='%5.1f', **options)
    M.legend()
    
    M.subplot(212)
    options.update({'title': 'JASON Track Plot', 'xlabel': 'Longitude (deg)', 'ylabel': 'Latitude (deg)'})
    fields = N.array([map(floatOrMiss, line.split()) for line in open(gtcFiles[0], 'r')])
    lons = fields[:,2]; lats = fields[:,1]
    marksOnMap(lons, lats, show=show, **options)
    if outFile: M.savefig(outFile)


def diffStats(name1, vals1, name2, vals2):
    """Compute RMS difference between two Numeric vectors."""
    from Stats import Stats
    label = name2 + ' - ' + name1
    diff = vals2 - vals1
    return Stats().label(label).addm(diff)

def ensureItems(d1, d2):
    for key in d2.keys():
        if key not in d1: d1[key] = d2[key]

def splitColumnSpec(s):
    """Split column spec 'label:integer[:style]' into its 2 or 3 parts."""
    items = s.split(':')
    n = len(items)
    if n < 2:
        die('plotlib: Bad column spec. %s' % s)
    elif n == 2:
        items.append(None)
    items[1] = int(items[1])
    return items

def floatOrMiss(val, missingValue=-999.):
    try: val = float(val)
    except: val = missingValue
    return val

def evalKeywordCmds(options, cmdOptions=CmdOptions):
    for option in options:
        if option in cmdOptions['MCommand']:
            args = options[option]
            if args:
                if args is True:
                    args = ''
                else:
                    args = "'" + args + "'"
                if option in cmdOptions:
                    args += dict2kwargs( validCmdOptions(options, cmdOptions[option]) )
                try:
                    eval('M.' + option + '(%s)' % args)
                except:
                    die('failed eval of keyword command option failed: %s=%s' % (option, args))
#        else:
#            warn('Invalid keyword option specified" %s=%s' % (option, args))

def validCmdOptions(options, possibleOptions):
    return dict([(option, options[option]) for option in options.keys() if option in possibleOptions])

def dict2kwargs(d):
    args = [',%s=%s' % (kw, d[kw]) for kw in d]
    return ', '.join(args)


if __name__ == '__main__':
    from sys import argv
#    lons = N.arange(0, 361, 2, N.Float)
#    lats = N.arange(-90, 91, 1, N.Float)
#    data = N.fromfunction( lambda x,y: x+y, (len(lats), len(lons)))

    outFile = 'out.png'
#    imageMap(lons, lats, data, outFile)
#    marksOnMap(lons, lats, 'bx', outFile)
    plotVtecAndJasonTracks([argv[1], argv[2]], outFile, show=True, legend=True)
