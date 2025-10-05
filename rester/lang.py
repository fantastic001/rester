
from abc import abstractmethod
from tatsu import compile 

GRAMMAR = """

    start = statements ;
    statements = head:statement tail:statements | head:statement ;
    statement = definition ;

    string = /"[^"]*"/ ;
    identifier = /[a-zA-Z_][a-zA-Z0-9_\\-]*/ ;
    number = /-?\d+(\.\d+)?/ ;
    boolean = "true" | "false" ;
    null = "null" ;
    object = "{"  pairs "}" ;
    pairs = head:pair tail:pairs | head:pair;
    pair = identifier ":" value ;
    array = "[" items:items "]" | "[" "]";
    items = head:value "," tail:items | head:value;
    value = 
        value:string 
        | value:number 
        | value:boolean 
        | value:null 
        | value:object 
        | value:array 
        | value:func_call
        | value:identifier
        ;

    definition = identifier is value ";";

    
    param = 
        "with" name:identifier value:value ;
    params = head:param tail:params | head:param ;


    func_call = 
        name:identifier params:params
        | name:identifier value:value params:params 
        | name:identifier args:args ;
    args = head:value tail:args | head:value;

    is = "is" ;


"""


class IdentifierProvider:
    @abstractmethod
    def provide(self, name):
        raise NotImplementedError()

class Context:
    def __init__(self, providers):
        self.providers = providers
        self.identifiers = {} 
    
    def get(self, name):
        if name in self.identifiers:
            return self.identifiers[name]
        for provider in self.providers:
            value = provider.provide(name)
            if value is not None:
                return value
    
    def __getitem__(self, name):
        return self.get(name)
    
    def __setitem__(self, name, value):
        self.identifiers[name] = value
    
    def items(self):
        all_items = {}
        for provider in self.providers:
            if hasattr(provider, 'items'):
                all_items.update(provider.items())
        all_items.update(self.identifiers)
        return all_items.items()

class HasIdentifier:
    def evaluate(self, context, args, params):
        identifier = args[0].name
        return identifier in context.identifiers

class BuiltinFunctionProvider(IdentifierProvider):
    def provide(self, name):
        import base64
        if name == "base64encode":
            return lambda s: base64.b64encode(s.encode()).decode()
        if name in ["get", "post", "put", "delete"]:
            return lambda *args, **kwargs: {
                "method": name.upper(),
                "args": args,
                "params": kwargs
            }
        return {
            "exists": HasIdentifier()
        }.get(name, None)

class Definition:
    def __init__(self, name, type_def):
        self.name = name
        self.type_def = type_def
    def __repr__(self):
        return f"Definition(name={self.name}, type_def={self.type_def})"

class Constant:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"Constant({self.value})"
    
    def evaluate(self, context: dict):
        return self.value

class Identifier:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"Identifier({self.name})"
    def evaluate(self, context: dict):
        return context[self.name]

class FunctionCall:
    def __init__(self, name, args, params=None):
        self.name = name
        self.args = args
        self.params = params or {}
    def __repr__(self):
        return f"FunctionCall(name={self.name}, args={self.args}, params={self.params})"
    def evaluate(self, context: dict):
        func = context[self.name]
        if hasattr(func, 'evaluate'):
            return func.evaluate(context, self.args, self.params)
        else:
            evaluated_args = [arg.evaluate(context) if hasattr(arg, 'evaluate') else arg for arg in self.args]
            evaluated_params = {k: (v.evaluate(context) if hasattr(v, 'evaluate') else v) for k, v in self.params.items()}
            return func(*evaluated_args, **evaluated_params)

class ObjectExpression:
    def __init__(self, pairs):
        self.pairs = pairs
    def __repr__(self):
        return f"ObjectExpression(pairs={self.pairs})"
    def evaluate(self, context: dict):
        evaluated_pairs = {k: (v.evaluate(context) if hasattr(v, 'evaluate') else v) for k, v in self.pairs.items()}
        return evaluated_pairs



class ResterLangSemantics:
    def string(self, s):
        s = s[1:-1].encode().decode('unicode_escape')
        return Constant(s)

    def identifier(self, id):
        return Identifier(str(id))

    def number(self, n):
        if '.' in n:
            return Constant(float(n))
        else:
            return Constant(int(n))

    def boolean(self, b):
        return Constant(b == 'true')

    def null(self, _):
        return Constant(None)

    def object(self, items):
        pairs = items[1] if len(items) > 2 else []
        return ObjectExpression(dict(pairs))

    def pair(self, ast):
        key, _, value = ast
        return (key.name, value)

    def pairs(self, ast):
        if ast.tail is None:
            return [ast.head]
        else:
            return [ast.head] + ast.tail
    
    def items(self, items):
        if items.tail is None:
            return [items.head]
        else:
            return [items.head] + items.tail

    def array(self, items):
        return list(items.items or [])

    def value(self, v):
        return v.value 


    def definition(self, parts):
        identifier, _, type_def, _ = parts
        name = identifier.name
        return Definition(name, type_def)

    def param(self, parts):
        if parts.value is None:
            return (parts.name.name, None)
        else:
            return (parts.name.name, parts.value)

    def params(self, parts):
        if parts.tail is None:
            return [parts.head]
        else:
            return [parts.head] + parts.tail

    def func_call(self, parts):
        if parts.params is not None:
            params = dict(parts.params)
            if parts.value is not None:
                return FunctionCall(parts.name.name, [parts.value], params)
            else:
                return FunctionCall(parts.name.name, [], params)
        else:
            return FunctionCall(parts.name.name, parts.args, {})

    def args(self, parts):
        if parts.tail is None:
            return [parts.head]
        else:
            return [parts.head] + parts.tail
    
    def statements(self, stmts):
        if stmts.tail is None:
            return [stmts.head]
        else:
            return [stmts.head] + stmts.tail
    
    def statement(self, stmt):
        return stmt
    
    def start(self, stmts):
        return stmts
    
    

parser = compile(GRAMMAR, semantics=ResterLangSemantics())

if __name__ == "__main__":
    import sys 
    f = sys.argv[1]
    with open(f) as fp:
        text = fp.read()
    result = parser.parse(text)
    context = Context(providers=[BuiltinFunctionProvider()])
    for r in result:
        if isinstance(r, Definition):
            print(f"Definition: {r.name} = {r.type_def}")
            context[r.name] = r.type_def
        else:
            print(f"Unknown: {r}")
    print("Context:")
    for k, v in context.items():
        if hasattr(v, 'evaluate'):
            v = v.evaluate(context)
        print(f"  {k}: {v}")