
void smart_ptr()
{                                       // @label name=smart_ptr_example
  int p = 10;                           // @push name=p val=10
  int q = 20;                           // @push name=q val=20
  int r = 30;                           // @push name=r val=30
  int s = 40;                           // @push name=s val=40
  char* a = new char[100];              // @alloc id=H1 label="a→char[100]" size=100
                                        // @bind_ptr name=a id=H1
                                        // @push name=a val="<heap H1>"
  int* b = new int[100];                // @alloc id=H2 label="b→float[100]" size=400
                                        // @bind_ptr name=b id=H2
                                        // @push name=b val="<heap H2>"
  auto c = std::make_shared<int>(100);  // @sp_alloc id=H3 label="[c]→int[100]" size=400
                                        // @bind_ptr name=c id=H3
                                        // @push name=c val="<heap H3>"
  auto d = c;                           // @sp_inc id=H3
                                        // @push name=d val="[c]"
  s += 10;                              // @update_stack name=s val=50
  delete[] a;                           // @free id=H1
  auto e = std::make_shared<int>(10);   // @sp_alloc id=H4 label="[e]→int[10]" size=40
                                        // @bind_ptr name=e id=H4
                                        // @push name=e val="[<heap H4>]"
}                                       // @pop_stack
                                        // @free id=H4
                                        // @pop_stack
                                        // @sp_dec id=H3
                                        // @pop_stack
                                        // @free id=H3
                                        // @pop_stack
                                        // @leak id=H2
                                        // @pop_stack
                                        // @pop_stack
                                        // @pop_stack
                                        // @pop_stack
                                        // @pop_stack

