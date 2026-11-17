"""Thử thách (puzzle) – tình huống cố định, phải hạ đối thủ trong MỘT lượt.
Mỗi thử thách dạy một ý tưởng và mở khoá thẻ mới khi hoàn thành."""

PUZZLES = [
    {
        "id": "p1", "topic": "Sắp xếp & Tìm kiếm",
        "title": "Tiền điều kiện của tìm kiếm nhị phân",
        "goal": "Hạ đối thủ 8 HP trong 1 lượt.",
        "hand": ["linear_search", "binary_search", "linear_search", "quick_sort"],
        "energy": 3, "enemy_hp": 8, "challenge": "phonebook",
        "hint": "Tìm kiếm nhị phân chỉ chạy được trên dữ liệu ĐÃ SẮP XẾP.",
        "lesson": "Quick Sort O(n log n) một lần rồi tìm nhị phân O(log n) nhiều lần là chiến lược kinh điển.",
        "unlocks": ["binary_search", "quick_sort"],
    },
    {
        "id": "p2", "topic": "Tham lam & Quy hoạch động",
        "title": "Balo 0/1 – đừng tham lam!",
        "goal": "Hạ đối thủ 12 HP trong 1 lượt. Bạn đã chơi BFS, DFS, Queue trước đó (memo = 3).",
        "hand": ["greedy", "dp", "stack", "linear_search"],
        "memo": ["bfs", "dfs", "queue"],
        "energy": 4, "enemy_hp": 12, "challenge": "knapsack",
        "hint": "Greedy là bẫy với Balo 0/1. DP mạnh hơn khi bảng memo có nhiều kết quả con hơn.",
        "lesson": "DP tái sử dụng kết quả bài toán con; Greedy chỉ đúng khi có tính chất lựa chọn tham lam.",
        "unlocks": ["dp"],
    },
    {
        "id": "p3", "topic": "Đồ thị",
        "title": "Cạnh âm trên đồ thị tỷ giá",
        "goal": "Hạ đối thủ 10 HP trong 1 lượt.",
        "hand": ["dijkstra", "bfs", "bellman_ford", "greedy"],
        "energy": 5, "enemy_hp": 10, "challenge": "arbitrage",
        "hint": "Dijkstra sai khi có cạnh âm.",
        "lesson": "Bellman-Ford chậm hơn (O(V·E)) nhưng là lựa chọn đúng khi đồ thị có cạnh âm.",
        "unlocks": ["bellman_ford"],
    },
    {
        "id": "p4", "topic": "Đệ quy",
        "title": "Điểm dừng của đệ quy",
        "goal": "Hạ đối thủ 14 HP trong 1 lượt. Memo hiện có: Stack, Queue.",
        "hand": ["recursion", "greedy", "dp", "greedy"],
        "memo": ["stack", "queue"],
        "energy": 7, "enemy_hp": 14, "challenge": "fibonacci",
        "hint": "Đệ quy dùng toàn bộ năng lượng: độ sâu ≥ 6 sẽ tràn ngăn xếp. Fibonacci cần DP.",
        "lesson": "Đệ quy cần điểm dừng và độ sâu hợp lý; Fibonacci đệ quy thuần là O(2^n), DP là O(n).",
        "unlocks": ["recursion"],
    },
    {
        "id": "p5", "topic": "Hàng đợi ưu tiên",
        "title": "Ai nguy kịch nhất?",
        "goal": "Hạ đối thủ 9 HP trong 1 lượt.",
        "hand": ["queue", "dijkstra", "heap", "bellman_ford"],
        "energy": 4, "enemy_hp": 9, "challenge": "topk",
        "hint": "Heap luôn lấy ra phần tử có độ ưu tiên (chi phí) lớn nhất trên tay.",
        "lesson": "Heap cho thao tác lấy max O(log n) – cốt lõi của lập lịch ưu tiên và Dijkstra.",
        "unlocks": ["heap"],
    },
    {
        "id": "p6", "topic": "Stack & Queue",
        "title": "Undo theo thứ tự LIFO",
        "goal": "Hạ đối thủ 9 HP trong 1 lượt.",
        "hand": ["undo", "greedy", "bfs", "queue"],
        "energy": 5, "enemy_hp": 9, "challenge": "undo_editor",
        "hint": "Pop/Hoàn tác trả về thẻ chơi GẦN NHẤT. Thứ tự chơi quyết định thẻ nào quay lại.",
        "lesson": "Stack: phần tử vào sau ra trước – Undo luôn hoàn tác thao tác mới nhất.",
        "unlocks": ["undo"],
    },
]

PUZZLE_BY_ID = {p["id"]: p for p in PUZZLES}
