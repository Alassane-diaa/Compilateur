## Pipeline
```python
python nanoC.py  
nasm -f elf64 resultat.asm  
gcc -no-pie resultat.o
./a.out "hello"
```

Notes (June 3, 2026):
- main is fixed to `main(int argc, char* argv)`.
- `argc` and `argv` are stored directly from the C ABI (no length prefix for `argv`).
- `argv[i]` reads the raw C pointer array; `len(argv)` is not supported.
- String concatenation now supports runtime values using `strlen`, `malloc`, `strcpy`, and `strcat`.