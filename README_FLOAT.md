# Documentation Technique : Intégration du type Float dans nanoC

---

## Choix d'Architecture et Layout Mémoire

L'intégration des nombres à virgule flottante (`float`) repose sur le standard **IEEE 754** (double précision, 64 bits), ce qui permet aux flottants d'avoir la même taille que les pointeurs et les entiers (`qword`). Ils peuvent ainsi transiter par la pile et les registres classiques (`rax`, `rbx`) sans modifier l'architecture du compilateur.

Cependant, les opérations arithmétiques et de conversions nécessitent l'utilisation de l'unité de calcul matériel FPU/SSE2 de l'architecture x86_64, et transitent donc temporairement par les registres vectoriels **`xmm0`, `xmm1`**.

Les tableaux de floats (`float[]`) partagent exactement le même layout mémoire que les autres tableaux (en-tête de longueur de 8 octets suivi des éléments).

---

## Fonctionnalités supportées

* **Grammaire Étendue et Notation Scientifique** : Support natif par le lexer Lark pour les flottants classiques (`3.14`) et la notation scientifique (`1.5e-10`, `2E+5`).
* **Opérations Arithmétiques dédiées** : Les symboles usuels (`+`, `-`, `*`, `/`) sont mappés sur les instructions assembleur flottantes (`addsd`, `subsd`, `mulsd`, `divsd`).
* **Conversions et Casts** :
  * **Cast Dynamique Explicite** : Syntaxe `(int) expression` ou `(float) expression` (utilise `cvttsd2si` ou `cvtsi2sd`).
  * **Conversions Implicites** : float + int (ou char) renvoie implicitement un `int` (troncature).
* **Tableaux de Flottants (`float[]`)** : Déclaration, initialisation littérale, bounds checking et `len()`.
* **Affichage Natif (`print`)** : Détecte le type `float` et utilise un format `%f` dynamiquement injecté.

---

## Éléments syntaxiques et sémantiques NON autorisés

1. **Absence de déclaration de type** :
   Une variable ne peut pas être assignée sans avoir été explicitement déclarée. Le compilateur lève une exception statique (NameError).

2. **Hétérogénéité dans les tableaux** :
   Il est interdit de mélanger des entiers et des flottants dans un même littéral de tableau, sauf cast explicite :
   ```c
   float[] t = {1.5, 2}; // ERREUR DE COMPILATION
   float[] t_valide = {1.5, (float) 2}; // OK