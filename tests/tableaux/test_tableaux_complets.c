main(int argc, char* argv) {
    // 1. Validation de la mise à zéro par défaut (calloc)
    int[3] t_auto;
    print(t_auto[0]);
    print(t_auto[1]);
    print(t_auto[2]);

    // 2. Initialisation littérale et modification d'éléments
    int[4] t_statique = {100, 200, 300, 400};
    t_statique[1] = 250;
    t_statique[3] = 450;
    
    // 3. Mesure de taille dynamique (len)
    int taille_statique = len(t_statique);
    print(taille_statique);

    // 4. Parcours simple avec boucle for
    int somme = 0;
    for (int i = 0; i < len(t_statique); i = i + 1) {
        print(t_statique[i]);
        somme = somme + t_statique[i];
    }
    print(somme);

    // 5. Validation du typage strict sur d'autres types de base (char et bool)
    char[2] lettres = {'x', 'y'};
    print(lettres[0]);

    bool[2] verifications;
    string s_argv = argv[0];
    verifications[0] = s_argv == "nanoC"; // Test de l'équivalence bool_str / bool
    verifications[1] = false;
    print(verifications[0]);

    // 6. Structure multidimensionnelle complexe (Matrice asymétrique)
    int[3][] grille = {{1, 2}, {3, 4, 5}, {6}};
    print(len(grille)); // Taille de la première dimension

    // 7. Extraction de sous-structure (Ligne complète)
    int[] sous_ligne = grille[1];
    print(len(sous_ligne)); // Devrait afficher 3
    print(sous_ligne[1]);   // Devrait afficher 4

    // 8. Parcours complet d'une structure multidimensionnelle par boucles imbriquées
    for (int p = 0; p < len(grille); p = p + 1) {
        int[] curseur_ligne = grille[p];
        for (int j = 0; j < len(curseur_ligne); j = j + 1) {
            print(curseur_ligne[j]);
        }
    }

    // Renvoie un élément modifié pour valider l'exécution de fin du main
    return (t_statique[1]);
}