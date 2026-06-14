## Pipeline
```bash
./nanoc.sh source.c
./source.out "coucou"
```

Notes:
- main is fixed to `main(int argc, char* argv)`.
- `argc` and `argv` are stored directly from the C ABI (no length prefix for `argv`).
- `argv[i]` reads the raw C pointer array; `len(argv)` returns `argc`.
- Arrays still use the length-prefixed layout internally; index typing is permissive (index keeps base array type, like before).
- String concatenation supports runtime values using `strlen`, `malloc`, `strcpy`, and `strcat`.
- `charAt(s, i)` returns a `char`. Assembly: evaluate `i` into `rcx`, `s` into `rdx`, then `movzx eax, byte [rdx + rcx]`.