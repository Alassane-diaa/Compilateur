main(int argc, char* argv) {
    // 1. Déclarations strictes (le compilateur rejetterait "x = 5;" sans type)
    float pi = 3.1415;
    float rayon = 10.0;
    
    // 2. Opérations usuelles sur les floats
    float surface = pi * rayon * rayon;
    print("--- Operations usuelles ---");
    print("Surface (doit etre ~314.15) :");
    print(surface);
    
    // 3. Puissances de 10 (Notation scientifique)
    float grand_nombre = 1.5E+3;   // 1500.0
    float petit_nombre = 2.5e-1;   // 0.25
    print("--- Puissances de 10 ---");
    print(grand_nombre);
    print(petit_nombre);

    // 4. Conversions implicites : float + int = int (selon tes specs)
    int entier_dix = 10;
    float cinq_virgule_cinq = 5.5;
    int resultat_implicite1 = cinq_virgule_cinq + entier_dix; 
    // Fait 5.5 + 10 -> troncature -> 15
    print("--- Conversions implicites (float + int -> int) ---");
    print("5.5 + 10 = (attendu 15) :");
    print(resultat_implicite1);

    // 5. Conversions implicites : float + char = int
    char lettre_A = 'A'; // Le code ASCII de 'A' est 65
    float deux_virgule_huit = 2.8;
    int resultat_implicite2 = deux_virgule_huit + lettre_A; 
    // Fait 2.8 + 65 -> 67.8 -> troncature -> 67
    print("--- Conversions implicites (float + char -> int) ---");
    print("2.8 + 'A' = (attendu 67) :");
    print(resultat_implicite2);

    // 6. Casts explicites
    int cast_vers_entier = (int) 9.99; // Va tronquer à 9
    float cast_vers_float = (float) 42; // Va convertir en 42.0
    print("--- Casts explicites ---");
    print("(int) 9.99 = (attendu 9) :");
    print(cast_vers_entier);
    print("(float) 42 = (attendu 42.0) :");
    print(cast_vers_float);

    // --- TEST D'ERREUR (Commenté pour que le programme compile) ---
    // "Erreur fatale: Variable non déclarée 'variable_non_declaree'"
    // variable_non_declaree = 50.0;

    return (0);
}

main(int argc, char* argv) {
    // ----------------------------------------------------
    // TEST 1 : RAPPEL SUR LES FLOATS SIMPLES ET CONVERSIONS
    // ----------------------------------------------------
    float pi = 3.1415;
    float rayon = 10.0;
    float surface = pi * rayon * rayon;
    
    print("--- Tests basiques ---");
    print(surface); // Attendu ~314.15
    
    // Notation scientifique et puissances de 10
    float grand_nombre = 1.5E+2; // 150.0
    print("Notation E+2 :");
    print(grand_nombre);
    
    // ----------------------------------------------------
    // TEST 2 : TABLEAUX DE FLOATS (FLOAT[])
    // ----------------------------------------------------
    print("--- Tests des Tableaux de Floats ---");
    
    // Déclaration et initialisation par accolades
    float[] temperatures = {22.5, 19.8, 24.1, 15.0e-1};
    
    // Test de l'opérateur 'len()' sur un float[]
    print("Taille du tableau :");
    print(len(temperatures)); // Attendu 4
    
    // Lecture des éléments du tableau par index
    print("Temperature a l'index 0 (attendu 22.5) :");
    print(temperatures[0]);
    print("Temperature a l'index 3 avec e-1 (attendu 1.5) :");
    print(temperatures[3]);

    // Modification d'un élément du tableau
    print("Modification de l'index 1 à 42.42...");
    temperatures[1] = 42.42;
    
    print("Nouvelle valeur a l'index 1 :");
    print(temperatures[1]);

    // ----------------------------------------------------
    // TEST 3 : TABLEAU ET CONVERSIONS EXPLICITES
    // ----------------------------------------------------
    print("--- Test des casts dans les tableaux ---");
    
    // Comme le typage est fort, on ne peut pas mettre de int 
    // directement dans un float[], mais on peut le "caster" :
    float[] mix_cast = {1.1, (float) 5, 3.3};
    print("Valeur a l'index 1 issue d'un cast (attendu 5.0) :");
    print(mix_cast[1]);

    return (0);
}