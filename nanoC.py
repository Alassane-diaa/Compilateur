
import sys
import struct
from typing import Literal
import ast
import lark

cpt = 0
bounds_cpt = 0
string_literals: dict[str, str] = {}

grammaire = lark.Lark("""
IDENTIFIER: /[a-zA-Z_][a-zA-Z_0-9]*/
CHAR: /'([^"\\\\]|\\\\.)'/
STRING: /"([^"\\\\]|\\\\.)*"/
BOOL.2: "true" | "false"
FLOAT: /-?[0-9]+\\.[0-9]+([eE][+-]?[0-9]+)?/ | /-?[0-9]+[eE][+-]?[0-9]+/
BASE_TYPE.2: "int" | "char" | "string" | "bool" | "float"
BRACKET: "[]"
OPBIN: /[+\\-*\\/<>%]/ | "==" | "<" | ">" | "<=" | ">="

type_expr: BASE_TYPE (BRACKET | "[" expression "]")* -> type_expr
decl: type_expr IDENTIFIER -> declaration

expression: IDENTIFIER -> variable 
          | FLOAT -> float_expr
          | SIGNED_NUMBER -> entier
          | BOOL -> bool
          | CHAR -> char
          | STRING -> string
          | "charAt" "(" expression "," expression ")" -> char_at
          | "len" "(" expression ")" -> len_expr  
          | "(" BASE_TYPE ")" expression -> cast
          | "(" expression ")" -> paren
          | expression OPBIN expression -> binaire
          | "{" (expression ",")* expression "}" -> tableau
          | expression "[" expression "]" -> index

lhs: IDENTIFIER -> variable
    | lhs "[" expression "]" -> index

for_step: lhs "=" expression -> assignation

commande: lhs "=" expression ";" -> assignation
        | type_expr IDENTIFIER ";"-> declaration
        | type_expr lhs "=" expression ";" -> declaration_assignation
        | "print" "(" expression ")" ";" -> print
        | "if" "(" expression ")" "{" commande "}" -> if
        | "while" "(" expression ")" "{" commande "}" -> while
        | "for" "(" commande expression ";" for_step ")" "{" commande "}" -> for
        | (commande)* commande -> sequence
        | "pass" -> pass

main: "main" "(" "int" "argc" "," "char*" "argv" ")" "{" commande "return" "(" expression ")" ";" "}"       

COMMENT: "//" /[^\\n]*/

%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
%ignore COMMENT
""", start="main")

op2asm = {"+": "add rax, rbx", "-": "sub rax, rbx", "*": "imul rax, rbx",
          "<": "setl", ">": "setg", "<=": "setle", ">=": "setge", "==": "sete"}

float_op2asm = {"+": "addsd", "-": "subsd", "*": "mulsd", "/": "divsd"}

float_cmp2asm = {"<": "setb", ">": "seta", "<=": "setbe", ">=": "setae", "==": "sete"}

string_id_to_value = {}
var_types = {}
var_declared_size = {}
declared_vars: set[str] = set()

def _type_str(type_node) -> str:
    base = type_node.children[0].value
    brackets = "[]" * (len(type_node.children) - 1)
    return base + brackets

def _type_sizes(type_node) -> list:
    sizes = []
    for child in type_node.children[1:]:
        if hasattr(child, "data"):
            sizes.append(child)
        else:
            sizes.append(None)
    return sizes

def _eval_const_string(expr):
    if expr.data == "string" or expr.data == "char":
        return ast.literal_eval(expr.children[0].value)
    if expr.data == "variable":
        return string_id_to_value.get(expr.children[0].value)
    if expr.data == "binaire" and expr.children[1].value == "+":
        left = _eval_const_string(expr.children[0])
        right = _eval_const_string(expr.children[2])
        if left is not None and right is not None:
            return left + right
    return None

def _is_array_type(vartype: str) -> bool:
    return "[]" in vartype

def _array_element_type(vartype: str) -> str:
    if vartype.endswith("[]"):
        return vartype[:-2]
    return vartype

def _decls_for_var(varname: str, vartype: str) -> str:
    if varname in declared_vars:
        return ""
    declared_vars.add(varname)
    return f"\n{varname} : dq 0"

