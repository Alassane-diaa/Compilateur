import lark

grammaire = lark.Lark("""
IDENTIFIER: /[a-zA-Z_][a-zA-Z_0-9]*/
OPBIN: /[+\-*\/<>]/
CHAR: /'([^"\\\\]|\\\\.)*'/

TYPE: "int" | "float" | "char" | "double"

vars : (TYPE IDENTIFIER ",")* TYPE IDENTIFIER -> liste_vars

decl: TYPE IDENTIFIER ";" -> declaration_vide
| TYPE IDENTIFIER "=" expression ";" -> declaration_renseignee

expression : IDENTIFIER -> variable
           | SIGNED_NUMBER -> entier
           | /[0-9]+\\.[0-9]*/ -> flottant
           | /[0-9]*\\.[0-9]*/ -> flottant
           | "(" TYPE ")" expression -> cast
           | "{" (expression ",")* expression "}" -> tableau
           |  expression OPBIN expression -> binaire
           |  expression "[" expression "]" -> index

lhs: IDENTIFIER -> variable
    | lhs "[" expression "]" -> index

commande : IDENTIFIER "=" expression ";" -> assignation
| TYPE lhs "=" expression ";" -> declaration_assignation
| decl -> declaration
| commande* commande -> sequence
| "pass" -> pass
| "print" "(" expression ")" ";" -> print
| "if" "(" expression ")" "{" commande "}" -> if
| "while" "(" expression ")" "{" commande "}" -> while

main: "main" "(" vars ")" "{" commande "return" "(" expression ")" ";" "}"

%import common.WS
%import common.SIGNED_NUMBER
%import common.FLOAT
%ignore WS
""", start="main")

compteur = iter(range(1000000000))
constantes_flottantes = set()

def pp_expression(ast):
    if ast.data in ("variable", "entier", "flottant"):
        return ast.children[0].value
    elif ast.data == "binaire":
        eg = pp_expression(ast.children[0])
        op = ast.children[1].value
        ed = pp_expression(ast.children[2])
        return f"{eg} {op} {ed}"
    elif ast.data == "tableau":
        return "{" + ", ".join(pp_expression(e) for e in ast.children) + "}"
    elif ast.data == "index":
        return f"{pp_expression(ast.children[0])}[{pp_expression(ast.children[1])}]"
    return ""

def asm_expression(ast):
    global constantes_flottantes
    if ast.data == "variable":
        return f"movsd xmm0, [{ast.children[0].value}]\n"
    if ast.data == "entier":
        # On peut charger un entier et le convertir au besoin, ou stocker directement
        return f"mov rax, {ast.children[0].value}\n"
    if ast.data == "flottant":
        val = ast.children[0].value
        constantes_flottantes.add(val)
        label = "cst_" + val.replace(".", "_")
        return f"movsd xmm0, [{label}]\n"
    if ast.data == "binaire":
        opbin_double = {'+': 'addsd xmm0, xmm1', '-': 'subsd xmm0, xmm1', '*': 'mulsd xmm0, xmm1', '/': 'divsd xmm0, xmm1'}
        eg = asm_expression(ast.children[0])
        op = ast.children[1].value
        ed = asm_expression(ast.children[2])
        
        # Sauvegarde de xmm0 (droite) sur la pile, évaluation de gauche, puis calcul
        return f"""{ed}sub rsp, 8
movsd [rsp], xmm0
{eg}movsd xmm1, [rsp]
add rsp, 8
{opbin_double[op]}
"""
    return ""

def pp_commande(ast):
    tab = "    "
    if ast.data == "assignation":
        lhs = ast.children[0].value
        rhs = pp_expression(ast.children[1])
        return f"{tab}{lhs} = {rhs};\n"
    if ast.data == "pass":
        return f"{tab}pass;\n"
    if ast.data == "print":
        return f"{tab}print({pp_expression(ast.children[0])});\n"
    if ast.data == "sequence":
        cg = pp_commande(ast.children[0])
        cd = pp_commande(ast.children[1])
        return f"{cg}{cd}"
    if ast.data in ("if", "while"):
        cg = pp_expression(ast.children[0])
        cd = pp_commande(ast.children[1])
        return f"{tab}{ast.data}({cg}) {{\n{cd}{tab}}}\n"
    if ast.data == "declaration":
        return pp_declaration(ast.children[0])
    return ""

