"""Thẻ Bài toán (Challenge) xuất hiện giữa sân, dùng chung cho hai người chơi.

Người chơi đầu tiên dùng thẻ TỐI ƯU sẽ giải được bài toán và nhận thưởng.
- optimal   : lựa chọn đúng và hiệu quả nhất → giải bài toán, nhận đủ thưởng, +2 Insight.
- acceptable: đúng nhưng chưa tối ưu (chậm/thừa) → giải bài toán, nhận nửa thưởng, +1 Insight.
- traps     : lựa chọn "trông có vẻ đúng" nhưng SAI → hiệu ứng của thẻ bị giảm một nửa.
Mỗi mục đều kèm giải thích để hiển thị sau trận (post-match explanation).
"""

CHALLENGES = {
    "brackets": {
        "title": "Kiểm tra dấu ngoặc hợp lệ",
        "desc": "Chuỗi \"{[()()]}\" có hợp lệ không? Ngoặc đóng phải khớp ngoặc mở GẦN NHẤT.",
        "optimal": {"stack": "Stack (LIFO): ngoặc mở gần nhất nằm ở đỉnh ngăn xếp, khớp và pop trong O(1)."},
        "acceptable": {"undo": "Pop/Hoàn tác chính là thao tác pop của Stack – đúng ý tưởng LIFO."},
        "traps": {"queue": "Queue là FIFO: lấy ra ngoặc mở SỚM NHẤT nên sai với ngoặc lồng nhau như \"([])\"."},
        "reward": [("dmg", 3)],
    },
    "printer": {
        "title": "Xử lý lệnh in theo thứ tự đến",
        "desc": "Nhiều người gửi lệnh in tới một máy in chung, ai gửi trước được in trước.",
        "optimal": {"queue": "Queue (FIFO): lệnh đến trước được phục vụ trước, enqueue/dequeue O(1)."},
        "acceptable": {},
        "traps": {"stack": "Stack là LIFO: lệnh gửi sau cùng lại được in trước – không công bằng.",
                  "heap": "Heap phục vụ theo độ ưu tiên, không theo thứ tự đến."},
        "reward": [("dmg", 2), ("draw", 1)],
    },
    "maze": {
        "title": "Đường ngắn nhất trong mê cung",
        "desc": "Mê cung dạng lưới, mỗi bước đi có chi phí như nhau (đồ thị không trọng số).",
        "optimal": {"bfs": "BFS duyệt theo từng lớp khoảng cách nên lần đầu chạm đích là đường ngắn nhất, O(V+E)."},
        "acceptable": {"dijkstra": "Dijkstra cũng đúng nhưng thừa: hàng đợi ưu tiên tốn thêm log V khi mọi cạnh bằng nhau.",
                       "bellman_ford": "Bellman-Ford đúng nhưng O(V·E), quá chậm cho đồ thị không trọng số."},
        "traps": {"dfs": "DFS đi sâu theo một nhánh, đường tìm được KHÔNG đảm bảo ngắn nhất.",
                  "greedy": "Đi tham lam về phía đích có thể kẹt ngõ cụt, không đảm bảo ngắn nhất."},
        "reward": [("dmg", 3)],
    },
    "gps": {
        "title": "Tìm đường GPS (trọng số dương)",
        "desc": "Bản đồ đường phố, mỗi đoạn đường có độ dài (km) khác nhau, đều dương.",
        "optimal": {"dijkstra": "Dijkstra tối ưu cho trọng số không âm: O((V+E) log V) với heap."},
        "acceptable": {"bellman_ford": "Bellman-Ford cho kết quả đúng nhưng O(V·E), chậm hơn nhiều."},
        "traps": {"bfs": "BFS bỏ qua độ dài cạnh: ít đoạn đường nhất ≠ quãng đường ngắn nhất.",
                  "greedy": "Luôn chọn đoạn ngắn nhất kế tiếp không đảm bảo tổng quãng đường nhỏ nhất."},
        "reward": [("dmg", 4)],
    },
    "arbitrage": {
        "title": "Đồ thị có cạnh âm (chênh lệch tỷ giá)",
        "desc": "Đồ thị tỷ giá có cạnh trọng số ÂM; cần đường đi ngắn nhất và phát hiện chu trình âm.",
        "optimal": {"bellman_ford": "Bellman-Ford xử lý được cạnh âm và phát hiện chu trình âm sau V-1 vòng nới lỏng."},
        "acceptable": {},
        "traps": {"dijkstra": "Dijkstra giả định cạnh không âm: một đỉnh đã 'chốt' có thể bị cạnh âm làm sai.",
                  "bfs": "BFS không xét trọng số nên sai hoàn toàn với cạnh âm."},
        "reward": [("dmg", 4), ("heal", 2)],
    },
    "phonebook": {
        "title": "Tra cứu trong danh bạ đã sắp xếp",
        "desc": "Danh bạ 1 triệu tên đã sắp xếp theo ABC. Tìm số của \"Nguyễn Văn A\".",
        "optimal": {"binary_search": "Mảng đã sắp xếp → Tìm kiếm nhị phân O(log n): ~20 bước cho 1 triệu phần tử."},
        "acceptable": {"linear_search": "Tìm tuyến tính vẫn đúng nhưng O(n): tới 1 triệu bước.",
                       "hash_table": "Bảng băm tra cứu O(1) nhưng phải xây bảng O(n) trước – thừa khi dữ liệu đã sắp xếp."},
        "traps": {},
        "reward": [("dmg", 3)],
    },
    "coins": {
        "title": "Đổi tiền mệnh giá chuẩn",
        "desc": "Trả lại 87.000đ bằng ít tờ nhất với mệnh giá 1k, 2k, 5k, 10k, 20k, 50k.",
        "optimal": {"greedy": "Hệ mệnh giá chuẩn có tính chất tham lam: luôn lấy tờ lớn nhất ≤ số còn lại là tối ưu."},
        "acceptable": {"dp": "DP cũng ra đáp án đúng nhưng O(số tiền × số mệnh giá) – thừa với hệ tiền chuẩn."},
        "traps": {},
        "reward": [("dmg", 2), ("draw", 1)],
    },
    "knapsack": {
        "title": "Bài toán Balo 0/1",
        "desc": "Balo chứa 10kg, chọn đồ vật (không chia nhỏ được) để tổng giá trị lớn nhất.",
        "optimal": {"dp": "DP trên (vật thứ i, sức chứa w) cho lời giải tối ưu trong O(n·W)."},
        "acceptable": {"backtracking": "Quay lui thử mọi tập con – đúng nhưng O(2^n)."},
        "traps": {"greedy": "Tham lam theo tỉ lệ giá trị/khối lượng chỉ đúng với balo PHÂN SỐ, sai với balo 0/1."},
        "reward": [("dmg", 4)],
    },
    "fibonacci": {
        "title": "Tính Fibonacci(50)",
        "desc": "F(n) = F(n-1) + F(n-2). Tính F(50) nhanh.",
        "optimal": {"dp": "DP/memoization tính mỗi F(i) đúng một lần: O(n)."},
        "acceptable": {},
        "traps": {"recursion": "Đệ quy thuần gọi lại cùng bài toán con rất nhiều lần: O(2^n) ≈ 10^15 phép gọi."},
        "reward": [("dmg", 3), ("heal", 1)],
    },
    "word_freq": {
        "title": "Đếm tần suất từ trong văn bản",
        "desc": "Đếm mỗi từ xuất hiện bao nhiêu lần trong 10 triệu từ.",
        "optimal": {"hash_table": "Bảng băm: mỗi từ cập nhật bộ đếm O(1) trung bình → tổng O(n)."},
        "acceptable": {"trie": "Trie đếm được theo tiền tố, đúng nhưng tốn bộ nhớ hơn bảng băm."},
        "traps": {"linear_search": "Mỗi từ lại tìm tuyến tính trong danh sách đã gặp → O(n²)."},
        "reward": [("draw", 1), ("dmg", 2)],
    },
    "topk": {
        "title": "Cấp cứu theo mức độ ưu tiên",
        "desc": "Bệnh nhân đến liên tục, luôn phải chọn người nguy kịch nhất để khám trước.",
        "optimal": {"heap": "Heap lấy phần tử ưu tiên cao nhất O(log n), chèn O(log n) – đúng cho dữ liệu đến liên tục."},
        "acceptable": {"merge_sort": "Sắp xếp lại toàn bộ mỗi lần có người mới: đúng nhưng O(n log n) mỗi lần.",
                       "quick_sort": "Sắp xếp lại toàn bộ mỗi lần có người mới: đúng nhưng O(n log n) mỗi lần."},
        "traps": {"queue": "Queue phục vụ theo thứ tự đến (FIFO), bỏ qua mức độ nguy kịch."},
        "reward": [("dmg", 3)],
    },
    "stable_sort": {
        "title": "Sắp xếp bảng điểm ổn định",
        "desc": "Sắp theo điểm, sinh viên bằng điểm phải giữ nguyên thứ tự theo tên đã có.",
        "optimal": {"merge_sort": "Merge Sort ổn định và luôn O(n log n)."},
        "acceptable": {"bubble_sort": "Bubble Sort ổn định nhưng O(n²)."},
        "traps": {"quick_sort": "Quick Sort KHÔNG ổn định: hai bạn bằng điểm có thể bị đảo thứ tự."},
        "reward": [("dmg", 3), ("block", 2)],
    },
    "cycle": {
        "title": "Phát hiện chu trình phụ thuộc",
        "desc": "Các module import lẫn nhau. Có vòng lặp phụ thuộc không?",
        "optimal": {"dfs": "DFS tô màu trắng/xám/đen: gặp đỉnh 'xám' trên ngăn xếp đệ quy là có chu trình."},
        "acceptable": {"topo_sort": "Sắp xếp topo (Kahn) không xử lý hết đỉnh ⇔ có chu trình."},
        "traps": {"bfs": "BFS đơn thuần không nhận biết cạnh quay lui trên đồ thị có hướng."},
        "reward": [("dmg", 2), ("draw", 1)],
    },
    "components": {
        "title": "Nhóm bạn bè (kết nối động)",
        "desc": "Liên tục có lời mời kết bạn mới; hỏi nhanh: A và B có cùng nhóm không?",
        "optimal": {"union_find": "Union-Find: union và find gần O(1) với nén đường đi + gộp theo hạng."},
        "acceptable": {"bfs": "BFS mỗi truy vấn đúng nhưng O(V+E) cho mỗi lần hỏi.",
                       "dfs": "DFS mỗi truy vấn đúng nhưng O(V+E) cho mỗi lần hỏi."},
        "traps": {},
        "reward": [("heal", 3), ("dmg", 2)],
    },
    "autocomplete": {
        "title": "Gợi ý từ khoá theo tiền tố",
        "desc": "Người dùng gõ \"thu\" → gợi ý \"thuật toán\", \"thư viện\"...",
        "optimal": {"trie": "Trie đi theo tiền tố trong O(độ dài tiền tố) rồi liệt kê các nhánh con."},
        "acceptable": {"binary_search": "Tìm nhị phân trên danh sách từ đã sắp xếp cũng tìm được dải tiền tố."},
        "traps": {"hash_table": "Bảng băm chỉ tra cứu khớp TOÀN BỘ khoá, không hỗ trợ truy vấn tiền tố."},
        "reward": [("draw", 2)],
    },
    "nqueens": {
        "title": "Bài toán 8 quân hậu",
        "desc": "Đặt 8 quân hậu trên bàn cờ sao cho không quân nào ăn nhau.",
        "optimal": {"backtracking": "Quay lui: đặt từng hàng, xung đột thì lùi lại – cắt nhánh mạnh."},
        "acceptable": {},
        "traps": {"greedy": "Đặt tham lam ô 'an toàn' đầu tiên sẽ sớm bế tắc và không quay lại được."},
        "reward": [("dmg", 4)],
    },
    "course_order": {
        "title": "Xếp lịch học theo môn tiên quyết",
        "desc": "CTDL cần Lập trình cơ bản; Thuật toán cần CTDL... Xếp thứ tự học hợp lệ.",
        "optimal": {"topo_sort": "Sắp xếp topo trên DAG cho thứ tự thoả mọi ràng buộc tiên quyết, O(V+E)."},
        "acceptable": {"dfs": "Thứ tự hậu tố của DFS đảo ngược chính là một thứ tự topo."},
        "traps": {"quick_sort": "Sắp xếp so sánh thông thường không biểu diễn được quan hệ tiên quyết (thứ tự bộ phận)."},
        "reward": [("dmg", 3)],
    },
    "network": {
        "title": "Nối cáp mạng chi phí nhỏ nhất",
        "desc": "Nối tất cả toà nhà trong khuôn viên với tổng chiều dài cáp nhỏ nhất.",
        "optimal": {"kruskal": "Kruskal xây cây khung nhỏ nhất: sắp cạnh + Union-Find, O(E log E)."},
        "acceptable": {"union_find": "Union-Find là thành phần cốt lõi của Kruskal (tránh tạo chu trình)."},
        "traps": {"dijkstra": "Cây đường đi ngắn nhất từ một nguồn KHÁC cây khung có tổng trọng số nhỏ nhất."},
        "reward": [("dmg", 3), ("heal", 2)],
    },
    "pair_sum": {
        "title": "Tìm cặp có tổng bằng K",
        "desc": "Mảng ĐÃ SẮP XẾP, tìm hai phần tử có tổng đúng bằng K.",
        "optimal": {"two_pointers": "Hai con trỏ ở hai đầu tiến vào giữa: O(n), bộ nhớ O(1)."},
        "acceptable": {"hash_table": "Bảng băm O(n) nhưng tốn thêm O(n) bộ nhớ.",
                       "binary_search": "Với mỗi phần tử tìm nhị phân phần bù: O(n log n)."},
        "traps": {"linear_search": "Thử mọi cặp bằng hai vòng lặp: O(n²)."},
        "reward": [("dmg", 3)],
    },
    "undo_editor": {
        "title": "Chức năng Undo của trình soạn thảo",
        "desc": "Ctrl+Z phải hoàn tác thao tác vừa làm gần nhất trước.",
        "optimal": {"undo": "Stack lưu lịch sử thao tác: Undo = pop phần tử trên đỉnh (mới nhất)."},
        "acceptable": {"stack": "Stack là cấu trúc đúng cho lịch sử Undo."},
        "traps": {"queue": "Queue sẽ hoàn tác thao tác CŨ NHẤT trước – sai yêu cầu."},
        "reward": [("block", 3), ("draw", 1)],
    },
}


def rate(challenge_id, card_id):
    """Trả về (rating, explanation). rating ∈ optimal|acceptable|trap|neutral."""
    ch = CHALLENGES.get(challenge_id)
    if not ch:
        return "neutral", ""
    for key in ("optimal", "acceptable", "traps"):
        if card_id in ch[key]:
            return ("trap" if key == "traps" else key), ch[key][card_id]
    return "neutral", ""


def best_answer(challenge_id):
    ch = CHALLENGES[challenge_id]
    cid, why = next(iter(ch["optimal"].items()))
    return cid, why
