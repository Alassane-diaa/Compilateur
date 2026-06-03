from typing import Literal

import ast
import lark

cpt = 0
string_literals: dict[str, str] = {}

grammaire = lark.Lark("""
IDENTIFIER: /[a-zA-Z_][a-zA-Z_0-9]*/
CHAR: /'([^"\\\\]|\\\\.)'/
STRING: /"([^"\\\\]|\\\\.)*"/
TYPE: "int" | "char" | "string" | "int[]" | "char[]" | "string[]"
OPBIN: /[+\\-*\\/<>%]/
decl: TYPE IDENTIFIER -> declaration
expression: IDENTIFIER -> variable 
          | SIGNED_NUMBER -> entier
          | CHAR -> char
          | STRING -> string
          | "len" "(" expression ")" -> len_expr  
          | expression OPBIN expression -> binaire
          | "{" (expression ",")* expression "}" -> tableau
          | expression "[" expression "]" -> index
lhs: IDENTIFIER -> variable
    | lhs "[" expression "]" -> index
commande: lhs "=" expression ";" -> assignation
        | TYPE IDENTIFIER ";"-> declaration
        | TYPE lhs "=" expression ";" -> declaration_assignation
        | "print" "(" expression ")" ";" -> print
        | "if" "(" expression ")" "{" commande "}" -> if
        | "while" "(" expression ")" "{" commande "}" -> while
        | (commande)* commande -> sequence
        | "pass" -> pass
main: "main" "(" "int" "argc" "," "char*" "argv" ")" "{" commande "return" "(" expression ")" ";" "}"       
%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""", start="main")

op2asm = {"+": "add rax, rbx", "-": "sub rax, rbx"}
string_id_to_value = {}
var_types = {}


def _eval_const_string(expr):
    if expr.data == "string":
        return ast.literal_eval(expr.children[0].value)
    if expr.data == "char":
        return ast.literal_eval(expr.children[0].value)
    if expr.data == "variable":
        return string_id_to_value.get(expr.children[0].value)
    if expr.data == "binaire":
        op = expr.children[1].value
        if op != "+":
            return None
        left = _eval_const_string(expr.children[0])
        right = _eval_const_string(expr.children[2])
        if left is None or right is None:
            return None
        return left + right
    return None

def _is_array_type(vartype: str) -> bool:
    return vartype in ("int[]", "char[]", "string[]")


def _decls_for_var(varname: str, vartype: str) -> str:
    return f"\n{varname} : dq 0"

def collect_decl_var_types(vars_ast):
    for i in range(0, len(vars_ast.children), 2):
        vartype = vars_ast.children[i].value
        varname = vars_ast.children[i + 1].value
        var_types[varname] = vartype



def expr_type2(expr) -> str:
    binaire_type = {
        "+": {"int_int": "int", "string_string": "string", "char_char": "char", "int_char": "int", "char_int": "int", "char_string": "string", "string_char": "string"},
        "*": {"int_int": "int"}
        }
    if expr.data == "entier":
        return "int"
    if expr.data == "char":
        return "char"
    if expr.data == "string":
        return "string"
    if expr.data == "variable":
        name = expr.children[0].value
        if name not in var_types:
            raise NameError(f"undeclared variable: {name}")
        return var_types[name]
    if expr.data == "len_expr":
        return "int"
    if expr.data == "binaire":
        e_left = expr.children[0]
        e_op   = expr.children[1].value
        e_right = expr.children[2]
        left_type = expr_type2(e_left)
        right_type = expr_type2(e_right)
        key = f"{left_type}_{right_type}"
        if e_op in binaire_type and key in binaire_type[e_op]:
            return binaire_type[e_op][key]
        return "int"
    if expr.data == "index":
        base_name = _base_name(expr.children[0])
        if base_name and _is_argv_base(base_name):
            return "string"
        if base_name and base_name in var_types:
            base_type = var_types[base_name]
            if base_type.endswith("[]"):
                return base_type[:-2]
            return base_type
        raise NameError(f"undeclared variable: {base_name}")
    return "int"

