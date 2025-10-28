
void heap()
{                                       // @label name=smart_ptr_example
  char* a = new char[100];              // @alloc id=H1 label="a→char[100]" size=100
                                        // @bind_ptr name=a id=H1
                                        // @push name=a val="<heap H1>"
  int* b = new int[100];                // @alloc id=H2 label="b→int[100]" size=400
                                        // @bind_ptr name=b id=H2
                                        // @push name=b val="<heap H2>"
  auto c = b;                           // @push name=c val="[b]"
  delete[] a;                           // @free id=H1
}                                       // @pop_stack
                                        // @leak id=H2
                                        // @pop_stack
                                        // @pop_stack
                                        // @pop_stack

