#include <coroutine>
#include <iostream>
#include <optional>

// ===========================================================
// Minimal generator type (stackless coroutine)
// ===========================================================

template <typename T>
struct Generator {
    // --- Promise type defines coroutine behavior ---
    struct promise_type {
        std::optional<T> current_value;

        Generator get_return_object() {
            return Generator{
                std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        std::suspend_always initial_suspend() noexcept { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }

        std::suspend_always yield_value(T value) noexcept {
            current_value = std::move(value);
            return {};
        }

        void return_void() noexcept {}
        void unhandled_exception() { std::terminate(); }
    };

    // --- Members ---
    using handle_type = std::coroutine_handle<promise_type>;
    handle_type coro = nullptr;

    explicit Generator(handle_type h) : coro(h) {}
    Generator(const Generator&) = delete;
    Generator(Generator&& other) noexcept : coro(other.coro) { other.coro = nullptr; }
    ~Generator() { if (coro) coro.destroy(); }

    // --- Iterator interface ---
    struct iterator {
        handle_type coro;
        bool done = false;

        void operator++() {
            coro.resume();
            done = coro.done();
        }
        const T& operator*() const { return *coro.promise().current_value; }
        bool operator==(std::default_sentinel_t) const { return done; }
    };

    iterator begin() {
        if (coro) {
            coro.resume();
            return iterator{coro, coro.done()};
        }
        return iterator{nullptr, true};
    }

    std::default_sentinel_t end() { return {}; }
};

// ===========================================================
// Example producer coroutine
// ===========================================================

Generator<int> produce_values(int n) {
    for (int i = 0; i < n; ++i)
        co_yield i * i;  // yields squares
}

// ===========================================================
// Consumer
// ===========================================================

int main() {
    auto gen = produce_values(5); // producer coroutine

    std::cout << "Squares produced:\n";
    for (int v : gen) {           // consumer loop
        std::cout << "  " << v << "\n";
    }

    std::cout << "Done.\n";
}

