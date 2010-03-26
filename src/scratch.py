#!/usr/bin/env python
"""
 A playground for trying out some code.

 Using logging rather than print makes it clear that these are diagnostics,
 allows various sorts of diagnostics, and makes it simple to turn 'em off.

"""

import logging
logging.basicConfig(
    # level=logging.DEBUG, # debug<info<warning<error<critical ; default warning
    level=logging.INFO, # debug<info<warning<error<critical ; default warning
    format='%(message)s',
    #datefmt='%Y-%m-%d %H:%M:%S',
    #filename='/tmp/python.log',
    #filemode='w' # replace, don't append
)

import pprint
pp = pprint.PrettyPrinter(indent=4)

def extractParts(str):
    return map(lambda s: s.lstrip().rstrip(), str.lstrip('#').split('|'))

def readStepsFile(filename):
    """ Read a .steps file in and return the as a list of hashes. """
    file = open(filename)
    result = []
    lines = file.readlines()
    names = extractParts(lines[0])
    logging.debug("names = '%s'; len=%i" % (str(names), len(names)))
    for line in lines:
        if line[0] == '#':
            continue
        values = extractParts(line)
        if len(values) < len(names):
            continue
        logging.debug("values = '%s'; len=%i" % (str(values), len(values)))
        pairs = {}
        for i in range(len(names)):
            pairs[names[i]] = values[i]
        result.append(pairs)
    return result

# From pivot/ directory :
filename = 'dances/tango/el_flete/el_flete.steps'
steps = readStepsFile(filename)
logging.info(pp.pformat(steps))
