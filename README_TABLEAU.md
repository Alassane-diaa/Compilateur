# Documentation Technique : Gestion des Tableaux dans nanoC

---

## Choix d'Architecture et Layout Mémoire

Pour implémenter les tableaux tout en permettant de connaître leur taille à l'exécution, le choix s'est porté sur un **layout avec en-tête de longueur sur le tas (Heap)**.

Chaque tableau est un pointeur vers un bloc de mémoire alloué dynamiquement via `malloc`. 
Le bloc mémoire est structuré de la manière suivante :

```
Pointeur retourné par malloc (rbx)
       v
+-----------------------+-----------------------+-----------------------+--
| Taille (n)            | Élément 0             | Élément 1             | ...
| (8 octets / qword)    | (8 octets / qword)    | (8 octets / qword)    | 
+-----------------------+-----------------------+-----------------------+--
       ^
       |
 Pointeur utilisateur (rax = rbx)
```

---

## Fonctionnalités supportées

* **Déclarations et Assignations complexes** (avec ou sans taille fixe explicite).
* **Tableaux multidimensionnels** (imbrications de sous-tableaux, accès chaîné du type `t[i][j]`).
* **Extraction de sous-structures** (isoler une ligne d'une matrice pour la stocker dans une référence à une dimension).
* **Lecture de longueur dynamique via `len()**`.
* **Initialisation automatique sécurisée à `0**` pour les déclarations vides.
* **Vérification sémantique stricte des types** à la compilation.

---

## Limitations actuelles

* **Absence de désallocation automatique (`Memory Leaks`)** : Le compilateur n'injecte pas d'instructions de libération de mémoire en fin de portée ou lors d'une réassignation de variable de tableau.
C'est une excellente base ! Pour combler les manques concernant la syntaxe (ce qui est valide, ce qui marche "sous le capot" et ce qui est interdit), voici une version enrichie de votre documentation.

Elle intègre de manière claire et structurée la grammaire supportée, la traduction conceptuelle vers l'assembleur ainsi que les restrictions sémantiques imposées.

---

## Syntaxe et Grammaire

La syntaxe des tableaux dans nanoC imite une déclaration de style C mélangée à des expressions d'initialisation de type accolades :

### 1. Formes de Déclarations Valides

* **Déclaration sans initialisation (Taille fixe)** : Réserve de la mémoire mise à zéro.
```c
int[5] tableau;

```


* **Déclaration avec initialisation littérale** :
```c
int[5] tableau = {1, 2, 3, 4, 5};
int[] t2 = {10, 20}; // Déduction de la taille permise

```


* **Tableaux multidimensionnels (imbriqués)** :
```c
int[3][] matrice = {{1, 2}, {3, 4}, {5, 6}};

```



### 2. Accès et Manipulation

* **Lecture / Écriture par index** : `tableau[2] = 13;`
* **Accès chaîné** : `matrice[1][0]`
* **Mesure de taille** : `len(tableau)`

---

## Éléments syntaxiques et sémantiques NON autorisés

Afin d'éviter tout comportement indéterminé à l'exécution, l'analyseur sémantique du compilateur applique des restrictions strictes dès la phase de compilation :

1. **Hétérogénéité des types interdite** :
Tous les éléments présents à l'intérieur d'un bloc d'accolades d'initialisation doivent correspondre strictement au type de base attendu pour le tableau.
```c
int[] t = {1, 'a', 3}; // ERREUR DE COMPILATION (Type error: expected 'int', got 'char')

```


2. **Incohérence de taille à la déclaration** :
Si une taille explicite constante est fournie à la déclaration, le compilateur rejette statiquement le code si le nombre d'éléments fournis dans l'accolade ne correspond pas.
```c
int[3] t = {1, 2}; // ERREUR DE COMPILATION (Taille déclarée (3) ne correspond pas au nombre d'éléments (2))

```


3. **Incompatibilité d'assignation directe de sous-tableau** :
L'assignation d'une valeur ou d'une expression dans une case de tableau indexée fait l'objet d'un contrôle de type strict.
```c
int[5] tableau;
tableau[0] = "chaîne"; // ERREUR DE COMPILATION (Type error: expected 'int', got 'string')

```
