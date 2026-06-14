#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <fichier_source.c>"
    exit 1
fi

SOURCE_FILE="$1"

DIR_NAME=$(dirname "$SOURCE_FILE")
BASE_NAME=$(basename "$SOURCE_FILE" .c)

EXE_PATH="$DIR_NAME/$BASE_NAME.out"

python3 nanoC.py "$SOURCE_FILE"
if [ $? -ne 0 ]; then
    exit 1
fi

nasm -f elf64 resultat.asm -o resultat.o
if [ $? -ne 0 ]; then
    exit 1
fi

gcc -no-pie resultat.o -o "$EXE_PATH"
if [ $? -ne 0 ]; then
    exit 1
fi

rm -f resultat.asm resultat.o
echo "Compilation réussie : $EXE_PATH"