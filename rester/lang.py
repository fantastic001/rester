
from abc import abstractmethod
from ast import FunctionDef
from math import e
import math
import random
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

    def __contains__(self, name):
        if name in self.identifiers:
            return True
        for provider in self.providers:
            value = provider.provide(name)
            if value is not None:
                return True
        return False
    
    def copy(self):
        new_context = Context(self.providers)
        new_context.identifiers = self.identifiers.copy()
        return new_context
    
    def __delitem__(self, name):
        if name in self.identifiers:
            del self.identifiers[name]

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
    def __str__(self) -> str:
        return str(self.value)
    
    def evaluate(self, context: dict):
        return self.value

class Identifier:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"Identifier({self.name})"
    def __str__(self) -> str:
        return self.name
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

# if __name__ == "__main__":
#     import sys 
#     f = sys.argv[1]
#     with open(f) as fp:
#         text = fp.read()
#     result = parser.parse(text)
#     context = Context(providers=[BuiltinFunctionProvider()])
#     for r in result:
#         if isinstance(r, Definition):
#             print(f"Definition: {r.name} = {r.type_def}")
#             context[r.name] = r.type_def
#         else:
#             print(f"Unknown: {r}")
#     print("Context:")
#     for k, v in context.items():
#         if hasattr(v, 'evaluate'):
#             v = v.evaluate(context)
#         print(f"  {k}: {v}")



# following grammar is intented to be used for 
# dynamic operator overloading 

GRAMMAR_OPS = """

    start = statements ;
    statements = head:statement ";" tail:statements | head:statement ;
    string = /"[^"]*"/ ;
    identifier = /[a-zA-Z0-9_]+/ | /[|:=+*\\/<>!@$%^&\\-.]+/ ;
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
        | "(" expr:expression_list ")"
        | x:"(" ")"
        | "{" symbolic_expr:statements "}"
        ;
    expression_list = head:expression "," tail:expression_list | head:expression ;
    expression = first:value rest:expression | first:value ;
    statement = expr:expression | empty:{} ;
"""

class ListExpression:
    def __init__(self, items):
        self.items = items
    def __repr__(self):
        return f"ListExpression({self.items})"
    def evaluate(self, context: dict):
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

class ExpressionList:
    def __init__(self, items):
        self.items = items
    def __repr__(self):
        return f"ExpressionList({self.items})"
    def evaluate(self, context: dict):
        result = [evaluate(context, item) for item in self.items]
        if len(result) == 1:
            return result[0]
        else:
            return result 
    
    def __len__(self):
        return len(self.items)
    
    def __getitem__(self, index):
        return self.items[index]
    
    def __add__(self, other):
        if isinstance(other, ExpressionList):
            return ExpressionList(self.items + other.items)
        elif isinstance(other, list):
            return ExpressionList(self.items + other)
        else:
            raise ValueError("Can only add ExpressionList or list to ExpressionList")