def expr_type(expr) -> str:
    if expr.data == "entier":
        return "int"
    if expr.data == "char":
        return "char"
    if expr.data == "string":
        return "string"
    if expr.data == "variable":
        name = expr.children[0].value
        if name not in var_types:
            raise NameError(f"undeclared variable: {name}")
        return var_types[name]
    if expr.data == "len_expr":
        return "int"
    if expr.data == "binaire":
        return expr_type2(expr)
    if expr.data == "index":
        base_name = _base_name(expr.children[0])
        if base_name and _is_argv_base(base_name):
            return "string"
        if base_name and base_name in var_types:
            base_type = var_types[base_name]
            if base_type.endswith("[]"):
                return base_type[:-2]
            return base_type
        raise NameError(f"undeclared variable: {base_name}")
    return "int"

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


def _lhs_name(ast) -> str:
    if ast.data == "variable":
        return ast.children[0].value
    if ast.data == "index":
        return _base_name(ast)
    return ""


def _is_argv_base(base_name: str) -> bool:
    return base_name == "argv"

def _asm_build_tableau(elements: list) -> str:
    """Construit un tableau heap avec un en-tête de longueur.

    Le registre rax contient le pointeur du bloc alloué à la fin.
    """
    n = len(elements)
    size = (n + 1) * 8
    lines = [
        f"mov rdi, {size}",
        "call malloc",
        "mov rbx, rax",
        f"mov qword [rbx], {n}",
    ]
    for i, elem in enumerate(elements):
        lines.append("push rbx")
        lines.append(asm_expression(elem))
        lines.append("pop rbx")
        lines.append(f"mov [rbx + {(i + 1) * 8}], rax")
    lines.append("mov rax, rbx")
    return "\n".join(lines)


def _asm_assign_tableau(lhs_name: str, elements: list, decl=False) -> tuple[str, str]:
    """
    Génère le code pour assigner un tableau à lhs_name.
    """
    decls = ""
    if decl:
        decls += _decls_for_var(lhs_name, "int[]")
    code = _asm_build_tableau(elements)
    return f"{code}\nmov [{lhs_name}], rax", decls


def _asm_concat_strings(asm_left: str, asm_right: str) -> str:
    return f"""{asm_left}
push rax
{asm_right}
push rax
mov rdi, [rsp+8]
call strlen
mov rcx, rax
mov rdi, [rsp]
call strlen
add rax, rcx
add rax, 1
mov rdi, rax
call malloc
mov rdi, rax
mov rsi, [rsp+8]
call strcpy
mov rdi, rax
mov rsi, [rsp]
call strcat
add rsp, 16"""

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
    if e.data == "len_expr":
        arg = e.children[0]
        arg_type = expr_type(arg)
        if arg_type in ["string", "char"]:
            arg_asm = asm_expression(arg)
            return f"""{arg_asm}
        mov rdi, rax
        call strlen"""
        if arg_type in ["int[]", "char[]", "string[]"]:
            arg_asm = asm_expression(arg)
            return f"""{arg_asm}
mov rax, [rax]"""
        else:
            raise NotImplementedError("len only avaible for strings, chars and arrays")
    if e.data == "tableau":
        return _asm_build_tableau(e.children)
    if e.data == "index":
        base = e.children[0]  
        idx  = e.children[1]  
        asm_idx = asm_expression(idx)
        base_name = _base_name(base)
        if base_name and _is_argv_base(base_name):
            return f"""{asm_idx}
push rax
{asm_expression(base)}
mov rdx, rax
pop rcx
mov rax, [rdx + rcx*8]"""
        return f"""{asm_idx}
push rax
{asm_expression(base)}
mov rdx, rax
pop rcx
mov rax, [rdx + 8 + rcx*8]"""
    else: # binaire
        e_left = e.children[0]
        e_op   = e.children[1]
        e_right = e.children[2]
        asm_left  = asm_expression(e_left)
        asm_right = asm_expression(e_right)
        binaire_type = expr_type2(e)
        print(binaire_type)
        if binaire_type == "string":
            const_value = _eval_const_string(e)
            if const_value is None:
                return _asm_concat_strings(asm_left, asm_right)
            label = register_string_literal(repr(const_value))
            return f"lea rax, [rel {label}]"
        elif binaire_type == "int":
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
        asm_idx = asm_expression(idx)
        base_name = _base_name(base)
        if base_name and _is_argv_base(base_name):
            pre = f"{asm_idx}\npush rax\n{asm_expression(base)}\nmov rdx, rax\npop rcx\n"
            addr = "rdx + rcx*8"
            return pre, addr
        pre = f"{asm_idx}\npush rax\n{asm_expression(base)}\nmov rdx, rax\npop rcx\n"
        addr = f"rdx + 8 + rcx*8"
        return pre, addr
    return "", ""

