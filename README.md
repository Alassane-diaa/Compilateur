## Pipeline
```python
python nanoC.py  
nasm -f elf64 resultat.asm  
gcc -no-pie resultat.o
./a.out 3 5
```