class Expression:
    def __init__(self, parts):
        if isinstance(parts, list):
            self.parts = parts
        else:
            raise ValueError("Expression parts must be a list but got " + str(type(parts)))
    def __repr__(self):
        return ",".join(" ".join(str(t) for t in part) for part in self.parts)
    

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
        if v.symbolic_expr is not None:
            return Expression(v.symbolic_expr)
        if v.expr is not None:
            return v.expr
        if v.value is not None:
            return v.value
        else:
            return ExpressionList([])
    
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

    def expression_list(self, parts):
        if parts.tail is None:
            return ExpressionList([parts.head])
        else:
            return ExpressionList([parts.head]) + parts.tail

    def statements(self, stmts):
        if stmts.tail is None:
            return [stmts.head] if stmts.head is not None else []
        else:
            return [stmts.head] + stmts.tail if stmts.head is not None else stmts.tail
    
    def statement(self, stmt):
        return stmt.expr if stmt.expr is not None else None
    
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
                    op = context.get(expr[i].name)
                    if op is None:
                        continue
                    if isinstance(op, tuple):
                        op, precedence = op
                    elif isinstance(op, Operator):
                        precedence = 100
                    else:
                        continue
                    if precedence < min_precedence:
                        min_precedence = precedence
                        op_index = i
                        min_op = op
            if op_index == -1 and len(expr) == 1:
                return evaluate(context, expr[0])
            if op_index == -1:
                return [evaluate(context, e) for e in expr]
            left = expr[:op_index]
            right = expr[op_index+1:]
            if not min_op:
                raise ValueError(f"Operator {expr[op_index].name} not found in context")
            if hasattr(min_op, "evaluate"):
                return min_op.evaluate(context, left, right)
            else:
                left_evaluated = evaluate(context, left)
                right_evaluated = evaluate(context, right)
                if left_evaluated is not None and right_evaluated is not None:
                    if isinstance(left_evaluated, list) and not isinstance(right_evaluated, list):
                        return [min_op(item, right_evaluated) for item in left_evaluated]
                    elif isinstance(right_evaluated, list) and not isinstance(left_evaluated, list):
                        return [min_op(left_evaluated, item) for item in right_evaluated]
                    else:
                        return min_op(left_evaluated, right_evaluated)
                else:
                    if isinstance(left_evaluated, list):
                        return min_op(*left_evaluated)
                    elif isinstance(right_evaluated, list):
                        return min_op(*right_evaluated)
                    else:
                        return min_op(left_evaluated, right_evaluated)

    else:
        if hasattr(expr, 'evaluate'):
            return expr.evaluate(context)
        else:
            return expr
        
EXAMPLE = """


"""

class Operator:
    pass 

class Id:
    def evaluate(self, context, left, right):
        if len(left) > 0:
            raise ValueError("Left side of operator id has to be empty")
        args = evaluate(context, right)
        if args is None:
            raise ValueError("arguments of id evaluate to nothing")
        if len(args) != 1:
            raise ValueError("Number of arguments of id operator must be 1")
        if not isinstance(args[0], str):
            raise ValueError("Argument of id operator must be string")
        identifier = args[0]
        return Identifier(identifier)
        

class ExprEval:
    
    def evaluate(self, context, left, right):
        if left:
            raise ValueError("Left side of $ operator must be empty")
        if right and len(right) == 1:
            e = evaluate(context, right[0])
            local_context = context.copy()
            result = evaluate(local_context, e.parts)
            if isinstance(result, list):
                return result[-1] if result else None
            return result
        else:
            raise ValueError("Right side of $ operator must be a single Expression")

class ContextExtraction():
    def evaluate(self, context, left, right):
        if len(left) == 0:
            my_context = context.copy()
            expr = evaluate(my_context, right[0].parts) 
            return my_context.identifiers
        if len(left) != 1:
            raise ValueError("Left side of context extraction must be a single identifier name")
        if not right or len(right) != 1:
            raise ValueError("Right side of context extraction must be a single expression")
        if not isinstance(right[0], Expression):
            raise ValueError("Right side of context extraction must be an Expression")
        my_context = context.copy()
        identifier = evaluate(my_context, left[0])
        expr = evaluate(my_context, right[0])
        if isinstance(identifier, str):
            result = evaluate(my_context, expr.parts)
            return my_context[identifier]
        elif isinstance(identifier, Expression):
            result = evaluate(my_context, expr.parts)
            return evaluate(my_context, identifier.parts)

class Identifiers():
    def evaluate(self, context, left, right):
        left = evaluate(context, left)
        right = evaluate(context, right)
        if right is None:
            raise ValueError("Right side of identifiers() must be an Expression or empty")
        if left:
            raise ValueError("Left side of identifiers() must be empty")
        if len(right) == 0:
            return ListExpression(context.identifiers.keys())
        elif len(right) == 1:
            if not isinstance(right[0], Expression):
                raise ValueError("Right side of identifiers() must be an Expression or empty")
            my_context = context.copy()
            expr = evaluate(my_context, right[0].parts)
            return ListExpression([k for k, v in my_context.items() if not k in context.identifiers])


