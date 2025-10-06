
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
        return None
    
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



# following grammar is intented to be used for 
# dynamic operator overloading 

GRAMMAR_OPS = """

    start = statements ;
    statements = head:statement tail:statements | head:statement ;
    string = /"[^"]*"/ ;
    identifier = /[a-zA-Z0-9_]+/ | /[|:=+*\\/<>!\\-]+/ ;
    number = /[0-9]+/ | /[0-9]*\\.[0-9]+/ ;
    boolean = "true" | "false" ;
    null = "null" ;
    array = "[" list:items "]" | x:"[" "]";
    items = head:expression "," tail:items | head:expression;
    value =
        value:string 
        | value:number 
        | value:boolean 
        | value:null 
        | value:array
        | value:identifier
        | "(" expr:expression ")"
        ;
    expression = first:value rest:expression | first:value ;
    statement = expr:expression ";" ;
"""

class ListExpression:
    def __init__(self, items):
        self.items = items
    def __repr__(self):
        return f"ListExpression({self.items})"
    def evaluate(self, context: dict):
        print("Evaluating ListExpression with items:", self.items)
        return ListExpression([evaluate(context, item) for item in self.items])
    
    def __len__(self):
        return len(self.items)
    
    def __add__(self, other):
        if isinstance(other, ListExpression):
            return ListExpression(self.items + other.items)
        elif isinstance(other, list):
            return ListExpression(self.items + other)
        else:
            raise ValueError("Can only add ListExpression or list to ListExpression")

class CustomOpSemantics:
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

    def value(self, v):
        return v.value if v.value else v.expr
    
    def items(self, items):
        if items.tail is None:
            return [items.head]
        else:
            return [items.head] + items.tail
    
    def array(self, items):
        return ListExpression(items.list or [])

    def expression(self, parts):
        left = parts.first
        right = parts.rest or [] 
        return [left] + right

    def statements(self, stmts):
        if stmts.tail is None:
            return [stmts.head]
        else:
            return [stmts.head] + stmts.tail
    
    def statement(self, stmt):
        return stmt.expr
    
    def start(self, stmts):
        return stmts

parser_ops = compile(GRAMMAR_OPS, semantics=CustomOpSemantics())

def evaluate(context, expr):
    if isinstance(expr, list) or isinstance(expr, tuple):
        if not expr:
            return None
        if len(expr) == 1:
            return evaluate(context, expr[0])
        else:
            # find operator with highest precedence
            min_precedence = 1000000
            op_index = -1
            min_op = None
            for i in range(len(expr)):
                if isinstance(expr[i], Identifier):
                    print(f"Found operator: {expr[i].name}")
                    op = context.get(expr[i].name)
                    if op is None:
                        print(f"Warning: Operator {expr[i].name} not found in context, skipping")
                        continue
                    if isinstance(op, tuple):
                        op, precedence = op
                    else:
                        print(f"Warning: Operator {expr[i].name} has no precedence defined, skipping")
                        continue
                    if precedence < min_precedence:
                        min_precedence = precedence
                        op_index = i
                        min_op = op
            print("Operator selected:", expr[op_index] if op_index != -1 else None)
            if op_index == -1 and len(expr) == 1:
                return evaluate(context, expr[0])
            if op_index == -1:
                raise ValueError("No operator found in expression:" + str(expr))
            left = expr[:op_index]
            right = expr[op_index+1:]
            if not min_op:
                raise ValueError(f"Operator {expr[op_index].name} not found in context")
            if hasattr(min_op, "evaluate"):
                return min_op.evaluate(context, left, right)
            else:
                left_evaluated = evaluate(context, left)
                right_evaluated = evaluate(context, right)
                return min_op(left_evaluated, right_evaluated)

    else:
        if hasattr(expr, 'evaluate'):
            return expr.evaluate(context)
        else:
            return expr
        
EXAMPLE = """
a = [1, 2, 3];
b = a + [4, 5];
"""
# if __name__ == "__main__":
#     import sys 
#     f = sys.argv[1] if len(sys.argv) > 1 else None
#     if f:
#         with open(f) as fp:
#             text = fp.read()
#     else:
#         text = EXAMPLE
#     result = parser_ops.parse(text)
#     context = Context(providers=[BuiltinFunctionProvider()])
#     # define operators in context
#     context["+"] = (lambda a, b: a + b if a else b, 10)
#     context["-"] = (lambda a, b: a - b if a else -b, 10)
#     context["*"] = (lambda a, b: a * b if a else 0, 20)
#     context["/"] = (lambda a, b: a / b if a else 1, 20)

#     class Assignment:
#         def evaluate(self, context, left, right):
#             if len(left) != 1:
#                 raise ValueError("Left side of assignment must be a single identifier")
#             if not isinstance(left[0], Identifier):
#                 raise ValueError("Left side of assignment must be an identifier")
#             right_value = evaluate(context, right)
#             context[left[0].name] = right_value
#             return right_value

#     context["="] = (Assignment(), 0)
#     print("Parsed result:")
#     for r in result:
#         print(f"  {r}")
#     print("Evaluating...")
#     for r in result:
#         print(f"Evaluating: {r}")
#         if hasattr(r, 'evaluate'):
#             value = evaluate(context, r)
#             print(f"Expression result: {value}")
#         elif isinstance(r, list) or isinstance(r, tuple):
#             value = evaluate(context, r)
#             print(f"Expression result: {value}")
#         else:
#             print(f"Unknown: {r}")
#     print("Context:")
#     for k, v in context.items():
#         if hasattr(v, 'evaluate'):
#             v = v.evaluate(context)
#         if isinstance(v, list):
#             v = evaluate(context, v)
#         print(f"  {k}: {v}")