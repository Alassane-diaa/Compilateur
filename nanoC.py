from typing import Literal

import ast
import lark

cpt = 0
string_literals: dict[str, str] = {}

grammaire = lark.Lark("""
IDENTIFIER: /[a-zA-Z_][a-zA-Z_0-9]*/
CHAR: /'([^"\\\\]|\\\\.)'/
STRING: /"([^"\\\\]|\\\\.)*"/
TYPE: "int" | "char" | "string"
OPBIN: /[+\\-*\\/<>%]/
decl: TYPE IDENTIFIER -> declaration
expression: IDENTIFIER -> variable 
          | SIGNED_NUMBER -> entier
          | CHAR -> char
          | STRING -> string
          | expression OPBIN expression -> binaire
          | "{" (expression ",")* expression "}" -> tableau
          | expression "[" expression "]" -> index
lhs: IDENTIFIER -> variable
    | lhs "[" expression "]" -> index
commande: lhs "=" expression ";" -> assignation
        | TYPE lhs "=" expression ";" -> declaration_assignation
        | "print" "(" expression ")" ";" -> print
        | "if" "(" expression ")" "{" commande "}" -> if
        | "while" "(" expression ")" "{" commande "}" -> while
        | (commande)* commande -> sequence
        | "pass" -> pass
vars: (TYPE IDENTIFIER ",")* TYPE IDENTIFIER -> liste_vars
main: "main" "(" vars ")" "{" commande "return" "(" expression ")" ";" "}"       
%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""", start="main")

op2asm = {"+": "add rax, rbx", "-": "sub rax, rbx"}
var_types = {}

def collect_decl_var_types(vars_ast):
    for i in range(0, len(vars_ast.children), 2):
        vartype = vars_ast.children[i].value
        varname = vars_ast.children[i + 1].value
        var_types[varname] = vartype

def register_string_literal(token_value: str) -> str:
    literal_value = ast.literal_eval(token_value)
    if literal_value not in string_literals:
        string_literals[literal_value] = f"str_{len(string_literals)}"
    return string_literals[literal_value]


def escape_nasm_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')

def _base_name(ast) -> str:
    """Remonte jusqu'au nom de la variable de base d'un lhs ou expression."""
    if ast.data == "variable":
        return ast.children[0].value
    elif ast.data == "index":
        return _base_name(ast.children[0])
    return ""

def _asm_assign_tableau(lhs_name: str, elements: list, decl=False) -> tuple[str, str]:
    """
    Génère le code pour assigner un tableau à lhs_name.
    """
    n = len(elements)
    decls = ""
    if decl:
        vals = ", ".join(str(0) for _ in elements)
        decls += f"\n{lhs_name} : dq {vals}"
        decls += f"\n{lhs_name}_len : dq {n}"

    lines = []
    for i, elem in enumerate(elements):
        asm_elem = asm_expression(elem)
        lines.append(f"{asm_elem}\nmov [{lhs_name} + {i}*8], rax")
    lines.append(f"mov qword [{lhs_name}_len], {n}")
    return "\n".join(lines), decls

def asm_expression(e):
    if e.data == "variable":
        return f"mov rax, [{e.children[0].value}]"
    if e.data == "entier":
        return f"mov rax, {e.children[0].value}"
    if e.data == "char":
        return f"mov rax, {ord(e.children[0].value[1])}"
    if e.data == "string":
        label = register_string_literal(e.children[0].value)
        return f"lea rax, [rel {label}]"
    e_left = e.children[0]
    e_op = e.children[1]
    e_right = e.children[2]
    asm_left = asm_expression(e_left)
    asm_right = asm_expression(e_right)
    if e.data == "tableau":
        # Ne devrait pas être évalué seul en dehors d'une assignation
        return ""
    if e.data == "index":
        base = e.children[0]  
        idx  = e.children[1]  
        base_name = _base_name(base)
        asm_idx = asm_expression(idx)
        return f"""{asm_idx}
mov rcx, rax
mov rax, [{base_name} + rcx*8]"""
    else: # binaire
        e_left = e.children[0]
        e_op   = e.children[1]
        e_right = e.children[2]
        asm_left  = asm_expression(e_left)
        asm_right = asm_expression(e_right)
        return f"""{asm_left}
push rax
{asm_right}
mov rbx, rax
pop rax
{op2asm[e_op.value]}"""

def asm_lhs(ast) -> tuple[str, str]:
    if ast.data == "variable":
        return "", ast.children[0].value
    elif ast.data == "index":
        base = ast.children[0]
        idx  = ast.children[1]
        base_name = _base_name(base)
        asm_idx = asm_expression(idx)
        pre = f"{asm_idx}\nmov rcx, rax\n"
        addr = f"{base_name} + rcx*8"
        return pre, addr
    return "", ""