class FunDef(Operator):
    def evaluate(self, context, left, right):
        print("Left: %s" % left)
        if isinstance(left[0], ExpressionList):
            arguments = [x[0].name  for x in  left[0].items]
        else:
            arguments = [x.name for x in left[0]]
        if len(right) == 1 and isinstance(right[0], Expression):
            body = right[0].parts
        else:
            body = right 
        class Execution(Operator):
            def __init__(self, args, bindings=None):
                self.bindings = bindings or {}
                self.arguments = args
                for arg in args:
                    if arg in self.bindings:
                        del self.bindings[arg]
            def evaluate(self, ctx, left=None, right=None):
                ctx = self.bindings
                if left is None and right is None:
                    return Execution(self.arguments, ctx.copy())
                assert len(left) == 0 
                if isinstance(right[0], ExpressionList):
                    vals = right[0].items
                else:
                    vals = right[0]
                 
                

            
                evals = [evaluate(context, val) for val in vals]
                
                if len(evals) > len(self.arguments):
                    raise ValueError("Too many arguments provided to function")
                for arg, val in zip(self.arguments, evals):
                    if arg not in ctx:
                        ctx[arg] = val
                unassigned = [arg for arg in self.arguments if arg not in ctx]
                if not unassigned:
                    return evaluate(ctx, body)
                else:
                    return Execution(unassigned, ctx.copy())
            def __repr__(self):
                result =  "(%s) -> %s" % (
                    ", ".join(self.arguments),
                    str(body)
                )
                return result
        return Execution(arguments, context.copy())


class Access(Operator):
    def evaluate(self, context, left, right):
        assert len(right) == 1
        left = evaluate(context, left)
        identifier = right[0].name 
        result = evaluate(context, left)
        if result is not None:
            return result[identifier]

if __name__ == "__main__":
    import sys 
    f = sys.argv[1] if len(sys.argv) > 1 else None
    if f:
        with open(f) as fp:
            text = fp.read()
    else:
        text = EXAMPLE
    result = parser_ops.parse(text)
    context = Context(providers=[BuiltinFunctionProvider()])
    # define operators in context
    context["+"] = (lambda a, b: a + b if a else b, 10)
    context["-"] = (lambda a, b: a - b if a else -b, 10)
    context["*"] = (lambda a, b: a * b if a else 0, 20)
    context["/"] = (lambda a, b: a / b if a else 1, 20)
    context["sum"] = (lambda *lst: sum(lst) if lst else 0, 30)
    context["."] = (Access(), 999)
    class Assignment:
        def evaluate(self, context, left, right):
            if len(left) != 1:
                left = evaluate(context, left)
                if not isinstance(left, Identifier):
                    raise ValueError("Left side of assignment must be a single identifier")
            else:
                left = left[0]
            if not isinstance(left, Identifier):
                raise ValueError("Left side of assignment must be an identifier")
            right_value = evaluate(context, right)
            context[left.name] = right_value
            print(f"Assigned {left.name} = {repr(right_value)}")
            return right_value

    context["="] = (Assignment(), 0)
    context["$"] = (ExprEval(), 1000)
    context["@"] = (ContextExtraction(), 1000)
    context["identifiers"] = (Identifiers(), 100)
    context["id"] = (Id(), 100)
    context["random"] = (lambda: random.random(), 100)
    context["->"] = (FunDef(), 5)
    print("Parsed result:")
    for r in result:
        if hasattr(r, 'evaluate'):
            value = evaluate(context, r)
        elif isinstance(r, list) or isinstance(r, tuple):
            value = evaluate(context, r)
        else:
            print(f"Unknown: {r}")
    print("Context:")
    for k, v in context.items():
        if hasattr(v, 'evaluate'):
            v = v.evaluate(context)
        if isinstance(v, list):
            v = evaluate(context, v)
        print(f"  {k}: {v}")