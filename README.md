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

Toutes les variables sont stockées en mémoire statique (section `.bss` / `.data`), déclarées comme `dq 0`.

---

## Déclarations et assignations

```c
// Déclaration seule
int x;
float f;
bool flag;

// Déclaration avec initialisation
int x = 42;
float pi = 3.14159;
char c = 'A';
string s = "bonjour";
bool ok = true;

// Assignation simple (variable déjà déclarée)
x = x + 1;
```

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

### Opérateurs binaires

Les opérateurs disponibles sont `+`, `-`, `*`, `/`, `%`, `==`, `<`, `>`, `<=`, `>=`.

Le compilateur détermine le type du résultat selon les types des opérandes :

| Opérandes          | `+` `-` `*` `/`       | `==` `<` `>` `<=` `>=` |
|--------------------|-----------------------|------------------------|
| `int` × `int`      | `int`                 | `bool`                 |
| `float` × `float`  | `float`               | `bool`                 |
| `float` × `int`    | `float` (conv. auto)  | —                      |
| `int` × `float`    | `float` (conv. auto)  | —                      |
| `string` × `string`| `string` (concat `+`) | `bool` (strcmp)        |
| `char` × `char`    | `char`                | —                      |
| `int` × `char`     | `int`                 | —                      |

L'opérateur `%` est interdit si l'un des opérandes est un `float` (erreur de compilation).

### Génération assembleur des opérateurs

Les opérations entières passent par `rax` / `rbx` :

| Opérateur | Instruction NASM      |
|-----------|-----------------------|
| `+`       | `add rax, rbx`        |
| `-`       | `sub rax, rbx`        |
| `*`       | `imul rax, rbx`       |
| `<`       | `setl al`             |
| `>`       | `setg al`             |
| `<=`      | `setle al`            |
| `>=`      | `setge al`            |
| `==`      | `sete al`             |

Les opérations flottantes transitent par `xmm0` / `xmm1` :

| Opérateur | Instruction NASM  |
|-----------|-------------------|
| `+`       | `addsd xmm0, xmm1`|
| `-`       | `subsd xmm0, xmm1`|
| `*`       | `mulsd xmm0, xmm1`|
| `/`       | `divsd xmm0, xmm1`|

Les comparaisons flottantes utilisent `ucomisd` suivi de `setb`, `seta`, `setbe`, `setae`, ou `sete`.

---

## Casts et conversions de type

### Cast explicite

```c
(int) expression    // float → int, tronque via cvttsd2si
(float) expression  // int → float, via cvtsi2sd
```

### Conversion implicite

Quand un `float` et un `int` (ou `char`) sont combinés dans une expression arithmétique, l'entier est automatiquement converti en flottant via `cvtsi2sd`. Le résultat est de type `float`.

Si une expression de type `float` est assignée à une variable déclarée `int`, une troncature implicite est appliquée (`cvttsd2si`).

---

## Flottants : détails d'implémentation

Les littéraux flottants sont représentés en IEEE 754 double précision (64 bits). À la compilation, la valeur est immédiatement convertie en sa représentation hexadécimale 64 bits et chargée via `mov rax, 0x...`. Les registres `xmm0` et `xmm1` ne servent que pour les opérations arithmétiques et les conversions — les flottants transitent par la pile et par `rax` comme les autres types.

```
float x = 3.14;
// → mov rax, 0x40091eb851eb851f   (représentation IEEE 754 de 3.14)
// → mov [x], rax
```

---

## Tableaux

### Layout mémoire

Chaque tableau est alloué sur le tas via `calloc`. Le bloc a la structure suivante :

```
+---------------------+---------------------+---------------------+--
| Taille (n)          | Élément 0           | Élément 1           | ...
| 8 octets            | 8 octets            | 8 octets            |
+---------------------+---------------------+---------------------+--
^
Pointeur stocké dans la variable
```

La taille est encodée dans les 8 premiers octets (en-tête), ce qui rend `len()` possible à l'exécution sans métadonnée externe.

