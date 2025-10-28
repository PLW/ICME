int run()
{                                         // @label name=basic_heap_example
  int a = 5;                              // @push name=a val=5
  float f = 3.14f;                        // @push name=f val=3.14
  int* p = new int[42];                   // @alloc id=H1 label="p→int[42]" size=168
                                          // @bind_ptr name=p id=H1
                                          // @push name=p val="<heap H1>"
  int* q = new int[4]{9,8,7,6};           // @alloc id=H2 label="q→int[4]" size=16
                                          // @bind_ptr name=q id=H2
                                          // @push name=q val="<heap H2>"
  // ..use(p, q);
  delete p;                               // @free id=H1
  a += arr[0];                            // @update_stack name=a val=14
  return a;                               // @leak id=H2
                                          // @pop_stack
                                          // @pop_stack
                                          // @pop_stack
                                          // @pop_stack
}

