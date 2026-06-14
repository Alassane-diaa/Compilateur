# nanoC — Compilateur vers x86_64

nanoC est un compilateur de source vers assembleur NASM x86_64, écrit en Python avec [Lark](https://github.com/lark-parser/lark) comme moteur de parsing. Il prend en entrée un sous-ensemble de C fortement typé et produit un fichier `.asm` prêt à être assemblé et lié.

---

## Utilisation

```bash
./nanoc.sh source.c
./source.out "argument"
```

Le script `nanoc.sh` enchaîne l'invocation de `nanoC.py`, l'assemblage via NASM et l'édition de liens. La structure du binaire est calquée sur l'ABI System V AMD64 : `main` reçoit `argc` dans `rdi` et `argv` dans `rsi` au démarrage.

---

## Structure d'un programme

Tout programme nanoC consiste en une unique fonction `main` avec la signature fixe suivante :

```c
main(int argc, char* argv) {
    // commandes
    return (expression);
}
```

- `argc` est de type `int` et vaut le nombre d'arguments passés à l'exécutable.
- `argv` est de type `string*` (tableau de chaînes brut, layout C). `argv[i]` lit directement le pointeur C sans en-tête de longueur. `len(argv)` renvoie `argc`.
- Le `return` est obligatoire et accepte n'importe quelle expression.
- Les commentaires sont introduits par `//` et ignorés jusqu'à la fin de la ligne.

---

## Système de types

nanoC est **statiquement typé**. Toute variable doit être déclarée avant d'être utilisée, faute de quoi le compilateur lève une `NameError` à la compilation. Les types scalaires disponibles sont :

| Type     | Taille en mémoire | Notes                                      |
|----------|-------------------|--------------------------------------------|
| `int`    | 8 octets (qword)  | Entier signé, registre `rax`               |
| `float`  | 8 octets (qword)  | IEEE 754 double précision, transit via SSE2|
| `char`   | 8 octets (qword)  | Valeur ASCII stockée comme entier          |
| `bool`   | 8 octets (qword)  | `true` → 1, `false` → 0                   |
| `string` | 8 octets (qword)  | Pointeur vers une chaîne null-terminée     |

Toutes les variables scalaires sont stockées en mémoire statique (section `.bss` / `.data`), déclarées comme `dq 0`. Les tableaux sont stockés sous forme de pointeur (8 octets) vers un bloc alloué dynamiquement sur le tas.

---

## Déclarations et assignations

```c
// Déclaration seule
int x;
float f;
bool flag;
string s;
char c;

// Déclaration avec initialisation
int x = 42;
float pi = 3.14159;
char c = 'A';
string s = "bonjour";
bool ok = true;

// Assignation simple (variable déjà déclarée)
x = x + 1;
```

Une `declaration` simple (`int x;`) initialise implicitement la variable à `0` (via `dq 0`) ; aucune instruction n'est générée pour une scalaire (`nop`), sauf dans le cas d'un tableau à taille fixe (voir [Tableaux](#tableaux)).

---

## Expressions et opérateurs

### Littéraux

```c
42          // int
-7          // int signé
3.14        // float
1.5e-10     // float, notation scientifique
2E+5        // float, notation scientifique
'A'         // char
"hello"     // string
true        // bool
false       // bool
```

Les littéraux flottants sont reconnus par une regex dédiée (`FLOAT`) qui couvre la notation décimale classique et la notation scientifique avec ou sans exposant signé (`1.5e-10`, `2E+5`, `3e10`).

### Parenthésage

```c
(1 + 2) * 3      // les parenthèses regroupent une sous-expression
```

Une expression entre parenthèses (`paren`) est transparente : elle conserve le type et la valeur de la sous-expression qu'elle contient, et ne génère aucun code supplémentaire.

### Opérateurs binaires

Les opérateurs disponibles sont `+`, `-`, `*`, `/`, `%`, `==`, `<`, `>`, `<=`, `>=`.

Le compilateur détermine le type du résultat selon les types des opérandes :

| Opérandes          | `+` `-` `*` `/`       | `==` `<` `>` `<=` `>=` |
|--------------------|-----------------------|------------------------|
| `int` × `int`      | `int`                 | `bool`                 |
| `float` × `float`  | `float`               | `bool`                 |
| `float` × `int`    | `float` (conv. auto)  | `bool` (conv. auto)    |
| `int` × `float`    | `float` (conv. auto)  | `bool` (conv. auto)    |
| `string` × `string`| `string` (concat `+`) | `bool` (strcmp)        |
| `char` × `char`    | `char`/`int`*         | `bool`                 |
| `int` × `char`     | `int`                 | —                      |
| `char` × `int`     | `int`                 | —                      |
| `char` × `string`  | `string` (concat)     | —                      |
| `string` × `char`  | `string` (concat)     | —                      |

*Note : `char + char` est typé `char` dans la table de typage, mais le résultat est généré comme une opération entière standard (`add rax, rbx`).

L'opérateur `%` est interdit si l'un des opérandes est un `float` (erreur de compilation `TypeError`).

Pour toute combinaison `int`/`char`/`bool` non listée explicitement dans la table de typage pour un opérateur donné, le compilateur retombe par défaut sur le type `int`.

### Génération assembleur des opérateurs

Les opérations entières passent par `rax` / `rbx` :

| Opérateur | Instruction NASM              |
|-----------|--------------------------------|
| `+`       | `add rax, rbx`                 |
| `-`       | `sub rax, rbx`                 |
| `*`       | `imul rax, rbx`                |
| `/`       | `cqo` puis `idiv rbx`          |
| `%`       | `cqo` puis `idiv rbx`*         |
| `<`       | `cmp rax, rbx` / `setl al` / `movzx rax, al` |
| `>`       | `cmp rax, rbx` / `setg al` / `movzx rax, al` |
| `<=`      | `cmp rax, rbx` / `setle al` / `movzx rax, al` |
| `>=`      | `cmp rax, rbx` / `setge al` / `movzx rax, al` |
| `==`      | `cmp rax, rbx` / `sete al` / `movzx rax, al`  |

*`idiv` produit le quotient dans `rax` et le reste dans `rdx` ; nanoC utilise `rax` (le quotient) comme résultat pour `/` comme pour `%` via la table `op2asm`.

Les opérations flottantes transitent par `xmm0` / `xmm1` :

| Opérateur | Instruction NASM  |
|-----------|-------------------|
| `+`       | `addsd xmm0, xmm1`|
| `-`       | `subsd xmm0, xmm1`|
| `*`       | `mulsd xmm0, xmm1`|
| `/`       | `divsd xmm0, xmm1`|

Les comparaisons flottantes (`float == float`, `float < float`, etc.) utilisent `ucomisd` suivi de `setb`, `seta`, `setbe`, `setae`, ou `sete` (table `float_cmp2asm`), puis `movzx rax, al`.

### Conversion implicite int ↔ float dans les expressions binaires

Quand une opération arithmétique (`+ - * /`) combine un `int` (ou un `char`) avec un `float`, l'opérande entier est automatiquement converti via `cvtsi2sd xmm0, rax` avant l'opération flottante. Le résultat est de type `float`.

---

## Casts explicites

```c
(int) expression    // float → int, tronque via cvttsd2si
(float) expression  // int → float, via cvtsi2sd
```

- `(float) <int_expr>` : convertit l'entier en `rax` vers un double via `cvtsi2sd xmm0, rax` puis `movq rax, xmm0`. Le résultat est typé `float`.
- `(int) <float_expr>` : convertit le double via `movq xmm0, rax` puis `cvttsd2si rax, xmm0` (troncature vers zéro). Le résultat est typé `int`.
- Si le type cible correspond déjà au type source (ou pour toute autre combinaison non gérée), le cast est transparent : il ne génère que le code de l'expression interne, sans conversion, et renvoie le type cible déclaré.

### Conversions implicites lors des assignations et déclarations

En plus des casts explicites, le compilateur tolère silencieusement deux cas de figure sans lever d'erreur de type :

- **Déclaration / assignation `int` avec une valeur `float`** : la valeur flottante calculée dans `rax` (via `movq`/SSE2) est tronquée en entier via `movq xmm0, rax` puis `cvttsd2si rax, xmm0` avant d'être stockée.
- **Tableau `int[]` initialisé avec des éléments `float`, ou inversement (`float[]` avec éléments `int`)** : autorisé par `_check_array_elements_type` sans conversion explicite des valeurs au niveau des éléments (les bits stockés restent ceux produits par `asm_expression` de chaque élément).

Toute autre incohérence de type entre la valeur déclarée/attendue et l'expression assignée lève une `TypeError` à la compilation.

---

## Flottants : détails d'implémentation

Les littéraux flottants sont représentés en IEEE 754 double précision (64 bits). À la compilation, la valeur est immédiatement convertie en sa représentation hexadécimale 64 bits et chargée via `mov rax, 0x...`. Les registres `xmm0` et `xmm1` ne servent que pour les opérations arithmétiques, les comparaisons et les conversions — les flottants transitent par la pile et par `rax` comme les autres types entre deux opérations.

```
float x = 3.14;
// → mov rax, 0x40091eb851eb851f   (représentation IEEE 754 de 3.14)
// → mov [x], rax
```

### Affichage des flottants

`print(<expr_float>)` génère une séquence dédiée :

```nasm
; ... calcul de la valeur dans rax (bits IEEE 754) ...
movq xmm0, rax
mov rdi, format_float
mov rax, 1          ; indique à printf un argument flottant variadique (convention SysV)
call printf
```

Le format `format_float` (`"%f\n"`) est ajouté automatiquement à la section `.data` du fichier généré, en plus des chaînes littérales déduplicées du programme.

---

## Tableaux

### Layout mémoire

Chaque tableau (hors `argv`) est alloué sur le tas via `malloc` (littéral de tableau `{...}`) ou `calloc` (déclaration à taille fixe sans littéral). Le bloc a la structure suivante :

```
+---------------------+---------------------+---------------------+--
| Taille (n)          | Élément 0           | Élément 1           | ...
| 8 octets            | 8 octets            | 8 octets            |
+---------------------+---------------------+---------------------+--
^
Pointeur stocké dans la variable
```

La taille est encodée dans les 8 premiers octets (en-tête), ce qui rend `len()` possible à l'exécution sans métadonnée externe.

Les tableaux `argv` font exception : ils utilisent le layout C brut (pas d'en-tête de longueur, pas de garde de bornes, pas de null-check).

### Déclarations

```c
// Taille fixe, initialisé à zéro (calloc(n+1, 8), header rempli avec n)
int[5] t;

// Avec littéral (taille déduite)
int[] t = {1, 2, 3};

// Taille fixe + littéral (doit correspondre, vérifié à la compilation si la taille est un littéral entier)
int[3] t = {10, 20, 30};

// Taille donnée par une expression (vérification générée au runtime)
int n = 3;
int[n] t = {10, 20, 30};   // génère un check d'égalité n == 3 au runtime, sort avec une erreur sinon

// Tableaux de flottants
float[] f = {1.0, 2.5, 3.14};

// Tableaux multidimensionnels (chaque sous-tableau est lui-même alloué sur le tas)
int[3][] mat = {{1, 2}, {3, 4}, {5, 6}};
int[2][] mat2 = {{10, 20, 30}, {40, 50}};   // sous-tableaux de tailles différentes autorisés
```

Pour une déclaration `type[n] varname;` sans littéral (taille fixe explicite, pas d'initialisation), le code généré est :

```nasm
; évalue n dans rax
push rax
inc rax              ; n + 1 (place pour l'en-tête)
mov rdi, rax
mov rsi, 8
call calloc          ; calloc(n+1, 8) -> zone mise à zéro
pop rcx
mov qword [rax], rcx ; en-tête = n
mov [varname], rax
```

Pour une déclaration `type[] varname;` (sans taille, sans littéral), aucune allocation n'est générée (`nop`) : la variable reste un pointeur nul jusqu'à une éventuelle assignation, ce qui déclenchera le null-check à l'accès.

### Accès et manipulation

```c
t[2]           // lecture de l'élément d'indice 2
t[0] = 99;     // écriture
mat[1][0]      // accès chaîné (tableau de tableaux)
len(t)         // longueur → int, lit l'en-tête à [pointeur]
```

L'accès par index (`t[i]`) sur un tableau nanoC (hors `argv`) génère, dans l'ordre :

1. Évaluation de l'index → `rax`, sauvegardé sur la pile (`push`/`pop`).
2. Évaluation du tableau de base → `rax` (pointeur vers l'en-tête).
3. **Null-check** : si le pointeur est `0`, affiche `format_null_array` sur `stderr` (fd 2) et appelle `exit(1)`.
4. **Garde de bornes** : compare l'index (`rcx`) à `0` et à la valeur de l'en-tête (`[rdx]`) ; si hors bornes, affiche `format_bounds` sur `stderr` et appelle `exit(1)`.
5. Lecture finale : `mov rax, [rdx + 8 + rcx*8]` (le `+8` correspond au décalage de l'en-tête de longueur).

L'écriture (`t[i] = expr;`) suit la même séquence de pré-calcul (null-check + garde de bornes) pour obtenir l'adresse cible `rdx + 8 + rcx*8`, puis y stocke la valeur de `expr`.

### Cas particulier : `argv`

`argv[i]` (et l'écriture `argv[i] = ...`) n'a **ni en-tête de longueur, ni null-check, ni garde de bornes** : l'accès est direct, `mov rax, [rdx + rcx*8]` (sans le `+8`), conformément au layout C natif d'`argv`. `len(argv)` retourne directement `[argc]` sans déréférencer `argv`.

### `len(expression)`

Renvoie la longueur d'un tableau sous forme d'`int` :

- Pour `argv` : retourne `[argc]` directement.
- Pour une `string` ou un `char` : appelle `strlen` (`mov rdi, rax` puis `call strlen`).
- Pour tout type tableau (`[]`) : effectue un **null-check** sur le pointeur, puis lit l'en-tête (`mov rax, [rax]`).
- Pour tout autre type : lève une `NotImplementedError` à la compilation (« len only available for strings, chars and arrays »).

### Restrictions sur les tableaux

- **Hétérogénéité interdite** (sauf int/float) : tous les éléments d'un littéral doivent avoir le même type de base, à l'exception du mélange `int`/`float` qui est toléré dans les deux sens. Un cast explicite est nécessaire pour les autres types :
  ```c
  float[] t = {1.5, 2};           // OK (int toléré dans un float[])
  int[] t = {1, 2.5};             // OK (float toléré dans un int[])
  int[] t = {1, 'a', 3};          // ERREUR (char dans un int[])
  string[] t = {"a", 'b'};        // ERREUR (char dans un string[])
  ```

- **Vérification récursive pour les tableaux imbriqués** : chaque sous-littéral `{...}` d'un tableau de tableaux est vérifié récursivement contre le type d'élément attendu de niveau inférieur (`_array_element_type` appliqué de façon répétée).

- **Incohérence de taille** :
  - Si la taille déclarée est un littéral entier (`int[3] t = {...}`), elle doit correspondre exactement au nombre d'éléments du littéral, sinon `ValueError` **à la compilation** :
    ```c
    int[3] t = {1, 2};              // ERREUR (3 ≠ 2), détectée à la compilation
    ```
  - Si la taille déclarée est une expression non constante (`int[n] t = {...}`), un test d'égalité est généré et exécuté **au runtime** : si `n != nombre_d_elements`, le programme affiche `format_size_mismatch` sur `stderr` et appelle `exit(1)`.

- **Type d'assignation** : l'écriture dans une case fait l'objet d'une vérification de type (avec tolérance `int`/`float` comme ci-dessus) :
  ```c
  int[5] t;
  t[0] = "texte";                 // ERREUR (string dans un int[])
  ```

- **Accès hors-bornes et tableau non initialisé** : détectés et gérés à l'exécution (voir [Accès et manipulation](#accès-et-manipulation)), pas seulement à la compilation.

- **Absence de libération automatique** : le compilateur ne génère pas d'instructions `free`. Toute réassignation d'une variable tableau crée une fuite mémoire.

---

## Structures de contrôle

```c
// Conditionnelle (sans else)
if (condition) {
    commande
}

// Boucle while
while (condition) {
    commande
}

// Boucle for
for (int i = 0; i < 10; i = i + 1) {
    commande
}

// Instruction vide
pass
```

Les accolades sont obligatoires. Le corps d'une structure de contrôle peut contenir une séquence de commandes (plusieurs instructions enchaînées). Les conditions sont évaluées comme des entiers : `0` est faux, toute autre valeur est vraie (`cmp rax, 0` / `jz`).

La clause d'initialisation et le pas (`for_step`) d'une boucle `for` n'acceptent qu'une `assignation` (`lhs = expression`), pas une `declaration_assignation` : la variable de boucle doit donc être déclarée avant la boucle.

> **Note d'implémentation** : la branche `if` est reconnue par le parseur (`"if" "(" expression ")" "{" commande "}" -> if`) mais n'est **pas traitée** par `asm_commande` (qui ne gère que `declaration`, `assignation`, `declaration_assignation`, `pass`, `print`, `while`, `for`, `sequence`) : un `if` isolé produit une chaîne vide (aucun code généré), ce qui peut casser la séquence environnante. Évitez `if` pour le moment, ou utilisez `while` avec une condition garantissant une seule itération comme contournement.

---

## Fonctions built-in

### `print(expression)`

Affiche une valeur sur la sortie standard via `printf`. Le format est sélectionné automatiquement selon le type de l'expression :

| Type     | Format utilisé   | Mécanisme                                  |
|----------|------------------|----------------------------------------------|
| `int`    | `%lld\n`         | `rsi` ← valeur, `xor rax, rax`               |
| `float`  | `%f\n`           | `xmm0` ← valeur, `rax` ← 1 (arg variadique SSE)|
| `char`   | `%c\n`           | `rsi` ← valeur, `xor rax, rax`               |
| `string` | `%s\n`           | `rsi` ← pointeur, `xor rax, rax`             |
| `bool`   | `%lld\n`         | (traité comme `int`)                         |
| `bool_str` (résultat de `string == string`, etc.) | `%lld\n` | normalisé en `bool` avant sélection du format |

Tous les formats (`format_int`, `format_str`, `format_char`) incluent un retour à la ligne final (`\n`) dans `squelette.asm`.

### `len(expression)`

Voir la section [Tableaux](#lenexpression).

### `charAt(s, i)`

Renvoie le `char` à la position `i` dans la chaîne `s`. Génère :

```nasm
; évalue i -> rax, push
; évalue s -> rax
mov rdx, rax     ; pointeur chaîne
pop rcx          ; index
movzx eax, byte [rdx + rcx]
```

### Concaténation de chaînes

L'opérateur `+` sur deux opérandes dont le résultat est de type `string` (`string+string`, `string+char`, `char+string`) génère une concaténation à l'exécution via `strlen`, `malloc`, `strcpy` et `strcat`. Fonctionne avec des valeurs dynamiques (pas seulement des littéraux).

**Optimisation de constantes** : si les deux opérandes de la concaténation sont des expressions constantes évaluables à la compilation (chaînes littérales, `char` littéraux, variables connues comme constantes via une chaîne de `+` constante, récursivement), le compilateur calcule directement la chaîne résultante, l'enregistre comme un nouveau littéral dédupliqué, et génère simplement `lea rax, [rel str_N]` — sans aucun appel `strcpy`/`strcat`/`malloc` au runtime.

---

## Gestion des erreurs à l'exécution

nanoC génère des vérifications défensives systématiques pour les opérations sur tableaux, qui terminent le programme avec un message d'erreur sur `stderr` (file descriptor 2, via `syscall write` direct) et un code de sortie `1` (`exit`) :

| Situation                                                   | Message                                              |
|--------------------------------------------------------------|-------------------------------------------------------|
| Index `< 0` ou `>= len(tableau)` lors d'un accès `t[i]`       | `IndexError: array index out of bounds`               |
| Tableau non initialisé (pointeur nul) utilisé dans `t[i]` ou `len(t)` | `RuntimeError: array used before initialization` |
| Taille déclarée (expression non constante) ≠ nombre d'éléments du littéral assigné | `SizeError: array size mismatch` |

Ces vérifications ne s'appliquent **pas** aux accès `argv[i]` ni `len(argv)`.

---

## Architecture du compilateur

Le pipeline se déroule en quatre phases :

1. **Lexing / Parsing** via Lark (grammaire EBNF). Le parseur construit un arbre syntaxique abstrait. La grammaire reconnaît notamment : identifiants, `CHAR`, `STRING`, `BOOL`, `FLOAT` (décimal et notation scientifique), `BASE_TYPE` (`int`, `char`, `string`, `bool`, `float`), `BRACKET` (`[]`), opérateurs binaires (`OPBIN`), et commentaires `//`.
2. **Analyse sémantique** intégrée aux fonctions de génération : vérification des types (`expr_type`, `_check_array_elements_type`), résolution des variables (`var_types`), inférence du type de retour des expressions, vérification de cohérence des tailles de tableaux littéraux.
3. **Génération de code** récursive sur l'AST (`asm_expression`, `asm_lhs`, `asm_commande`, `asm_main`). Produit du texte NASM directement, avec compteurs globaux (`cpt` pour les boucles, `bounds_cpt` pour les labels de garde/erreur uniques).
4. **Instanciation du squelette** : le code généré est injecté dans `squelette.asm` via remplacement de marqueurs (`DECL_VARS`, `INIT_VARS`, `COMMAND`, `RETURN`).

Les chaînes littérales sont dédupliquées (table `string_literals`) et déclarées une seule fois en section `.data`, avec échappement des guillemets et des antislashs (`escape_nasm_string`). Les variables scalaires et les pointeurs de tableaux sont toutes en section `.bss`/`.data`, déclarées comme `dq 0` (une seule fois par nom de variable, suivi via l'ensemble `declared_vars`).

`squelette.asm` déclare également les fonctions externes utilisées (`printf`, `atoi`, `strlen`, `malloc`, `calloc`, `strcpy`, `strcat`, `strcmp`, `exit`) et les chaînes de format / messages d'erreur fixes (`format_int`, `format_str`, `format_char`, `format_bounds`, `format_size_mismatch`, `format_null_array`). `format_float` est ajouté dynamiquement par `asm_main`.

---

## Limitations connues

- Pas de fonctions utilisateur : un seul point d'entrée `main`.
- **`if` est reconnu par la grammaire mais non généré par `asm_commande`** : un bloc `if` produit une chaîne vide et n'exécute aucun code conditionnel.
- Pas de `else` ni de `else if`.
- Pas de libération de mémoire (`free`) pour les tableaux : toute réassignation fuit.
- Division entière (`/`) sur deux `int` ne produit pas de `float`, même si le résultat n'est pas entier (troncature vers zéro via `idiv`).
- `%` interdit sur les flottants (erreur de compilation).
- Pas de `!=` (utiliser `== 0` sur le résultat d'une comparaison comme contournement, ou `(int) ... ` selon le contexte).
- Variables globales uniquement (pas de portée de bloc) : toute déclaration, y compris à l'intérieur d'un `while`/`for`, est globale en section `.bss`/`.data`.
- L'initialisation `int[] t = {...};` sans taille déclarée n'effectue aucune vérification de taille (seule la cohérence des types est vérifiée).
- La clause d'initialisation et le pas d'une boucle `for` doivent être des `assignation` (pas de `type x = expr` dans le `for(...)`).