Les tableaux `argv` font exception : ils utilisent le layout C brut (pas d'en-tête de longueur).

### Déclarations

```c
// Taille fixe, initialisé à zéro
int[5] t;

// Avec littéral (taille déduite)
int[] t = {1, 2, 3};

// Taille fixe + littéral (doit correspondre)
int[3] t = {10, 20, 30};

// Tableaux de flottants
float[] f = {1.0, 2.5, 3.14};

// Tableaux multidimensionnels
int[3][] mat = {{1, 2}, {3, 4}, {5, 6}};
```

### Accès et manipulation

```c
t[2]           // lecture de l'élément d'indice 2
t[0] = 99;     // écriture
mat[1][0]      // accès chaîné (tableau de tableaux)
len(t)         // longueur → int, lit l'en-tête à [pointeur - 8]
```

L'accès par index génère le séquence assembleur suivante :
1. Évaluation du tableau → `rax` (pointeur vers l'en-tête)
2. Évaluation de l'index → `rax`, push/pop pour préserver le pointeur
3. `imul rax, 8` pour l'offset en octets
4. `add rax, rbx` puis `mov rax, [rax]`

### Restrictions sur les tableaux

- **Hétérogénéité interdite** : tous les éléments d'un littéral doivent avoir le même type de base. Un cast explicite est nécessaire si les types diffèrent :
  ```c
  float[] t = {1.5, 2};           // ERREUR (int dans un float[])
  float[] t = {1.5, (float) 2};   // OK
  int[] t = {1, 'a', 3};          // ERREUR (char dans un int[])
  ```

- **Incohérence de taille** : si une taille explicite est fournie, elle doit correspondre exactement au nombre d'éléments du littéral :
  ```c
  int[3] t = {1, 2};              // ERREUR (3 ≠ 2)
  ```

- **Type d'assignation** : l'écriture dans une case fait l'objet d'une vérification de type :
  ```c
  int[5] t;
  t[0] = "texte";                 // ERREUR (string dans un int[])
  ```

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

Les accolades sont obligatoires. Le corps d'une structure de contrôle peut contenir une séquence de commandes (plusieurs instructions enchaînées). Les conditions sont évaluées comme des entiers : 0 est faux, tout autre valeur est vraie.

---

## Fonctions built-in

### `print(expression)`

Affiche une valeur sur la sortie standard via `printf`. Le format est sélectionné automatiquement selon le type de l'expression :

| Type     | Format utilisé | Mécanisme                                  |
|----------|----------------|--------------------------------------------|
| `int`    | `%d`           | `rsi` ← valeur, `xor rax, rax`             |
| `float`  | `%f\n`         | `xmm0` ← valeur, `rax` ← 1                |
| `char`   | `%c`           | `rsi` ← valeur, `xor rax, rax`             |
| `string` | `%s`           | `rsi` ← pointeur, `xor rax, rax`           |
| `bool`   | `%d`           | (traité comme int)                         |

### `len(expression)`

Renvoie la longueur d'un tableau sous forme d'`int`. Pour les tableaux nanoC, lit l'en-tête de 8 octets situé au début du bloc mémoire. Pour `argv`, renvoie `argc` directement.

### `charAt(s, i)`

Renvoie le `char` à la position `i` dans la chaîne `s`. Génère :

```nasm
mov rcx, i      ; index
mov rdx, s      ; pointeur chaîne
movzx eax, byte [rdx + rcx]
```

### Concaténation de chaînes

L'opérateur `+` sur deux `string` génère une concaténation à l'exécution via `strlen`, `malloc`, `strcpy` et `strcat`. Fonctionne avec des valeurs dynamiques (pas seulement des littéraux).

---

## Architecture du compilateur

Le pipeline se déroule en quatre phases :

1. **Lexing / Parsing** via Lark (grammaire EBNF). Le parseur construit un arbre syntaxique abstrait.
2. **Analyse sémantique** intégrée aux fonctions de génération : vérification des types, résolution des variables, inférence du type de retour des expressions (`expr_type`).
3. **Génération de code** récursive sur l'AST (`asm_expression`, `asm_commande`, `asm_main`). Produit du texte NASM directement.
4. **Instanciation du squelette** : le code généré est injecté dans `squelette.asm` via remplacement de marqueurs (`DECL_VARS`, `INIT_VARS`, `COMMAND`, `RETURN`).

Les chaînes littérales sont dédupliquées (table `string_literals`) et déclarées une seule fois en section data. Les variables scalaires et tableaux sont toutes en section BSS/data, déclarées comme `dq 0`.

---

## Limitations connues

- Pas de fonctions utilisateur : un seul point d'entrée `main`.
- Pas de `else` ni de `else if`.
- Pas de libération de mémoire (`free`) pour les tableaux : toute réassignation fuit.
- Division entière (`/`) sur deux `int` ne produit pas de `float`, même si le résultat n'est pas entier.
- `%` interdit sur les flottants.
- Comparaisons `<`, `>`, `<=`, `>=` non définies entre `int` et `float` dans la table de types (nécessite un cast explicite).
- Pas de `!=` (utiliser `== 0` sur le résultat d'une comparaison comme contournement).
- Variables globales uniquement (pas de portée de bloc).