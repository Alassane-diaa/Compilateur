extern printf, atoi, strlen, malloc
section .data
argv: dq 0
format_int: db "%lld",10, 0
format_str: db "%s",10, 0
format_char: db "%c",10, 0
DECL_VARS
global main
section .text
main:
push rbp
mov rbp, rsp
mov [argv], rsi
INIT_VARS
COMMAND
RETURN
pop rbp
ret