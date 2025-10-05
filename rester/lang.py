
from tatsu import compile 

GRAMMAR = """

    start = statements ;
    statements = head:statement tail:statements | head:statement ;
    statement = global_statement | definition ;

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
        | "(" value:expression ")"
        | value:identifier
        ;

    global_statement = "global" identifier "is" value  ;
    definition = identifier is type "end";

    
    method_type = "GET" | "POST" | "PUT" | "DELETE" | "PATCH" ;
    param = 
        "with" name:identifier value:value ;
    params = head:param tail:params | head:param ;
    request_type = 
          "request" method_type string params
        | "request" method_type string
        ;
                    

    type = request_type ;

    func_call = identifier args ;
    args = head:value tail:args | head:value;
    expression = func_call | value | identifier ;
    assignment = identifier "=" expression ;

    is = "is" ;


"""

class GlobalStatement:
    def __init__(self, name, value):
        self.name = name
        self.value = value
    def __repr__(self):
        return f"GlobalStatement(name={self.name}, value={self.value})"
    
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
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"FunctionCall(name={self.name}, args={self.args})"
    def evaluate(self, context: dict):
        func = context[self.name]
        evaluated_args = [arg.evaluate(context) if hasattr(arg, 'evaluate') else arg for arg in self.args]
        return func(*evaluated_args)

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

    def global_statement(self, parts):
        _, name, _, value = parts
        return GlobalStatement(name, value)

    def definition(self, parts):
        name, _, type_def, _ = parts
        return Definition(name, type_def)

    def method_type(self, method):
        return method

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

    def request_type(self, parts):
        _, method, url, *params = parts
        params_dict = {}
        for p in params:
            if isinstance(p, list):
                for subp in p:
                    key = subp[0]
                    if key in params_dict:
                        if isinstance(params_dict[key], list):
                            params_dict[key].append(subp[1])
                        else:
                            params_dict[key] = [params_dict[key], subp[1]]
                    else:
                        params_dict[key] = subp[1]
            else:
                key = p[0]
                if key in params_dict:
                    if isinstance(params_dict[key], list):
                        params_dict[key].append(p[1])
                    else:
                        params_dict[key] = [params_dict[key], p[1]]
                else:
                    params_dict[key] = p[1]
        return ('request', method, url, params_dict)

    def type(self, t):
        return t
    def func_call(self, parts):
        func_name = parts[0]
        args = parts[1]
        return FunctionCall(func_name.name, args)
    
    def expression(self, expr):
        return expr
    
    def assignment(self, parts):
        var_name, _, expr = parts
        return ('assignment', var_name, expr)
    
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
    context = {} 
    for r in result:
        if isinstance(r, GlobalStatement):
            print(f"Global: {r.name} = {r.value}")
            context[r.name] = r.value.evaluate(context) if hasattr(r.value, 'evaluate') else r.value
        elif isinstance(r, Definition):
            print(f"Definition: {r.name} = {r.type_def}")
            context[r.name] = r.type_def
        else:
            print(f"Unknown: {r}")
    print("Context:")
    for k, v in context.items():
        if hasattr(v, 'evaluate'):
            v = v.evaluate(context)
        print(f"  {k}: {v}")