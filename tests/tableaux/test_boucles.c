main(int argc, char* argv) {
    int[5] t = {10, 20, 30, 40, 50};
    
    for (int i = 0; i < len(t); i = i + 1) {
        t[i] = t[i] + 5;
    }

    int somme = 0;
    int k = 0;
    while (k < len(t)) {
        print(t[k]);
        somme = somme + t[k];
        k = k + 1;
    }
    print(somme);

    int[2][] matrice = {{1, 2}, {3, 4, 5}};

    for (int p = 0; p < len(matrice); p = p + 1) {
        int[] row = matrice[p];
        for (int j = 0; j < len(row); j = j + 1) {
            print(row[j]);
        }
    }

    return (somme);
}