def expr_type(expr) -> str:
    binaire_type = {
        "+": {"int_int": "int", "string_string": "string", "char_char": "char", 
              "int_char": "int", "char_int": "int", "float_float": "float", 
              "float_int": "float", "int_float": "float", "float_char": "float", "char_float": "float"},
        "-": {"int_int": "int", "float_float": "float", "float_int": "float", "int_float": "float"},
        "*": {"int_int": "int", "float_float": "float", "float_int": "float", "int_float": "float"},
        "/": {"int_int": "int", "float_float": "float", "float_int": "float", "int_float": "float"},
        "==": {"bool_bool": "bool", "char_char": "bool", "int_int": "bool", "float_float": "bool", "string_string": "bool_str"},
        "<": {"int_int": "bool", "float_float": "bool"},
        ">": {"int_int": "bool", "float_float": "bool"},
        "<=": {"int_int": "bool", "float_float": "bool"},
        ">=": {"int_int": "bool", "float_float": "bool"}
    }
    
    if expr.data == "entier": return "int"
    if expr.data == "float_expr": return "float"
    if expr.data == "char": return "char"
    if expr.data == "bool": return "bool"
    if expr.data == "string": return "string"
    if expr.data == "char_at": return "char"
    if expr.data == "len_expr": return "int"
    if expr.data == "cast": return expr.children[0].value
    if expr.data == "paren": return expr_type(expr.children[0])
    
    if expr.data == "variable":
        name = expr.children[0].value
        if name not in var_types:
            raise NameError(f"Erreur fatale: Variable non declaree '{name}'")
        return var_types[name]
        
    if expr.data == "binaire":
        e_left, e_op, e_right = expr.children[0], expr.children[1].value, expr.children[2]
        if e_op == "%" and (expr_type(e_left) == "float" or expr_type(e_right) == "float"):
            raise TypeError("Erreur de type : L'operateur modulo '%' est interdit sur les flottants.")
            
        key = f"{expr_type(e_left)}_{expr_type(e_right)}"
        if e_op in binaire_type and key in binaire_type[e_op]:
            return binaire_type[e_op][key]
        return "int"
        
    if expr.data == "index":
        base_name = _base_name(expr.children[0])
        if base_name == "argv": return "string"
        return _array_element_type(expr_type(expr.children[0]))
        
    if expr.data == "tableau":
        if not expr.children: return "void[]"
        return expr_type(expr.children[0]) + "[]"
    return "int"

def register_string_literal(token_value: str) -> str:
    literal_value = ast.literal_eval(token_value)
    if literal_value not in string_literals:
        string_literals[literal_value] = f"str_{len(string_literals)}"
    return string_literals[literal_value]

def escape_nasm_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')

def _base_name(ast) -> str:
    if ast.data == "variable": return ast.children[0].value
    if ast.data == "index": return _base_name(ast.children[0])
    return ""

def _lhs_name(ast) -> str:
    if ast.data == "variable": return ast.children[0].value
    if ast.data == "index": return _base_name(ast)
    return ""

def asm_expression(e):
    if e.data == "variable": return f"mov rax, [{e.children[0].value}]"
    if e.data == "entier": return f"mov rax, {e.children[0].value}"
    
    if e.data == "float_expr":
        f_val = float(e.children[0].value)
        hex_val = hex(struct.unpack('<Q', struct.pack('<d', f_val))[0])
        return f"mov rax, {hex_val}"
        
    if e.data == "char": return f"mov rax, {ord(e.children[0].value[1])}"
    if e.data == "bool": return f"mov rax, {'1' if e.children[0].value=='true' else '0'}"
    if e.data == "string":
        label = register_string_literal(e.children[0].value)
        return f"lea rax, [rel {label}]"
        
    if e.data == "paren": return asm_expression(e.children[0])

    if e.data == "cast":
        target_type = e.children[0].value
        inner_type = expr_type(e.children[1])
        inner_asm = asm_expression(e.children[1])
        
        if inner_type == "int" and target_type == "float":
            return f"{inner_asm}\ncvtsi2sd xmm0, rax\nmovq rax, xmm0"
        if inner_type == "float" and target_type == "int":
            return f"{inner_asm}\nmovq xmm0, rax\ncvttsd2si rax, xmm0"
        return inner_asm 
        
    if e.data == "index":
        base_asm = asm_expression(e.children[0])
        idx_asm = asm_expression(e.children[1])
        return f"{base_asm}\npush rax\n{idx_asm}\npop rbx\nimul rax, 8\nadd rax, rbx\nmov rax, [rax]"

    if e.data == "tableau":
        size = len(e.children)
        asm = f"mov rdi, {size}\nmov rsi, 8\ncall calloc\npush rax"
        for i, child in enumerate(e.children):
            child_asm = asm_expression(child)
            asm += f"\n{child_asm}\npop rbx\nmov [rbx + {i*8}], rax\npush rbx"
        asm += "\npop rax"
        return asm

    if e.data == "binaire":
        e_left, e_op, e_right = e.children[0], e.children[1], e.children[2]
        res_type = expr_type(e)
        type_l, type_r = expr_type(e_left), expr_type(e_right)
        
        asm_l = asm_expression(e_left)
        asm_r = asm_expression(e_right)

        if res_type == "bool" and type_l == "float" and type_r == "float":
            return f"{asm_l}\npush rax\n{asm_r}\nmovq xmm1, rax\npop rax\nmovq xmm0, rax\nucomisd xmm0, xmm1\n{float_cmp2asm.get(e_op.value, 'sete')} al\nmovzx rax, al"

        if res_type == "float" and (type_l == "int" or type_r == "int"):
            conv_l = "cvtsi2sd xmm0, rax\nmovq rax, xmm0" if type_l == "int" else ""
            conv_r = "cvtsi2sd xmm0, rax\nmovq rax, xmm0" if type_r == "int" else ""
            return f"{asm_l}\n{conv_l}\npush rax\n{asm_r}\n{conv_r}\nmovq xmm1, rax\npop rax\nmovq xmm0, rax\n{float_op2asm.get(e_op.value, 'addsd')} xmm0, xmm1\nmovq rax, xmm0"

        if res_type == "float" and type_l == "float" and type_r == "float":
            return f"{asm_l}\npush rax\n{asm_r}\nmovq xmm1, rax\npop rax\nmovq xmm0, rax\n{float_op2asm.get(e_op.value, 'addsd')} xmm0, xmm1\nmovq rax, xmm0"

        return f"{asm_l}\npush rax\n{asm_r}\nmov rbx, rax\npop rax\n{op2asm.get(e_op.value, 'add rax, rbx')}"

    return ""

