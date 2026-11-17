"""Danh mục thẻ bài: mỗi thẻ đại diện cho một cấu trúc dữ liệu / chiến lược thuật toán.

Quy ước:
- cost: năng lượng cần để chơi. cost = -1 nghĩa là "X" (dùng toàn bộ năng lượng còn lại).
- Chi phí được thiết kế tỉ lệ với độ phức tạp thời gian: O(n^2) đắt hơn O(n log n)...
- effects: danh sách thao tác (op, *args) mà rule engine thực thi tuần tự.
- unlock: điều kiện mở khoá ("start" | "level:N" | "puzzle:ID"), chỉ cần thoả một điều kiện.
"""

CATEGORY_LABEL = {
    "ds": "Cấu trúc dữ liệu",
    "search": "Tìm kiếm",
    "sort": "Sắp xếp",
    "graph": "Đồ thị",
    "paradigm": "Chiến lược",
}

CARDS = {
    # ------------------------------------------------------------ Starter
    "linear_search": {
        "name": "Tìm kiếm tuyến tính", "cost": 1, "cat": "search", "complexity": "O(n)",
        "text": "Gây 2 sát thương. Không cần dữ liệu đã sắp xếp.",
        "lesson": "Duyệt lần lượt từng phần tử: đơn giản, luôn đúng nhưng chậm với dữ liệu lớn.",
        "effects": [("dmg", 2)], "unlock": ["start"],
    },
    "bubble_sort": {
        "name": "Bubble Sort", "cost": 2, "cat": "sort", "complexity": "O(n²)",
        "text": "Sắp xếp dữ liệu (2 lượt). Nhận 1 giáp.",
        "lesson": "Đổi chỗ các cặp kề nhau: ổn định nhưng O(n²) nên tốn chi phí mà hiệu quả thấp.",
        "effects": [("sort", 2), ("block", 1)], "unlock": ["start"],
    },
    "stack": {
        "name": "Ngăn xếp (Stack)", "cost": 1, "cat": "ds", "complexity": "push/pop O(1)",
        "text": "Nhận 4 giáp.",
        "lesson": "LIFO – vào sau ra trước. Dùng cho kiểm tra ngoặc, undo, lời gọi hàm.",
        "effects": [("block", 4)], "unlock": ["start"],
    },
    "queue": {
        "name": "Hàng đợi (Queue)", "cost": 2, "cat": "ds", "complexity": "enqueue/dequeue O(1)",
        "text": "Gây 1 sát thương. Xếp hàng 2 + 2 sát thương: mỗi đầu lượt của bạn lấy ra 1 phần tử (FIFO).",
        "lesson": "FIFO – vào trước ra trước. Dùng cho xử lý theo thứ tự đến, BFS, lập lịch vòng tròn.",
        "effects": [("dmg", 1), ("schedule", [2, 2])], "unlock": ["start"],
    },
    "greedy": {
        "name": "Tham lam (Greedy)", "cost": 1, "cat": "paradigm", "complexity": "thường O(n log n)",
        "text": "Gây 3 sát thương.",
        "lesson": "Chọn phương án tốt nhất ở từng bước. Nhanh, nhưng chỉ đúng khi bài toán có tính chất lựa chọn tham lam.",
        "effects": [("dmg", 3)], "unlock": ["start"],
    },
    "bfs": {
        "name": "BFS", "cost": 2, "cat": "graph", "complexity": "O(V + E)",
        "text": "Gây 3 sát thương.",
        "lesson": "Duyệt theo chiều rộng bằng hàng đợi: tìm đường ngắn nhất trên đồ thị KHÔNG trọng số.",
        "effects": [("dmg", 3)], "unlock": ["start"],
    },
    "dfs": {
        "name": "DFS", "cost": 2, "cat": "graph", "complexity": "O(V + E)",
        "text": "Gây 2 sát thương. Rút 1 thẻ.",
        "lesson": "Duyệt theo chiều sâu (ngăn xếp/đệ quy): phát hiện chu trình, sắp xếp topo, duyệt mọi đỉnh.",
        "effects": [("dmg", 2), ("draw", 1)], "unlock": ["start"],
    },
    "hash_table": {
        "name": "Bảng băm (Hash Table)", "cost": 2, "cat": "ds", "complexity": "tra cứu O(1) TB",
        "text": "Tra cứu O(1): lấy từ bộ bài 1 thẻ TỐI ƯU cho bài toán hiện tại lên tay. Nếu không có, rút 1 thẻ.",
        "lesson": "Ánh xạ khoá → giá trị qua hàm băm: đếm tần suất, tra cứu nhanh, khử trùng lặp.",
        "effects": [("tutor",)], "unlock": ["start"],
    },
    # ------------------------------------------------------------ Mở khoá
    "binary_search": {
        "name": "Tìm kiếm nhị phân", "cost": 1, "cat": "search", "complexity": "O(log n)",
        "text": "CẦN dữ liệu đã sắp xếp: gây 5 sát thương. Nếu chưa sắp xếp: thất bại.",
        "lesson": "Chia đôi khoảng tìm kiếm mỗi bước. Điều kiện bắt buộc: dữ liệu đã sắp xếp.",
        "effects": [("need_sorted", [("dmg", 5)], [])], "unlock": ["puzzle:p1", "level:3"],
    },
    "quick_sort": {
        "name": "Quick Sort", "cost": 2, "cat": "sort", "complexity": "O(n log n) TB",
        "text": "Sắp xếp dữ liệu (2 lượt). Gây 2 sát thương.",
        "lesson": "Chia để trị quanh phần tử chốt: nhanh trung bình nhưng KHÔNG ổn định.",
        "effects": [("sort", 2), ("dmg", 2)], "unlock": ["puzzle:p1", "level:2"],
    },
    "merge_sort": {
        "name": "Merge Sort", "cost": 3, "cat": "sort", "complexity": "O(n log n)",
        "text": "Sắp xếp dữ liệu (2 lượt). Gây 2 sát thương, nhận 3 giáp.",
        "lesson": "Chia để trị rồi trộn: luôn O(n log n) và ỔN ĐỊNH (giữ thứ tự phần tử bằng nhau).",
        "effects": [("sort", 2), ("dmg", 2), ("block", 3)], "unlock": ["level:3"],
    },
    "dijkstra": {
        "name": "Dijkstra", "cost": 4, "cat": "graph", "complexity": "O((V+E) log V)",
        "text": "Gây 6 sát thương.",
        "lesson": "Đường đi ngắn nhất từ một nguồn với trọng số KHÔNG ÂM, dùng hàng đợi ưu tiên.",
        "effects": [("dmg", 6)], "unlock": ["level:2"],
    },
    "bellman_ford": {
        "name": "Bellman-Ford", "cost": 5, "cat": "graph", "complexity": "O(V·E)",
        "text": "Gây 6 sát thương, hồi 2 máu.",
        "lesson": "Đường đi ngắn nhất cho phép cạnh ÂM, phát hiện chu trình âm. Chậm hơn Dijkstra.",
        "effects": [("dmg", 6), ("heal", 2)], "unlock": ["puzzle:p3", "level:5"],
    },
    "dp": {
        "name": "Quy hoạch động (DP)", "cost": 3, "cat": "paradigm", "complexity": "O(số trạng thái)",
        "text": "Gây 2 sát thương + 1 cho mỗi loại thẻ khác nhau bạn đã chơi trong trận (tối đa +6).",
        "lesson": "Lưu kết quả bài toán con (memoization) để tái sử dụng: Balo 0/1, Fibonacci, LCS.",
        "effects": [("memodmg", 2, 6)], "unlock": ["puzzle:p2", "level:4"],
    },
    "heap": {
        "name": "Heap (Hàng đợi ưu tiên)", "cost": 2, "cat": "ds", "complexity": "lấy max O(log n)",
        "text": "Gây 1 + (chi phí lớn nhất trong các thẻ trên tay) sát thương.",
        "lesson": "Luôn lấy được phần tử ưu tiên cao nhất: Top-K, lập lịch theo độ ưu tiên, Dijkstra.",
        "effects": [("heapdmg", 1)], "unlock": ["puzzle:p5", "level:4"],
    },
    "recursion": {
        "name": "Đệ quy", "cost": -1, "cat": "paradigm", "complexity": "độ sâu X",
        "text": "X = toàn bộ năng lượng. Gây 2×X sát thương. Nếu X ≥ 6: TRÀN NGĂN XẾP, bạn nhận 4 sát thương.",
        "lesson": "Hàm gọi lại chính nó. Cần điểm dừng; quá sâu sẽ tràn ngăn xếp; đệ quy thuần có thể lặp lại bài toán con.",
        "effects": [("recursion",)], "unlock": ["puzzle:p4", "level:3"],
    },
    "undo": {
        "name": "Pop / Hoàn tác", "cost": 1, "cat": "ds", "complexity": "pop O(1)",
        "text": "Lấy thẻ bạn chơi GẦN NHẤT (LIFO) từ chồng bài đã dùng trở về tay. Nhận 1 giáp.",
        "lesson": "Thao tác pop của Stack: chức năng Undo luôn hoàn tác thao tác mới nhất trước.",
        "effects": [("undo",), ("block", 1)], "unlock": ["puzzle:p6", "level:2"],
    },
    "union_find": {
        "name": "Union-Find (DSU)", "cost": 2, "cat": "ds", "complexity": "≈O(α(n))",
        "text": "Hồi 3 máu, nhận 2 giáp.",
        "lesson": "Gộp tập và kiểm tra cùng tập gần O(1): thành phần liên thông động, thuật toán Kruskal.",
        "effects": [("heal", 3), ("block", 2)], "unlock": ["level:3"],
    },
    "shuffle": {
        "name": "Xáo trộn Fisher-Yates", "cost": 1, "cat": "sort", "complexity": "O(n)",
        "text": "Gây 2 sát thương. Dữ liệu của đối thủ trở thành CHƯA sắp xếp.",
        "lesson": "Hoán vị ngẫu nhiên đều trong O(n): phá vỡ điều kiện 'đã sắp xếp' của thuật toán khác.",
        "effects": [("dmg", 2), ("unsort_opp",)], "unlock": ["level:4"],
    },
    "two_pointers": {
        "name": "Hai con trỏ", "cost": 1, "cat": "search", "complexity": "O(n)",
        "text": "Nếu dữ liệu đã sắp xếp: gây 3 sát thương và rút 1 thẻ. Nếu chưa: gây 1 sát thương.",
        "lesson": "Hai chỉ số tiến về nhau trên mảng ĐÃ SẮP XẾP: tìm cặp có tổng K, gộp hai dãy.",
        "effects": [("need_sorted", [("dmg", 3), ("draw", 1)], [("dmg", 1)])], "unlock": ["level:5"],
    },
    "backtracking": {
        "name": "Quay lui (Backtracking)", "cost": 4, "cat": "paradigm", "complexity": "hàm mũ (có cắt nhánh)",
        "text": "Gây 4 sát thương. Rút 1 thẻ.",
        "lesson": "Thử từng lựa chọn, gặp ngõ cụt thì quay lại: N quân hậu, Sudoku, sinh hoán vị.",
        "effects": [("dmg", 4), ("draw", 1)], "unlock": ["level:6"],
    },
    "trie": {
        "name": "Cây tiền tố (Trie)", "cost": 2, "cat": "ds", "complexity": "O(độ dài từ)",
        "text": "Rút 2 thẻ.",
        "lesson": "Lưu chuỗi theo từng ký tự: gợi ý từ khoá theo tiền tố, kiểm tra chính tả.",
        "effects": [("draw", 2)], "unlock": ["level:5"],
    },
    "topo_sort": {
        "name": "Sắp xếp Topo", "cost": 3, "cat": "graph", "complexity": "O(V + E)",
        "text": "Gây 3 sát thương, nhận 2 giáp.",
        "lesson": "Thứ tự tuyến tính của đồ thị có hướng không chu trình (DAG): xếp môn tiên quyết, build phụ thuộc.",
        "effects": [("dmg", 3), ("block", 2)], "unlock": ["level:6"],
    },
    "kruskal": {
        "name": "Kruskal (Cây khung nhỏ nhất)", "cost": 3, "cat": "graph", "complexity": "O(E log E)",
        "text": "Gây 3 sát thương, hồi 2 máu.",
        "lesson": "Sắp cạnh tăng dần, thêm cạnh không tạo chu trình (dùng DSU): nối mạng chi phí nhỏ nhất.",
        "effects": [("dmg", 3), ("heal", 2)], "unlock": ["level:7"],
    },
}

