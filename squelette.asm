extern printf, atoi, strlen, malloc, strcpy, strcat, strcmp, exit
section .data
format_int: db "%lld",10, 0
format_str: db "%s",10, 0
format_char: db "%c",10, 0
format_bounds: db "IndexError: array index out of bounds",10, 0
DECL_VARS
global main
section .text
main:
push rbp
mov rbp, rsp
INIT_VARS
COMMAND
RETURN
pop rbp
ret