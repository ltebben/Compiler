#ifndef RUNTIME_H_INCLUDED
#define RUNTIME_H_INCLUDED

int putinteger(int *);
int putfloat(double *);
int putstring(char s[]);
int putbool(int *);
int strcomp(char s1[], char s2[]);

int getinteger();
double getfloat();
int getstring(char s[]);
int getbool();
double sqrtt(double *);

#endif