DECK_SIZE = 12
MAX_COPIES = 2

STARTER_DECK = [
    "linear_search", "linear_search", "stack", "stack", "queue", "queue",
    "greedy", "greedy", "bfs", "dfs", "hash_table", "bubble_sort",
]


def card_cost_label(card_id):
    c = CARDS[card_id]["cost"]
    return "X" if c < 0 else str(c)


def validate_deck(deck, unlocked=None):
    """Trả về (ok, lý do)."""
    if not isinstance(deck, list) or len(deck) != DECK_SIZE:
        return False, f"Bộ bài phải có đúng {DECK_SIZE} thẻ"
    counts = {}
    for cid in deck:
        if cid not in CARDS:
            return False, f"Thẻ không tồn tại: {cid}"
        if unlocked is not None and cid not in unlocked:
            return False, f"Chưa mở khoá thẻ: {CARDS[cid]['name']}"
        counts[cid] = counts.get(cid, 0) + 1
        if counts[cid] > MAX_COPIES:
            return False, f"Tối đa {MAX_COPIES} bản cho mỗi thẻ ({CARDS[cid]['name']})"
    return True, "OK"


def unlocked_cards(level, puzzles_done):
    res = []
    for cid, c in CARDS.items():
        for cond in c["unlock"]:
            if cond == "start":
                ok = True
            elif cond.startswith("level:"):
                ok = level >= int(cond.split(":")[1])
            elif cond.startswith("puzzle:"):
                ok = cond.split(":")[1] in puzzles_done
            else:
                ok = False
            if ok:
                res.append(cid)
                break
    return res
