
struct Node {
  std::shared_ptr<Node> next; 
  std::weak_ptr<Node> prev; 
};

void shared_ptr_cycle() {
  auto a = std::make_shared<Node>();    // @sp_alloc id=H1 label="[a]→Node"
                                        // @bind_ptr name=a id=H1
                                        // @push name=a val="<heap H1>"
  auto b = std::make_shared<Node>();    // @sp_alloc id=H2 label="[b]→Node"
                                        // @bind_ptr name=b id=H2
                                        // @push name=b val="<heap H2>"
  a->next = b;                          // @sp_inc id=H2
  b->prev = a;                          // 
}                                       // @pop_stack
                                        // @sp_dec id=H2
                                        // @pop_stack
                                        // @sp_dec id=H1
                                        // @free id=H1
                                        // @sp_dec id=H2
                                        // @pop_stack
                                        // @free id=H2



