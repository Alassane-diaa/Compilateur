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
    // Si tu décommentes la ligne suivante, le compilateur plantera avec :
    // "Erreur fatale: Variable non déclarée 'variable_non_declaree'"
    // variable_non_declaree = 50.0;

    return (0);
}