def asm_commande(c) -> tuple[str, str]:
    global cpt
    decls = ""
    if c.data == "assignation":
        lhs_node = c.children[0]
        exp      = c.children[1]

        if exp.data == "tableau":
            lhs_name = _base_name(lhs_node)
            code, _ = _asm_assign_tableau(lhs_name, exp.children, decl=False)
            return code, decls

        pre, addr = asm_lhs(lhs_node)
        return f"{pre}{asm_expression(exp)}\nmov [{addr}], rax", decls

    elif c.data == "declaration_assignation":
        # collect var types in the body
        vartype = c.children[0].value
        varname = asm_lhs(c.children[1])
        var_types[varname] = vartype
        # collect declarations in the body to store them in data section
        lhs_node = c.children[1]
        exp = c.children[2]

        if exp.data == "tableau":
            lhs_name = _base_name(lhs_node)
            code, new_decls = _asm_assign_tableau(lhs_name, exp.children, decl=True)
            return code, new_decls

        pre, addr = asm_lhs(lhs_node)
        decls += f"\n{addr} : dq 0"
        return f"{pre}{asm_expression(exp)}\nmov [{addr}], rax", decls

    elif c.data == "pass":
        return "nop", decls

    elif c.data == "print":
        expr = c.children[0]
        # print(expr)
        asm_expr = asm_expression(expr)
        _format = "format_str" if var_types[expr.children[0]] == "string" else "format_int"
        return f"""{asm_expr}
mov rdi, {_format}
mov rsi, rax
xor rax, rax
call printf
""", decls

    elif c.data == "while":
        exp  = c.children[0]
        body = c.children[1]
        idx  = cpt
        cpt += 1
        body_cmd, body_decls = asm_commande(body)
        return f"""loop{idx}:
{asm_expression(exp)}
cmp rax, 0
jz end{idx}
{body_cmd}
jmp loop{idx}
end{idx}: nop
""", decls + body_decls

    elif c.data == "sequence":
        d    = c.children[0]
        tail = c.children[1]
        d_cmd,    d_decls    = asm_commande(d)
        tail_cmd, tail_decls = asm_commande(tail)
        return f"{d_cmd}\n{tail_cmd}", decls + d_decls + tail_decls

    else:
        return "", decls

def asm_vars(ast):
    return "\n".join(
        f"""
        mov rbx, [argv]
        add rbx, {(i+1)*8}
        mov rdi, [rbx]
        call atoi
        mov [{ast.children[2*i+1].value}], rax
        """
        for i in range(len(ast.children)//2))

def asm_decls_vars(ast):
    return "\n".join(f"{ast.children[2*i+1].value} : dq 0" 
                     for i in range(len(ast.children)//2))


def pp_expression(ast) -> str :
    if ast.data in ("variable", "entier", "char", "string"):
        return ast.children[0].value
    elif ast.data == "binaire":
        eg = pp_expression(ast.children[0])
        op = ast.children[1].value
        ed = pp_expression(ast.children[2])
        return  f"{eg} {op} {ed}"
    elif ast.data == "tableau":
        return "{" + ", ".join(pp_expression(e) for e in ast.children) + "}"
    elif ast.data == "index":
        return f"{pp_expression(ast.children[0])}[{pp_expression(ast.children[1])}]"
    else :
        return ""
    
def pp_lhs(ast) -> str:
    if ast.data == "variable":
        return ast.children[0].value
    elif ast.data == "index":
        return f"{pp_lhs(ast.children[0])}[{pp_expression(ast.children[1])}]"
    else:
        return ""

def pp_commande(ast) -> str:
    if ast.data == "sequence":
        cg = pp_commande(ast.children[0])
        cd = pp_commande(ast.children[1])
        return f"{cg} \n{cd}"
    elif ast.data == "assignation":
        eg = pp_lhs(ast.children[0])
        ed = pp_expression(ast.children[1])
        return f"{eg} = {ed} ;"
    elif ast.data == "declaration_assignation":
        vartype = ast.children[0].value
        var = pp_lhs(ast.children[1])
        exp = pp_expression(ast.children[2])
        return f"{vartype} {var} = {exp} ;"
    elif ast.data == "print":
        return f"print({pp_expression(ast.children[0])})"
    elif ast.data in ("if", "while"):
        cond = pp_expression(ast.children[0])
        cmd = pp_commande(ast.children[1])
        return f"{ast.data} ({cond}) then \n{cmd}"
    elif ast.data == "pass":
        return "pass"
    else: 
        return ""

def pp_vars(ast) -> str:
    args = f""
    for child in ast.children:
        args += child.value + ","
    args = args[:-1]
    return args

def pp_main(ast) -> str:
    args = pp_vars(ast.children[0])
    cmd = pp_commande(ast.children[1])
    ret = pp_expression(ast.children[2])
    return f"main({args}) {{ \n{cmd} \nreturn {ret} \n}}"


def asm_main(ast):
    collect_decl_var_types(ast.children[0])
    decls = asm_decls_vars(ast.children[0])
    vs = asm_vars(ast.children[0])
    cmd, decls_body = asm_commande(ast.children[1])
    ret = asm_expression(ast.children[2])
    squelette = open("squelette.asm", "r").read()
    string_decls = "\n".join(
        f'{label}: db "{escape_nasm_string(value)}", 0'
        for value, label in string_literals.items()
    )
    all_decls = "\n".join(part for part in (decls, decls_body, string_decls) if part)
    squelette = squelette.replace("DECL_VARS", all_decls)
    squelette = squelette.replace("INIT_VARS", vs)
    squelette = squelette.replace("COMMAND", cmd)
    squelette = squelette.replace("RETURN", ret)
    return squelette


if __name__ == "__main__":
    src = open("source.c", "r").read()
    t = grammaire.parse(src)
    # print(t.pretty())
    with open("resultat.asm", "w") as f:
        f.write(asm_main(t))
        # f.write(pp_main(t))