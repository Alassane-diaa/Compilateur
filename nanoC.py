from typing import Literal

import ast
import lark

cpt = 0
bounds_cpt = 0
string_literals: dict[str, str] = {}

# add .2 to add priority (so that bool or int is not considered as an identifier)
grammaire = lark.Lark("""
IDENTIFIER: /[a-zA-Z_][a-zA-Z_0-9]*/
CHAR: /'([^"\\\\]|\\\\.)'/
STRING: /"([^"\\\\]|\\\\.)*"/
BOOL.2: "true" | "false"
BASE_TYPE.2: "int" | "char" | "string" | "bool"
BRACKET: "[]"
OPBIN: /[+\\-*\\/<>%]/ | "==" | "<" | ">" | "<=" | ">="
type_expr: BASE_TYPE (BRACKET | "[" expression "]")* -> type_expr
decl: type_expr IDENTIFIER -> declaration
expression: IDENTIFIER -> variable 
          | SIGNED_NUMBER -> entier
          | BOOL -> bool
          | CHAR -> char
          | STRING -> string
          | "charAt" "(" expression "," expression ")" -> char_at
          | "len" "(" expression ")" -> len_expr  
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
%import common.WS
%import common.SIGNED_NUMBER
%ignore WS
""", start="main")

op2asm = {"+": "add rax, rbx", "-": "sub rax, rbx", 
          "<": "setl", ">": "setg", "<=": "setle", ">=": "setge", "==": "sete"}
string_id_to_value = {}
var_types = {}
var_declared_size = {}
declared_vars: set[str] = set()


def _type_str(type_node) -> str:
    """Reconstruit la chaîne de type depuis un noeud type_expr, ex: 'int[][]'.
    Les tailles explicites (int[E]) comptent comme une dimension '[]' mais
    leur expression E n'apparaît pas dans la signature de type."""
    base = type_node.children[0].value  # BASE_TYPE token
    brackets = "[]" * (len(type_node.children) - 1)
    return base + brackets


def _type_sizes(type_node) -> list:
    """Retourne la liste des tailles déclarées pour chaque dimension de
    type_expr, dans l'ordre. Chaque élément est soit un noeud d'expression
    (taille E donnée explicitement, ex: int[E]) soit None (ex: int[])."""
    sizes = []
    for child in type_node.children[1:]:
        if hasattr(child, "data"):  # noeud d'expression -> taille explicite
            sizes.append(child)
        else:  # token BRACKET "[]" -> pas de taille
            sizes.append(None)
    return sizes


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
    return "[]" in vartype


def _array_element_type(vartype: str) -> str:
    """Retire un niveau de tableau: 'int[][]' -> 'int[]', 'int[]' -> 'int'."""
    if vartype.endswith("[]"):
        return vartype[:-2]
    return vartype


def _decls_for_var(varname: str, vartype: str) -> str:
    if varname in declared_vars:
        return ""
    declared_vars.add(varname)
    return f"\n{varname} : dq 0"

def collect_decl_var_types(vars_ast):
    for i in range(0, len(vars_ast.children), 2):
        vartype = vars_ast.children[i].value
        varname = vars_ast.children[i + 1].value
        var_types[varname] = vartype



def expr_type(expr) -> str:
    binaire_type = {
        "+": {"int_int": "int", "string_string": "string", "char_char": "char", "int_char": "int", "char_int": "int", "char_string": "string", "string_char": "string"},
        "==": {"bool_bool": "bool", "char_char": "bool", "int_int": "bool", "string_string": "bool_str"},
        "<=": {"bool_bool": "bool", "char_char": "bool", "int_int": "bool", "string_string": "bool_str"},
        ">=": {"bool_bool": "bool", "char_char": "bool", "int_int": "bool", "string_string": "bool_str"},
        "<": {"bool_bool": "bool", "char_char": "bool", "int_int": "bool", "string_string": "bool_str"},
        ">": {"bool_bool": "bool", "char_char": "bool", "int_int": "bool", "string_string": "bool_str"},
        "*": {"int_int": "int"}
        }
    if expr.data == "entier":
        return "int"
    if expr.data == "char":
        return "char"
    if expr.data == "bool":
        return "bool"
    if expr.data == "string":
        return "string"
    if expr.data == "char_at":
        return "char"
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
        left_type = expr_type(e_left)
        right_type = expr_type(e_right)
        key = f"{left_type}_{right_type}"
        if e_op in binaire_type and key in binaire_type[e_op]:
            return binaire_type[e_op][key]
        return "int"
    if expr.data == "index":
        base = expr.children[0]
        base_name = _base_name(base)
        if base_name and _is_argv_base(base_name):
            return "string"
        return _array_element_type(expr_type(base))
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


