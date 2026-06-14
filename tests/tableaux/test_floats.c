main(int argc, char* argv) {
    print("========================================");
    print("      TESTS INTENSIFS DES FLOATS        ");
    print("========================================");

    // ---------------------------------------------------------
    // 1. GESTION DES SIGNES ET DE LA NOTATION SCIENTIFIQUE
    // ---------------------------------------------------------
    print("--- 1. SIGNES ET EXTREMES ---");
    float f_pos = 9999.99;
    float f_neg = -1234.56;   
    float f_zero = 0.0;
    
    print("Positif (9999.99) :"); print(f_pos);
    print("Negatif (-1234.56) :"); print(f_neg);
    print("Soustraction avec negatif (Attendu: 11234.55) :"); print(f_pos - f_neg);
    
    float sci_negatif = -2.5e-3;
    float sci_positif = 1.0E+5;
    print("Scientifique negatif (-0.0025) :"); print(sci_negatif);
    print("Scientifique positif (100000.0) :"); print(sci_positif);

    // ---------------------------------------------------------
    // 2. ARITHMETIQUE LOURDE ET CHAINEE
    // ---------------------------------------------------------
    print("--- 2. EMPILAGE D'OPERATIONS FLOTTANTES ---");
    // Ce test vérifie que le push/pop de la pile fonctionne bien
    // pour garder les résultats temporaires en évitant d'écraser xmm0/xmm1
    float a = 3.14159;
    float b = 2.71828;
    float c = 1.61803;
    float lourd = ((a * b) + c) / 2.0;
    print("((3.14159 * 2.71828) + 1.61803) / 2.0 (Attendu: ~5.078) :");
    print(lourd);

    // ---------------------------------------------------------
    // 3. CASTS EXTREMES ET PROMOTIONS
    // ---------------------------------------------------------
    print("--- 3. CASTS ET TRONCATURES ---");
    int i_neg = (int) -42.8;
    print("Cast de -42.8 vers int (Attendu: -42) :"); print(i_neg);
    
    float f_from_int = (float) 65; 
    print("Cast de 65 vers float (Attendu: 65.0) :"); print(f_from_int);
    
    int compteur = 10;
    float decale = compteur + 0.5;
    print("10 + 0.5 promotion implicite (Attendu: 10.5) :"); print(decale);

    // ---------------------------------------------------------
    // 4. Comparaisons
    // ---------------------------------------------------------
    print("--- 4. COMPARAISONS");
    float x1 = 0.3;
    float x2 = 0.1 + 0.2; 
    
    print("0.3 == (0.1 + 0.2) (Souvent 0 à cause de l'imprecision IEEE) :");
    print(x1 == x2);
    
    print("0.3 <= 0.3001 (Attendu: 1) :");
    print(x1 <= 0.3001);

    // ---------------------------------------------------------
    // 5. STRUCTURES DE CONTROLE AVEC DES FLOTTANTS
    // ---------------------------------------------------------
    print("--- 5. BOUCLE WHILE AVEC ACCUMULATEUR FLOAT ---");
    float somme = 0.0;
    float step = 0.5;
    int iterations = 0;
    
    while (somme < 5.0) {
        somme = somme + step;
        iterations = iterations + 1;
    }
    print("Iterations pour atteindre 5.0 avec pas de 0.5 (Attendu: 10) :");
    print(iterations);
    print("Valeur finale de l'accumulateur (Attendu: 5.0) :");
    print(somme);

    // ---------------------------------------------------------
    // 6. MANIPULATION LOURDE DE TABLEAUX DE FLOATS
    // ---------------------------------------------------------
    print("--- 6. ITERATION SUR TABLEAU DE FLOATS ---");
    float[] stats = { -1.1, 2.5e2, 0.003, 42.0 }; // 2.5e2 = 250.0
    print("Taille tableau stats (Attendu: 4) :"); print(len(stats));
    
    float stats_sum = 0.0;
    int k = 0;
    while (k < len(stats)) {
        stats_sum = stats_sum + stats[k];
        k = k + 1;
    }
    print("Somme (-1.1 + 250.0 + 0.003 + 42.0 = ~290.903) :");
    print(stats_sum);

    print("========================================");
    print("           FIN DES TESTS                ");
    print("========================================");

    return (0);
}