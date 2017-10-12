import os, sys

from sciflo.utils import ScifloConfigParser
from recognize import getSystemLevelUserDir

def getPubDataDir():
    """Return tuple of (absolute path, url path) to public data directory."""
    
    scp = ScifloConfigParser(os.path.join(getSystemLevelUserDir(), 'myconfig.xml'))
    return (os.path.join(sys.prefix, 'share', 'sciflo', 'data'),
            scp.getParameter('htmlBaseHref').replace('/web/', '/data/'))