def pp_declaration(ast):
    tab = "    "
    if ast.data == "declaration_vide":
        type_ = ast.children[0].value
        nom   = ast.children[1].value  
        return f"{tab}{type_} {nom};\n"
    if ast.data == "declaration_renseignee":
        type_ = ast.children[0].value 
        nom   = ast.children[1].value 
        val   = pp_expression(ast.children[2])   
        return f"{tab}{type_} {nom} = {val};\n"
    return ""

def asm_commande(ast):
    if ast.data == "assignation":
        lhs = ast.children[0].value
        rhs = asm_expression(ast.children[1])
        return f"{rhs}movsd [{lhs}], xmm0\n"
    if ast.data == "pass":
        return "nop\n"
    if ast.data == "print":
        # printf pour un float (%f) attend sa valeur dans xmm0 et rax = 1 (1 registre xmm utilisé)
        return f"""{asm_expression(ast.children[0])}mov rdi, format_float
mov rax, 1
call printf
"""
    if ast.data == "sequence":
        cg = asm_commande(ast.children[0])
        cd = asm_commande(ast.children[1])
        return f"{cg}{cd}"
    if ast.data == "while":
        test = asm_expression(ast.children[0])
        cmd = asm_commande(ast.children[1])
        cpt = next(compteur)
        return f"""debut_{cpt}:
{test}xorpd xmm1, xmm1
ucomisd xmm0, xmm1
jp fin_{cpt}
je fin_{cpt}
{cmd}jmp debut_{cpt}
fin_{cpt}: nop
"""
    if ast.data == "if":
        test = asm_expression(ast.children[0])
        cmd = asm_commande(ast.children[1])
        cpt = next(compteur)
        return f"""{test}xorpd xmm1, xmm1
ucomisd xmm0, xmm1
jp fin_{cpt}
je fin_{cpt}
{cmd}fin_{cpt}: nop
"""
    return ""

def asm_vars(ast):
    code = []
    for i in range(len(ast.children) // 2):
        nom_var = ast.children[2 * i + 1].value
        code.append(f"""push rsi
mov rbx, rsi
mov rdi, [rbx + {(i+1)*8}]
call atof
pop rsi
movsd [{nom_var}], xmm0""")
    return "\n".join(code)

def asm_decl_vars(ast):
    return "\n".join(f"{ast.children[2 * i + 1].value}: dq 0.0" for i in range(len(ast.children) // 2))

def pp_vars(ast):
    res = []
    for i in range(len(ast.children) // 2):
        t = ast.children[2*i].value
        v = ast.children[2*i+1].value
        res.append(f"{t} {v}")
    return ", ".join(res)

def pp_main(ast):
    vs = pp_vars(ast.children[0])
    cmd = pp_commande(ast.children[1])
    ret = pp_expression(ast.children[2])
    return f"main({vs}) {{\n{cmd}    return ({ret});\n}}"

def asm_main(ast):
    global constantes_flottantes
    constantes_flottantes.clear()
    
    cmd = asm_commande(ast.children[1])
    ret = asm_expression(ast.children[2])
    decl = asm_decl_vars(ast.children[0])
    vs = asm_vars(ast.children[0])
    
    # Génération dynamique des constantes flottantes pour la section .data
    cst_section = "\n".join(f"cst_{val.replace('.', '_')}: dq {val}" for val in constantes_flottantes)
    
    squelette = f"""global main
extern printf
extern atof

section .data
format_float: db "%f", 10, 0
{decl}
{cst_section}

section .text
main:
push rbp
mov rbp, rsp
{vs}
{cmd}
{ret}
mov rsp, rbp
pop rbp
ret
"""
    return squelette

if __name__ == "__main__":
    src = open("source.c").read()
    t = grammaire.parse(src)
    print(pp_main(t))
    with open("resultat.asm", "w") as f:
        f.write(asm_main(t))