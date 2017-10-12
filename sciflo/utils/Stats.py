#!/usr/bin/env python
#
# Stats.py -- Simple statistics class:  computes mean, sigma, min, max, rms.
#
# Author: Brian Wilson
#    @(#) Stats.py     1.0     2003/11/24
#
# Implemented by saving five accumulators:
#   no of points, mean, sum of squares of diffs from mean, min, and max.
# Methods:
#   add    -- add a data point to the accumulating stats
#   calc   -- compute the five statistics:  n, mean, std dev, min, max, rms
#   label  -- set the label for printing
#   format -- set the float format for printing
#   __repr__   -- generates one-line string version of statistics for easy printing
#   reset  -- zero the accumulators
#   addm   -- add an array of data points to the accumulators (add multiple)
#
# See tests at end of file for example usage.
#

from math import sqrt

class Stats:
    """Simple statistics class that computes mean, std dev, min, max, and rms."""
    def __init__(self, label=None, format=None):
        """Create Stats object, optionally set print label and float format string."""
        self.reset()
        self.labelStr = label; self.formatStr = format

    def add(self, val):
        """Add one data point to the accumulators."""
        self.n += 1
        dval = val - self.mean      # difference from current mean
        self.mean += dval/self.n    # update mean
        dval = val - self.mean      # diff from new mean
        self.sumsq += dval*dval     # update sum of squares
        if ( self.n == 1 ):
            self.min = val
            self.max = val
        else:
            self.min = min(self.min, val)
            self.max = max(self.max, val)
        return self

    def calc(self):
        """Calculate the statistics for the data added so far.
        Returns tuple of six values:  n, mean, sigma, min, max, rms.
        """
        sigma = 0.; rms = 0.
        if (self.n > 0):
            if (self.n >= 2):
                sd2 = self.sumsq / (self.n-1)
                if (sd2 > 0.): sigma = sqrt(sd2)
                else: sigma = 0.
            rms = sqrt(self.mean*self.mean +  self.sumsq/self.n)
        return (self.n, self.mean, sigma, self.min, self.max, rms)

    def label(self, str):
        """Label the statistics for printing."""
        self.labelStr = str
        return self
        
    def format(self, str):
        """Set the float format to be used in printing stats."""
        self.formatStr = str
        return self
        
    def __repr__(self):
        """One-line stats representation for simple printing."""
        if (self.labelStr == None or self.labelStr == ""): self.labelStr = "Stats"
        line = self.labelStr + ": "
        if self.formatStr:
            a = [self.formatStr for i in xrange(5)]
            a.insert(0, '%d')
            format = ' '.join(a)
            line += format % self.calc()
        else:
            line += "%d %f %f %f %f %f" % self.calc()
        return line

    def reset(self):
        """Reset the accumulators to start over."""
        self.n = 0
        self.mean = 0.0; self.sumsq = 0.0
        self.min = 0.0; self.max = 0.0
        self.labelStr = None
        self.formatStr = None
        return self

    def addm(self, seq):
        """Add multiple - add a sequence of data points all at once."""
        for val in seq:
            self.add(val)
        return self


if __name__ == '__main__':
    def test():
        """
>>> print Stats()
Stats: 0 0.000000 0.000000 0.000000 0.000000 0.000000

>>> def f(s):
...     for v in [2.3, 4.5, 1.8, 6.2, 3.5]: s.add(v)
...     s.label('test2')
...     return s
>>> print f( Stats() )
test2: 5 3.660000 1.468279 1.800000 6.200000 3.888480

>>> print Stats().label('test3').addm([2.3, 4.5, 1.8, 6.2, 3.5])
test3: 5 3.660000 1.468279 1.800000 6.200000 3.888480

>>> print Stats('test4').format('%5.2f').addm([2.3, 4.5, 1.8, 6.2, 3.5])
test4: 5  3.66  1.47  1.80  6.20  3.89

>>> print Stats('test5', '%4.1f').addm([2.3, 4.5, 1.8, 6.2, 3.5])
test5: 5  3.7  1.5  1.8  6.2  3.9
        """

    import doctest
    doctest.testmod()
