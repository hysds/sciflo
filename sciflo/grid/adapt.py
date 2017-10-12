#-----------------------------------------------------------------
#    adapt.py
#-----------------------------------------------------------------

import sys, types, re
from traceback import print_exc
from elementtree.ElementTree import ElementTree, XML

def echo2(*s): sys.stderr.write(' '.join(s) + '\n')
def warn(*s): echo2('adapt:', *s)

Verbose = False
Warn = False

class Adapt:
    """Decorator to *declare* the types of a function's arguments,
    as in, these are the argument types I *want/require*.

    The actual input arguments are then automatically 'adapted' to
    the declared types, potentially converting each input object to
    a different type of object, using a registry of installed
    conversion operators.  If an appropriate conversion is not found,
    then MissingConversionError is raised.  If the adaptation fails,
    then AdaptationError is raised.

    Not all arguments need be typed; i.e., the type list can be
    shorter than the function arg list.

    Each of the args of this decorator function (types) can be:
      1) A string type name; e.g., 'xsd:float' or 'py:ListOfList'.
      2) A type object; e.g., types.TupleType.
      3) A class object for the type; e.g., ElementTree
      4) A callable object that takes a single argument,
         in which case the type *is* the conversion function;
         e.g., float().
      5) An object, in which case the type is type(obj).
    
    See the function getTypeString for the implementation of this case statement.
    
    To use adapt, one uses the @adapt() decorator to declare the types
    your function wants, and automatically wrap the function.
    
    For example, the adapt declaration:
      @adapt(ElementTree, 'py:ListOfList', float)
      def myfunction(xmlDoc, xmlFragment, tolerance):
          pass
    means that this function call:
      myfunction('<?xml ...><tag> ... </tag>',
                 '<records><record><name>Hoover</name><address> ... </record></records>',
                 '3.0km')
    will invoke three adaptations before the actual function is called:
      - The xmlDoc will be parsed into an ElementTree data structure by
        the conversion function, elementtree.ElementTree.XML, installed
        under the registry key 'str -> elementTree.ElementTree.XML'.        
      - The xmlFragment will be parsed and converted to a list of lists
        python data structure using an installed conversion.
      - The value string will be converted to a float value by
        calling the built-in float() function on the string.
    """
    def __init__(self):
        self._registry = ConversionRegistry()
        self._synonyms = SynonymsDict()
    
    def addConversions(self, triples, verbose=Verbose):
        self._registry.addTriples(triples, verbose=verbose)
        return self
    
    def __call__(self, *types):
        def adaptThenCall(fn):
            """Adapt the input args and then call the function.
            The decorator replaces the function with this wrapper."""
            #assert len(types) <= fn.func_code.co_argcount
            def newFn(*args, **kwds):
                args = list(args)
                for i, type in enumerate(types):
                    outType, conversionFn = getTypeStringOrConversion(type)
                    if conversionFn is None:
                        outType = ns(outType)
                        inType = ns(getType(args[i]))
                        if inType in self.synonyms(outType):  # in and out types equal, so no conversion needed
                            continue
                        else:
                            conversionFn = self.findConversion(inType, outType, verbose=Verbose)
                    try:
                        args[i] = conversionFn(args[i], verbose=Verbose)
                    except:
                        #print_exc()
                        raise AdaptationError
                return fn(*args, **kwds)
            newFn.func_name = fn.func_name
            return newFn
        return adaptThenCall
    
    def findConversion(self, inType, outType, verbose=Verbose):
        return self._registry.find(inType, outType, verbose=verbose)
        
    def registerConversion(self, inType, outType, conversionFn, verbose=Verbose):
        self._registry.register(inType, outType, conversionFn, verbose=verbose)
        return self
    
    def unregisterConversion(self, inType, outType, conversionFn, verbose=Verbose):
        self._registry.unregister(inType, outType, conversionFn, verbose=verbose)
        return self

    def synonyms(self, word):
        """Return all of the synonyms for a type, including itself."""
        return self._synonyms.synonyms(word)    
    
    def addTypeSynonyms(self, syns):
        self._synonyms.addSynonyms(syns)
        return self
    
    def addTypeSynonymsList(self, synsList):
        self._synonyms.addSynonymsList(synsList)
        return self
    

class AdaptationError(TypeError): pass
class MissingConversionError(AdaptationError): pass

_DefaultNamespaceDict = {'sf': '{http://sciflo.jpl.nasa.gov/2006v1/sf}',  # SciFlo namespace
                         'xs': '{http://www.w3.org/2001/XMLSchema}',      # XML schema namespace
                         'py': '{http://sciflo.jpl.nasa.gov/2006v1/py}'   # SciFlo python namespace
                        }

def ns(tag, namespaceDict=_DefaultNamespaceDict):
    if tag[0] == '{': return tag
    if tag.find(':') == -1: return tag
    prefix, name = tag.split(':')
    try:
        namespace = namespaceDict[prefix]
        return namespace + name
    except:
        return tag
    
