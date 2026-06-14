main(int argc, char* argv) {
    int[2][] matrice = {{10, 20, 30}, {40, 50}};
    
    int[] ligne = matrice[0];
    print(len(matrice)); // Affiche 2
    print(len(ligne));   // Affiche 3
    print(matrice[1][1]); // Affiche 50

    return (0);
}