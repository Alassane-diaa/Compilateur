main(int argc, char* argv) {
    bool[3] drapeaux = {true, false, true};
    
    string s1 = "test";
    string s2 = "test";
    
    // Validation du cas d'affectation bool_str vers bool
    drapeaux[1] = s1 == s2; 
    print(drapeaux[1]);

    return (0);
}