def _asm_assign_tableau(lhs_name: str, elements: list, vartype: str, decl=False, size_expr=None) -> tuple[str, str]:
    """
    Génère le code pour assigner un tableau à lhs_name.
    Si size_expr est fourni (taille déclarée pour la 1ère dimension, ex: int[E] t = {...}),
    vérifie que len(elements) == E :
      - si size_expr est une constante entière, vérification à la compilation
      - sinon, vérification générée au runtime (sortie avec format_size_mismatch si différent)
    """
    decls = ""
    if decl:
        decls += _decls_for_var(lhs_name, vartype)

    n = len(elements)
    check_code = ""
    if size_expr is not None:
        if size_expr.data == "entier":
            declared_n = int(size_expr.children[0].value)
            if declared_n != n:
                raise ValueError(
                    f"Taille déclarée pour '{lhs_name}' ({declared_n}) "
                    f"ne correspond pas au nombre d'éléments fournis ({n})"
                )
        else:
            check_code = _asm_size_check(n, size_expr)

    code = _asm_build_tableau(elements)
    return f"{check_code}{code}\nmov [{lhs_name}], rax", decls


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


def _asm_index_bounds_guard() -> tuple[str, int]:
    global bounds_cpt
    idx = bounds_cpt
    bounds_cpt += 1
    guard = f"""cmp rcx, 0
jl bounds_error{idx}
cmp rcx, qword [rdx]
jge bounds_error{idx}
"""
    return guard, idx


def _asm_bounds_error_block(guard_id: int, ok_label: str) -> str:
    return f"""jmp {ok_label}
bounds_error{guard_id}:
mov rax, 1
mov rdi, 2
lea rsi, [rel format_bounds]
mov rdx, 38
syscall
mov rdi, 1
call exit
{ok_label}: nop"""


def _asm_size_check(n_literal: int, size_expr) -> str:
    """Vérifie au runtime que size_expr == n_literal (nombre d'éléments du
    littéral assigné). Si différent, affiche une erreur et quitte."""
    global bounds_cpt
    idx = bounds_cpt
    bounds_cpt += 1
    return f"""{asm_expression(size_expr)}
cmp rax, {n_literal}
je size_ok{idx}
mov rax, 1
mov rdi, 2
lea rsi, [rel format_size_mismatch]
mov rdx, 40
syscall
mov rdi, 1
call exit
size_ok{idx}: nop
"""


def asm_expression(e):
    if e.data == "variable":
        return f"mov rax, [{e.children[0].value}]"
    if e.data == "entier":
        return f"mov rax, {e.children[0].value}"
    if e.data == "char":
        return f"mov rax, {ord(e.children[0].value[1])}"
    if e.data == "bool":
        return f"mov rax, {"1" if e.children[0].value=="true" else "0"}"
    if e.data == "string":
        label = register_string_literal(e.children[0].value)
        return f"lea rax, [rel {label}]"
    if e.data == "char_at":
        str_expr = e.children[0]
        idx_expr = e.children[1]
        asm_idx = asm_expression(idx_expr)
        asm_str = asm_expression(str_expr)
        return f"""{asm_idx}
push rax
{asm_str}
mov rdx, rax
pop rcx
movzx eax, byte [rdx + rcx]"""
    
    if e.data == "len_expr":
        arg = e.children[0]
        if arg.data == "variable" and arg.children[0].value == "argv":
            return "mov rax, [argc]"
        arg_type = expr_type(arg)
        if arg_type in ["string", "char"]:
            arg_asm = asm_expression(arg)
            return f"""{arg_asm}
        mov rdi, rax
        call strlen"""
        if _is_array_type(arg_type):
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
        asm_base = asm_expression(base)
        guard, guard_id = _asm_index_bounds_guard()
        ok_label = f"bounds_ok{guard_id}"
        error_block = _asm_bounds_error_block(guard_id, ok_label)
        return f"""{asm_idx}
push rax
{asm_base}
mov rdx, rax
pop rcx
{guard}mov rax, [rdx + 8 + rcx*8]
{error_block}"""
    
    else: # binaire
        e_left = e.children[0]
        e_op   = e.children[1]
        e_right = e.children[2]
        asm_left  = asm_expression(e_left)
        asm_right = asm_expression(e_right)
        binaire_type = expr_type(e)
        if binaire_type == "string":
            const_value = _eval_const_string(e)
            if const_value is None:
                return _asm_concat_strings(asm_left, asm_right)
            label = register_string_literal(repr(const_value))
            return f"lea rax, [rel {label}]"
        elif binaire_type == "bool":
            return f"""
{asm_left}
push rax
{asm_right}
mov rbx, rax
pop rax
cmp rax, rbx
{op2asm[e_op.value]} al
movzx eax, al """
        elif binaire_type == "bool_str":
            return f"""
{asm_left}
push rax
{asm_right}
mov rbx, rax
pop rax
mov rdi, rax
mov rsi, rbx
call strcmp
cmp rax, 0
{op2asm[e_op.value]} al
movzx eax, al """
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
        asm_base = asm_expression(base)
        guard, guard_id = _asm_index_bounds_guard()
        ok_label = f"bounds_ok{guard_id}"
        pre = f"{asm_idx}\npush rax\n{asm_base}\nmov rdx, rax\npop rcx\n{guard}jmp {ok_label}\nbounds_error{guard_id}:\nmov rax, 1\nmov rdi, 2\nlea rsi, [rel format_bounds]\nmov rdx, 38\nsyscall\nmov rdi, 1\ncall exit\n{ok_label}: nop\n"
        addr = f"rdx + 8 + rcx*8"
        return pre, addr
    return "", ""

