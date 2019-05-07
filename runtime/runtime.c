#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#include "runtime.h"

int putinteger(int i) {
    printf("%i\n", i);
    return 1;
}

int putfloat(double d) {
    printf("%f\n", d);
    return 1;
}

int putstring(char s[])
{
    printf("%s\n", s);
    return 1;
}

int strcomp(char s1[], char s2[]) {
    if (strcmp(s1, s2) == 0) {
        return 1;
    }
    return 0;
}

int putbool(int b) {
    if (b == 0) {
        printf("false\n");
    } else {
        printf("true\n");
    }
    return 1;
}

int getinteger() {
    int ret;
    char in[256];
    fgets(in, 256, stdin);
    sscanf(in,  " %i", &ret);
    return ret;
}

double getfloat() {
    float ret;
    char in[256];
    fgets(in, 256, stdin);
    sscanf(in, " %f", &ret);
    return ret;
}

double sqrtt(int n) 
{ 
    double x = n; 
    double y = 1; 
    double e = 0.000001;
    while (x - y > e) { 
        x = (x + y) / 2; 
        y = n / x; 
    } 
    return x; 
} 

int getstring(char s[]) {
    fgets(s, 256, stdin);
    for (int i=0; i<256; i++){
        if (s[i] == '\n') {
            s[i] = '\0';
            break;
        }
        s[i] = tolower(s[i]);
    }
    return 1;
}

int getbool() {
    char in[256];
    fgets(in, 256, stdin);
    if (strncmp(in, "true", 4) == 0 ) {
      return 1;
    }
    else {
      return 0;
    }
}