def asm_lhs(ast) -> tuple[str, str]:
    if ast.data == "variable":
        return "", ast.children[0].value
    return "", ""

def asm_commande(c) -> tuple[str, str]:
    global cpt
    decls = ""
    
    if c.data == "declaration":
        vartype, varname = _type_str(c.children[0]), c.children[1].value
        var_types[varname] = vartype
        return "nop", _decls_for_var(varname, vartype)
        
    if c.data == "declaration_assignation":
        vartype = _type_str(c.children[0])
        varname = _lhs_name(c.children[1])
        var_types[varname] = vartype
        exp = c.children[2]
        
        current_type = expr_type(exp)
        if vartype != current_type and not (vartype=="int" and current_type=="float"): 
            pass 

        pre, addr = asm_lhs(c.children[1])
        decls += _decls_for_var(addr, vartype)
        
        asm_exp = asm_expression(exp)
        if current_type == "float" and vartype == "int":
            asm_exp += "\nmovq xmm0, rax\ncvttsd2si rax, xmm0"
            
        return f"{pre}{asm_exp}\nmov [{addr}], rax", decls

    if c.data == "print":
        expr = c.children[0]
        asm_expr = asm_expression(expr)
        type_pr = expr_type(expr)
        
        if type_pr == "float":
            return f"{asm_expr}\nmovq xmm0, rax\nmov rdi, format_float\nmov rax, 1\ncall printf\n", decls
        elif type_pr == "string": _format = "format_str"
        elif type_pr == "char": _format = "format_char"
        else: _format = "format_int"
        
        return f"{asm_expr}\nmov rdi, {_format}\nmov rsi, rax\nxor rax, rax\ncall printf\n", decls
        
    if c.data == "sequence":
        d_cmd, d_decls = asm_commande(c.children[0])
        tail_cmd, tail_decls = asm_commande(c.children[1])
        return f"{d_cmd}\n{tail_cmd}", decls + d_decls + tail_decls
        
    return "nop", decls

def asm_main(ast):
    var_types["argc"] = "int"
    var_types["argv"] = "string*"
    decls = "\n".join((_decls_for_var("argc", "int"), _decls_for_var("argv", "string*")))
    cmd, decls_body = asm_commande(ast.children[0])
    ret = asm_expression(ast.children[1])
    
    with open("squelette.asm", "r") as f:
        squelette = f.read()
        
    string_decls = "\n".join(f'{label}: db "{escape_nasm_string(value)}", 0' for value, label in string_literals.items())
    
    string_decls += '\nformat_float: db "%f", 10, 0'
    
    all_decls = "\n".join(part for part in (decls, decls_body, string_decls) if part)
    squelette = squelette.replace("DECL_VARS", all_decls)
    squelette = squelette.replace("INIT_VARS", "mov [argc], rdi\nmov [argv], rsi")
    squelette = squelette.replace("COMMAND", cmd)
    squelette = squelette.replace("RETURN", ret)
    return squelette

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Erreur : Aucun fichier source fourni.")
        sys.exit(1)
        
    fichier_cible = sys.argv[1]
    with open(fichier_cible, "r") as f:
        src = f.read()
        
    t = grammaire.parse(src)
    with open("resultat.asm", "w") as f:
        f.write(asm_main(t))