def asm_commande(c) -> tuple[str, str]:
    global cpt
    decls = ""
    if c.data == "declaration":
        vartype = _type_str(c.children[0])
        varname = c.children[1].value
        var_types[varname] = vartype
        string_id_to_value.pop(varname, None)
        decls += _decls_for_var(varname, vartype)

        sizes = _type_sizes(c.children[0])
        if sizes and sizes[0] is not None:
            var_declared_size[varname] = sizes[0]
            size_expr = sizes[0]
            code = f"""{asm_expression(size_expr)}
push rax
inc rax
imul rax, 8
mov rdi, rax
call malloc
pop rcx
mov qword [rax], rcx
mov [{varname}], rax"""
            return code, decls
        else:
            var_declared_size.pop(varname, None)
        return "nop", decls
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
            vartype = var_types.get(lhs_name, "int[]")
            size_expr = var_declared_size.get(lhs_name)
            code, _ = _asm_assign_tableau(lhs_name, exp.children, vartype, decl=False, size_expr=size_expr)
            return code, decls

        pre, addr = asm_lhs(lhs_node)
        return f"{pre}{asm_expression(exp)}\nmov [{addr}], rax", decls

    elif c.data == "declaration_assignation":
        vartype = _type_str(c.children[0])
        varname = _lhs_name(c.children[1])
        var_types[varname] = vartype
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
            sizes = _type_sizes(c.children[0])
            size_expr = sizes[0] if sizes else None
            if size_expr is not None:
                var_declared_size[lhs_name] = size_expr
            else:
                var_declared_size.pop(lhs_name, None)
            code, new_decls = _asm_assign_tableau(lhs_name, exp.children, vartype, decl=True, size_expr=size_expr)
            return code, new_decls

        pre, addr = asm_lhs(lhs_node)
        decls += _decls_for_var(addr, vartype)
        return f"{pre}{asm_expression(exp)}\nmov [{addr}], rax", decls

    elif c.data == "pass":
        return "nop", decls

    elif c.data == "print":
        expr = c.children[0]
        asm_expr = asm_expression(expr)
        if expr_type(expr) == "string":
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

    elif c.data == "for":
        init = c.children[0]
        cond = c.children[1]
        step = c.children[2]
        body = c.children[3]
        idx  = cpt
        cpt += 1
        init_cmd, init_decls = asm_commande(init)
        body_cmd, body_decls = asm_commande(body)
        step_cmd, step_decls = asm_commande(step)
        return f"""{init_cmd}
loop{idx}:
{asm_expression(cond)}
cmp rax, 0
jz end{idx}
{body_cmd}
{step_cmd}
jmp loop{idx}
end{idx}: nop
""", decls + init_decls + body_decls + step_decls

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
        vartype = _type_str(ast.children[0])
        var = pp_lhs(ast.children[1])
        exp = pp_expression(ast.children[2])
        return f"{vartype} {var} = {exp} ;"
    elif ast.data == "print":
        return f"print({pp_expression(ast.children[0])})"
    elif ast.data in ("if", "while"):
        cond = pp_expression(ast.children[0])
        cmd = pp_commande(ast.children[1])
        return f"{ast.data} ({cond}) then \n{cmd}"
    elif ast.data == "for":
        init = pp_commande(ast.children[0])
        cond = pp_expression(ast.children[1])
        step = pp_commande(ast.children[2])
        body = pp_commande(ast.children[3])
        return f"for ({init} {cond} ; {step}) then \n{body}"
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