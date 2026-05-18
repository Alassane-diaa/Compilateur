extern printf, atoi
section .data
argv: dq 0
format: db "%lld",10, 0
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