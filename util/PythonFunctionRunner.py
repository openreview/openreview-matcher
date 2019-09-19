import openreview
# The list of symbols that are included by default in the generated
# function's environment
SAFE_SYMBOLS = ["list", "dict", "tuple", "set", "long", "float", "object", "print",
                "bool", "callable", "True", "False", "dir",
                "frozenset", "getattr", "hasattr", "abs", "cmp", "complex",
                "divmod", "id", "pow", "round", "slice", "vars",
                "hash", "hex", "int", "isinstance", "issubclass", "len",
                "map", "filter", "max", "min", "oct", "chr", "ord", "range",
                "reduce", "repr", "str", "type", "zip", "xrange", "None",
                "Exception", "KeyboardInterrupt"]


# Also add the standard exceptions
__bi = __builtins__
if type(__bi) is not dict:
    __bi = __bi.__dict__
for k in __bi:
    if k.endswith("Error") or k.endswith("Warning"):
        SAFE_SYMBOLS.append(k)
del __bi

class PythonFunctionRunner:
    """
    TODO:  In order to work with openreview API, this needs to be passed an or_client object.
    """

    def __init__ (self, lambda_def, symbol_dict={}):
        self._additional_symbols_dict = symbol_dict
        self.fn = self._parse_lambda(lambda_def)


    def run_function (self, arg):
        return self.fn(arg)


    # expecting expression of the form: lambda x: python code
    def _parse_lambda (self, lambda_def):
        lambda_def = lambda_def.strip()
        colon_loc =  lambda_def.index(':')
        prototype = lambda_def[:colon_loc] # e.g. 'lambda x, y, z'
        body = lambda_def[colon_loc+1:]
        args = prototype[7:].strip() # e.g. 'x, y, z'
        return self._createFunction(body, args, self._additional_symbols_dict)

    # from: http://code.activestate.com/recipes/550804-create-a-restricted-python-function-from-a-string/
    def _createFunction(self, sourceCode, args="", additional_symbols=dict()):
        """
        Create a python function from the given source code which is in the form:
        lambda x,y:
            statement
            statement
            ...
        The above is not a legal Python lambda but it makes more sense than taking a named function defined with def because our calling context
        is better with an anonymous function than a named one and this lambda formulation conveys that.  The really problematic issue with these
        is that editing the lambda definitions within a text area that edits JSON (where the lambda is a field in the JSON) is a nightmare because
        indentation is lost by the current UI which makes it impossible to edit python functions in a text area (which is what the rest of the configuration note
        can be edited with).   So this is a feature that is not in use and will probably go away, but I leave here just in case.... DM 7/19

        :param sourceCode A python string containing the core of the
        function. Might include the return statement (or not), definition of
        local functions, classes, etc. Indentation matters !

        :param args The string representing the arguments to put in the function's
        prototype, such as "a, b", or "a=12, b",
        or "a=12, b=dict(akey=42, another=5)"

        :param additional_symbols A dictionary variable name =>
        variable/funcion/object to include in the generated function's
        closure

        The sourceCode will be executed in a restricted environment,
        containing only the python builtins that are harmless (such as map,
        hasattr, etc.). To allow the function to access other modules or
        functions or objects, use the additional_symbols parameter. For
        example, to allow the source code to access the re and sys modules,
        as well as a global function F named afunction in the sourceCode and
        an object OoO named ooo in the sourceCode, specify:
            additional_symbols = dict(re=re, sys=sys, afunction=F, ooo=OoO)

        \return A python function implementing the source code. It can be
        recursive: the (internal) name of the function being defined is:
        __TheFunction__. Its docstring is the initial sourceCode string.

        Tests show that the resulting function does not have any calling
        time overhead (-3% to +3%, probably due to system preemption aleas)
        compared to normal python function calls.
        """
        # Include the sourcecode as the code of a function __TheFunction__:
        s = "def __TheFunction__(%s):\n" % args
        s += "\t" + "\n\t".join(sourceCode.split('\n')) + "\n"

        # Byte-compilation (optional)
        byteCode = compile(s, "<string>", 'exec')

        # Setup the local and global dictionaries of the execution
        # environment for __TheFunction__
        bis   = dict() # builtins
        globs = dict()
        locs  = dict()

        # Setup a standard-compatible python environment
        bis["locals"]  = lambda: locs
        bis["globals"] = lambda: globs
        globs["__builtins__"] = bis
        globs["__name__"] = "SUBENV"
        globs["__doc__"] = sourceCode

        # Determine how the __builtins__ dictionary should be accessed
        if type(__builtins__) is dict:
            bi_dict = __builtins__
        else:
            bi_dict = __builtins__.__dict__

        # Include the safe symbols
        for k in SAFE_SYMBOLS:
            # try from current locals
            try:
                locs[k] = locals()[k]
                continue
            except KeyError:
                pass
            # Try from globals
            try:
                globs[k] = globals()[k]
                continue
            except KeyError:
                pass
            # Try from builtins
            try:
                bis[k] = bi_dict[k]
            except KeyError:
                # Symbol not available anywhere: silently ignored
                pass

        # Include the symbols added by the caller, in the globals dictionary
        globs.update(additional_symbols)

        # Finally execute the def __TheFunction__ statement:
        eval(byteCode, globs, locs)
        # As a result, the function is defined as the item __TheFunction__
        # in the locals dictionary
        fct = locs["__TheFunction__"]
        # Attach the function to the globals so that it can be recursive
        del locs["__TheFunction__"]
        globs["__TheFunction__"] = fct
        # Attach the actual source code to the docstring
        fct.__doc__ = sourceCode
        return fct

class ORFunctionRunner (PythonFunctionRunner):
    '''
    A function runner that will build/run functions that can access OpenReview.
    '''

    def __init__ (self, lambda_def, or_client):
        # provide access to the openreview package and bind an or_client variable to openreview.Client object
        super().__init__(lambda_def, symbol_dict={'openreview': openreview, 'or_client': or_client})

    # Add to the additional_symbols_dict that gets passed to the createFunction method.
    # The symbols in the dictionary will allow the lambda function reference the openreview package, the or-client variable
    # which is bound to an openreview.Client, and forum_id and reviewer.
    def add_additional_symbols_dict (self, forum_id, reviewer):
        if forum_id:
            self._additional_symbols_dict['forum_id'] = forum_id
        if reviewer:
            self._additional_symbols_dict['reviewer'] = reviewer