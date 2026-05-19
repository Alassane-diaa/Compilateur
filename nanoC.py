from typing import Literal

import lark

cpt = 0

grammaire = lark.Lark("""
IDENTIFIER: /[a-zA-Z_][a-zA-Z_0-9]*/
CHAR: /'([^"\\\\]|\\\\.)*'/
TYPE: "int" | "char"
OPBIN: /[+\\-*\\/<>%]/
decl: TYPE IDENTIFIER -> declaration
    | TYPE IDENTIFIER "=" expression ";" -> declaration_assignation
expression: IDENTIFIER -> variable 
          | SIGNED_NUMBER -> entier
          | CHAR -> char
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

def asm_expression(e):
    if e.data == "variable":
        return f"mov rax, [{e.children[0].value}]"
    if e.data == "entier":
        return f"mov rax, {e.children[0].value}"
    if e.data == "char":
        return f"mov rax, {ord(e.children[0].value[1])}"
    e_left = e.children[0]
    e_op = e.children[1]
    e_right = e.children[2]
    asm_left = asm_expression(e_left)
    asm_right = asm_expression(e_right)
    return f"""{asm_left}
push rax
{asm_right}
mov rbx, rax
pop rax
{op2asm[e_op.value]}"""


def asm_commande(c) -> tuple[str, Literal['']]:
    global cpt
    decls = ""
    if c.data == "assignation":
        var = c.children[0]
        exp = c.children[1]
        return f"{asm_expression(exp)}\nmov [{var.value}], rax", decls
    elif c.data == "declaration_assignation":
        var = c.children[1]
        exp = c.children[2]
        decls += f"\n{var.value} : dq 0"
        return f"{asm_expression(exp)}\nmov [{var.value}], rax", decls
    elif c.data == "pass":
        return "nop", decls
    elif c.data == "print":
        return f"""{asm_expression(c.children[0])}
mov rdi, format
mov rsi, rax
xor rax, rax
call printf
""", decls
    elif c.data == "while":
        exp = c.children[0]
        body = c.children[1]
        idx = cpt
        cpt += 1
        body_cmd, body_decls = asm_commande(body)
        return f"""loop{idx}:{asm_expression(exp)}
cmp rax, 0
jz end{idx}
{body_cmd}
jmp loop{idx}
end{idx}: nop
""", decls + body_decls
    elif c.data == "sequence":
        d = c.children[0]
        tail = c.children[1]
        d_cmd, d_decls = asm_commande(d)
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
    if ast.data in ("variable", "entier", "char"):
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
    decls = asm_decls_vars(ast.children[0])
    vs = asm_vars(ast.children[0])
    cmd, decls_body = asm_commande(ast.children[1])
    ret = asm_expression(ast.children[2])
    squelette = open("squelette.asm", "r").read()
    squelette = squelette.replace("DECL_VARS", decls + decls_body)
    squelette = squelette.replace("INIT_VARS", vs)
    squelette = squelette.replace("COMMAND", cmd)
    squelette = squelette.replace("RETURN", ret)
    return squelette


if __name__ == "__main__":
    src = open("source.c", "r").read()
    t = grammaire.parse(src)
    with open("resultat.asm", "w") as f:
        # f.write(asm_main(t))
        f.write(pp_main(t))