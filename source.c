main(int argc, char* argv) {
    
    bool hp1 = false;
    bool hp2 = true;
    bool hp3 = hp1 == hp2;
    int c = 1 + 2;
    int h = len(argv);
    int x = 1;
    int y = 2;
    
    char a = 'a';
    char b = 'b';
    bool hp5 = a < b;
    print(hp5);
    string s = argv[h-1];
    string s1 = "hello1";
    string s3;
    char f = charAt(s1, 0);
    print(f);
    s = argv[1];
    s3 = ""+"coucou";
    string s2 = s1 + s;
    print(s);
    print(s3);
    bool hp4;
    hp4 = s1 == s;
    print(hp4);
    int[] tableau = {1, 2, 3, 4, 5};
    tableau[2] = 13;
    x = tableau[2];
    print(x);
    int z = len(tableau);
    print(z);
    int[][] tableau2 = {{1, 2}, {3, 4}, {5, 6}};
    int[] extrait = tableau2[1];
    int size = len(tableau2[0]);
    print(size);
    print(len(extrait));
    y = tableau[1];
    print(tableau2[1][0]);
    print(tableau2[1][1]);
    return (y);
}