def asm_commande(c) -> tuple[str, str]:
    global cpt
    decls = ""
    if c.data == "declaration":
        vartype = c.children[0].value
        varname = c.children[1].value
        var_types[varname] = vartype
        string_id_to_value.pop(varname, None)
        decls += _decls_for_var(varname, vartype)
    if c.data == "assignation":
        lhs_node = c.children[0]
        exp      = c.children[1]

        lhs_name = _lhs_name(lhs_node)
        if lhs_name:
            if var_types.get(lhs_name) != "string":
                string_id_to_value.pop(lhs_name, None)
            else:
                const_value = _eval_const_string(exp)
                if const_value is None:
                    string_id_to_value.pop(lhs_name, None)
                else:
                    string_id_to_value[lhs_name] = const_value

        if exp.data == "tableau":
            lhs_name = _base_name(lhs_node)
            code, _ = _asm_assign_tableau(lhs_name, exp.children, decl=False)
            return code, decls

        pre, addr = asm_lhs(lhs_node)
        return f"{pre}{asm_expression(exp)}\nmov [{addr}], rax", decls

    elif c.data == "declaration_assignation":
        # collect var types in the body
        vartype = c.children[0].value
        varname = _lhs_name(c.children[1])
        var_types[varname] = vartype
        # collect declarations in the body to store them in data section
        lhs_node = c.children[1]
        exp = c.children[2]

        if varname:
            if vartype != "string":
                string_id_to_value.pop(varname, None)
            else:
                const_value = _eval_const_string(exp)
                if const_value is None:
                    string_id_to_value.pop(varname, None)
                else:
                    string_id_to_value[varname] = const_value

        if exp.data == "tableau":
            lhs_name = _base_name(lhs_node)
            code, new_decls = _asm_assign_tableau(lhs_name, exp.children, decl=True)
            return code, new_decls

        pre, addr = asm_lhs(lhs_node)
        decls += _decls_for_var(addr, vartype)
        return f"{pre}{asm_expression(exp)}\nmov [{addr}], rax", decls

    elif c.data == "pass":
        return "nop", decls

    elif c.data == "print":
        expr = c.children[0]
        asm_expr = asm_expression(expr)
        if expr_type2(expr) == "string":
            _format = "format_str"
        elif expr_type(expr) == "char":
            _format = "format_char"
        else:
            _format = "format_int"
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

def asm_init_main() -> str:
    return """mov [argc], rdi
mov [argv], rsi"""


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
    cmd = pp_commande(ast.children[0])
    ret = pp_expression(ast.children[1])
    return f"main(int argc, char* argv) {{ \n{cmd} \nreturn {ret} \n}}"


def asm_main(ast):
    var_types["argc"] = "int"
    var_types["argv"] = "string*"
    decls = "\n".join((_decls_for_var("argc", "int"), _decls_for_var("argv", "string*")))
    vs = asm_init_main()
    cmd, decls_body = asm_commande(ast.children[0])
    ret = asm_expression(ast.children[1])
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