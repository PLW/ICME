
int recurse(int n)                      // @label name=recurse
{                                       // @push name=n val=n
  int p = 10;                           // @push name=p val=10
  int q = 20;                           // @push name=q val=20
  char* a = new char[100];              // @alloc id=H1 label="char[100]" size=100
                                        // @bind_ptr name=a id=H1
                                        // @push name=a val="<heap H1>"
  float* b = new float[1000];           // @alloc id=H2 label="float[1000]" size=4000
                                        // @bind_ptr name=b id=H2
                                        // @push name=b val="<heap H2>"
  if (n <= 0) return 0;                 // @ret
  delete[] a;                           // @free id=H1
  int r = recurse(n-1);                 // (no directive)
                                        // @call target=recurse arg="n-1"
  return r + 1;                         // @ret func=recurse
}                                       // @unwind