def getTypeStringOrConversion(stringOrTypeOrClassOrFnOrObj):
    """Return a type string (for lookup) from type name (already a string),
    a type object, class object, or implicit conversion function;
    or compute the type of the object.  Also return the conversion fn. if present.
    """
    obj = stringOrTypeOrClassOrFnOrObj
    ty = type(obj)
    if ty == types.StringType:
        return (obj, None)
    elif ty == types.TypeType:
        return (obj.__name__, None)
    elif ty == types.ClassType:
        return (str(obj), None)
    elif callable(obj):
        return (obj.__name__, obj)
    else:
        return (ty.__name__, None)

def getTypeString(stringOrTypeOrClassOrFnOrObj):
    return getTypeStringOrConversion(stringOrTypeOrClassOrFnOrObj)[0]
    
def getType(obj):
    """Return the type of any object, as a type string for lookup."""
    ty = type(obj)
    if ty == types.StringType:
        return 'str'
    else:
        return getTypeString(ty)


class SynonymsDict:
    """Holds a set of registered type synonyms."""
    def __init__(self, synonyms={}):
        self._synonyms = synonyms

    def addSynonyms(self, syns):
        syns = map(ns, syns)
        for syn in syns:
            self._synonyms[syn] = syns
        return self

    def addSynonymsList(self, synsList):
        for syns in synsList:
            self.addSynonyms(syns)
        return self

    def synonyms(self, word):
        """Return all of the synonyms for a word, including itself."""
        return self._synonyms.get(word, [word])    
    
_DefaultTypeSynonyms = \
    [['str', 'xs:string', 'py:string'],
     ['float', 'py:float']
    ]


class ConversionRegistry:
    """Holds a set of registered conversion functions, 
    conversionFn: inType -> outType, that can be looked up by
    either the forward key (in->out) or the backward key (out->in).
    """
    def __init__(self, convert={}):
        """Init a registry from a DictOfDict.
        self.convert[inType][outType] is a set of potential conversion functions
        for converting inType -> outType.
        """
        self.convert = convert
        
    def addTriples(self, triples, verbose=Verbose):
        """Add (inType, outType, conversionFn) triples to the registry."""
        for triple in triples: self.register(*triple)
        return self
        
    def register(self, inType, outType, conversionFn, verbose=Verbose):
        inType = ns(getTypeString(inType)); outType = ns(getTypeString(outType))
        self.convert.setdefault(inType, {}).setdefault(outType, set()).add(conversionFn)
        if verbose: warn('Registered conversion %s: %s -> %s' %
                          (str(conversionFn), inType, outType))
        # for each type pair, inType -> outType, keep a set of potential conversion functions
        return self
        
    def unregister(self, inType, outType, conversionFn, verbose=Verbose):
        inType = ns(getTypeString(inType)); outType = ns(getTypeString(outType))
        if verbose: warn('Unregistered conversion %s: %s -> %s' %
                          (str(conversionFn), inType, outType))
        try:
            self.convert[inType][outType].remove((conversionFn))
        except:
            warn('Attempt to unregister a conversion function that is not registered: ' \
                 '%s: %s -> %s' % (str(conversionFn), inType, outType))
        return self
    
    def find(self, inType, outType, verbose=Verbose):
        """Find a conversion from inType to outType."""
        inType = ns(getTypeString(inType)); outType = ns(getTypeString(outType))
        inTypes = typeSynonyms(inType); outTypes = typeSynonyms(outType)
        conversions = None
        for inType in inTypes:
            if inType in self.convert:
                for outType in outTypes:
                    if outType in self.convert[inType]:
                        fns = self.convert[inType][outType]  # set of potential conversion functions
                        if verbose: warn('Found conversions %s: %s -> %s' %
                                           (str(fns), inType, outType))
                        return ConversionRegistry.applyFunctionChain([fns], verbose)
                                                             # apply single-link chain
                conversions = self.seekChain(inType, outType, verbose)
                if conversions:
                    if verbose: warn('Found conversion chain %s: %s -> %s' %
                                       (str(conversions), inType, outType))
                    return ConversionRegistry.applyFunctionChain(conversions, verbose)
        raise MissingConversionError('No installed conversion for %s -> %s'
                                       % (inType, outType))
    
    def seekChain(self, inType, outType, verbose=Verbose):
        """Seek a chain of conversions to convert from inType to outType."""
        chain = self._seekChain(inType, outType, verbose)
        if chain:
            conversions = [self.convert[key[0]][key[1]] for key in chain]
            # conversions is now an ordered list (chain) of sets, where each set contains one or more potential conversion functions
            # for that link in the chain
            return conversions
        else:
            return None
        
    def _seekChain(self, inType, outType, verbose, chain=[], typesSeen=set()):
        """Recursively seek a conversion by forward chaining.
        KNOWN BUG: Synonyms not implemented for links in the middle of the chain.
        
        Chain argument holds the candidate chain discovered so far.
        TypesSeen argument holds a set of types that have already been visited
        via some candidate chain.
        """
        if verbose: warn('Seeking chain for conversion %s -> %s' % (inType, outType))
        typesSeen.add(inType)
        for ty in self.convert[inType]:
            if ty in typesSeen: continue
            link = (inType, ty)
            if verbose: warn('Trying link (%s -> %s)' % link)
            candidate = chain + [link]
            if ty in typeSynonyms(outType):
                return candidate
            else:
                candidate = self._seekChain(ty, outType, verbose, candidate, typesSeen)
                if candidate:
                    return candidate
                else:
                    continue
        return None

    @staticmethod
    def applyFunctionChain(conversions, verbose=Verbose):
        def convert(inObj, verbose=verbose):
            if verbose: warn('Converting: %s' % str(inObj))
            for link in conversions:    # execute each link in the conversion chain
                converted = False
                for fn in link:         # for each link, try each of the conversion functions
                    try:
                        if verbose: warn('Converting: Trying link conversion %s' % str(fn))
                        outObj = fn(inObj)
                        inObj = outObj  # if conversion succeeds, continue to next link in chain
                        converted = True
                        break
                    except:             # if conversion raises an exception, try the next function
                        if Warn:
                            warn('Conversion function %s raised exeception when called on %s' \
                              % (str(fn), str(inObj)))
                            #print_exc()
                            #if len(link) > 1: warn('Trying the next potential conversion.')                         
                # if all functions for this link failed, adaptation has failed
                if not converted:
                    raise AdaptationError('Failed conversion link %s in chain %s'
                                            % (str(link), str(conversions)))
            return outObj
        return convert


