#include <cstdio>
#include <stdlib.h>

int a(int n) { 
    int i = 10, r = 2*i+n;
    return r;
}


int b(int n) {
    int j = 20, r = 3*j+n;
    return r;
}


int c(int n) {
    int m = 30, r = 4*m+n;
    return r;
}


int h(int n) {
    int k = 40, r = c(k+n);
    return r;
}


int g(int n) {
    int q = 40, r = a(q+n), s = b(r);
    return s;
}

int f(int n) { 
    int p = 10, r = g(p+n), s = h(r);
    return s;
}

int main() {
  printf("=> %d\n",f(10)); 
}

