
#include <iostream>
#include <random>
#include <chrono>
#include <cstdio>

extern "C" void dump_heap_blocks(const char *out_path, unsigned max_ranges_per_callback);

char* randomAlloc() {
    int N = 100; 
    int pageSize = (1<<10); // 1K
    std::mt19937 eng(std::chrono::high_resolution_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<> dist(1, N); // uniform distribution[1, N]
    int r = pageSize*dist(eng);
    std::cout << "alloc(" << r << ")" << std::endl;
    return (char*)malloc(r); // alloc block of random size
}

int main(int argc, char* argv[]) {
    char buf[64];
    char* aloc_0[1024];
    char* aloc_1[256];
    for (int i=0; i<1024; ++i) {
        aloc_0[i] = randomAlloc();
    }
    for (int j=0; j<256; ++j) {
        snprintf(buf, 64, "heapdump.%d.json", j);
        aloc_1[j] = randomAlloc();
        dump_heap_blocks(buf, 0);
    }
}