def numericPart(s):
    try: return re.match(r'([-+0-9\.]+([eE][-+0-9]+)?)', s).group(1)
    except: return s

def str2float(s):
    """Better float conversion that allows the string value to contain
    an ASCII float value and a units specifier.
    For example: '3.0km' -> 3.0
    """
    return float(numericPart(s))

def float2str(f): return str(f)

_DefaultRegistryTriples = \
    [['str', 'float', float],
     ['str', 'float', str2float],
     ['xs:float', 'float', str2float],
     ['float', 'str', float2str],
     ['str', ElementTree, XML]  # XML function parses xmlDocString and returns an ElementTree object
    ]

# Init global adapt object with default type synonyms and conversion functions
adapt = Adapt().addTypeSynonymsList(_DefaultTypeSynonyms) \
               .addConversions(_DefaultRegistryTriples)

def typeSynonyms(word):
    return adapt._synonyms.synonyms(word)

    
if __name__ == '__main__':
    # simple test
    #from adapt import adapt

    records = """<?xml version='1.0'?>
      <records>
        <record>
          <name>Hoover</name>
          <address>dam</address>
        </record>
        <record>
          <name>YoMama</name>
          <address>In Your Heart</address>
        </record>
      </records>
    """
    def xml2ListOfDict(xml):
        """Convert an xmlDoc string to a python list of dictionaries."""
        return [dict([(child.tag, child.text) for child in elt]) for elt in XML(xml)]

    def xml2ListOfDict_Tutorial(xml):
        """Same as previous function, but the hard (wrong) way."""
        lis = []
        for elt in XML(xml):
            dic = {}
            for child in elt:
                dic[child.tag] = child.text
            lis.append(dic)
        return lis    
    #listOfDict = xml2ListOfDict_Tutorial(records)
    
    def xml2ListOfDict_2step(xml):
        """Same conversion but now input xml must be an ElementTree."""
        return [dict([(child.tag, child.text) for child in elt]) for elt in xml]
        
    #adapt.registerConversion('str', 'py:ListOfDict', xml2ListOfDict)
    # Register only single-step conversion to test seek of 2-step conversion chain:
    # (str -> ElementTree) followed by (ElementTree -> 'py:ListOfDict'    
    adapt.registerConversion(ElementTree, 'py:ListOfDict', xml2ListOfDict_2step)
    
    # Adapt my function and then call it.
    @adapt(ElementTree, 'py:ListOfDict', float)
    def myfn(xmlDoc, xmlFragment, tolerance):
        print xmlDoc, xmlFragment, tolerance

    myfn('<?xml version="1.0"?><tag1><tag2 type="fake">value</tag2></tag1>',
         records,
         '3.0km')
    
    # Save an 'adapted' (wrapped) function.
    '''g = adapt(ElementTree, 'py:ListOfDict', float)(myfn)
    g('<?xml version="1.0"?><tag1><tag2 type="fake">value</tag2></tag1>',
         records,
         '3.0km')
    '''