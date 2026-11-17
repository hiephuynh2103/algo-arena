"""Tutorial theo chủ đề: vài trang lý thuyết ngắn rồi dẫn vào một thử thách thực hành."""

TUTORIALS = [
    {
        "id": "t0", "title": "Cách chơi Algo Arena", "puzzle": None,
        "pages": [
            ("Mục tiêu", [
                "Đưa máu (HP) của đối thủ từ 30 về 0.",
                "Mỗi lượt bạn có năng lượng (tăng dần tới 8) để chơi thẻ.",
                "Mỗi thẻ là một cấu trúc dữ liệu hoặc thuật toán. Chi phí phản ánh độ phức tạp.",
            ]),
            ("Thẻ Bài toán ở giữa sân", [
                "Giữa sân luôn có một BÀI TOÁN dùng chung cho cả hai bên.",
                "Dùng thẻ TỐI ƯU cho bài toán → giải được, nhận thưởng và +2 Insight.",
                "Thẻ đúng nhưng CHƯA TỐI ƯU → giải được, nhận nửa thưởng, +1 Insight.",
                "Thẻ BẪY (trông đúng nhưng sai) → hiệu ứng của thẻ bị giảm một nửa.",
                "Bài toán hết hạn sau 3 vòng nếu không ai giải.",
            ]),
            ("Trạng thái đặc biệt", [
                "ĐÃ SẮP XẾP: do thẻ Sắp xếp tạo ra, kéo dài 2 lượt. Tìm nhị phân, Hai con trỏ cần trạng thái này.",
                "MEMO: các loại thẻ bạn đã chơi. DP mạnh hơn khi memo lớn.",
                "QUEUE: sát thương được xếp hàng, mỗi đầu lượt lấy ra 1 phần tử (FIFO).",
                "GIÁP: chặn sát thương, mất khi bắt đầu lượt mới của bạn.",
            ]),
            ("Sau trận", [
                "Màn hình kết quả giải thích từng quyết định: tối ưu, chưa tối ưu, bẫy, bỏ lỡ.",
                "Mọi trận được lưu để XEM REPLAY từng bước và học lại quyết định.",
                "Thắng trận và hoàn thành thử thách để lên cấp, mở khoá thẻ mới.",
            ]),
        ],
    },
    {
        "id": "t1", "title": "Stack & Queue", "puzzle": "p6",
        "pages": [
            ("Stack – LIFO", [
                "Vào sau ra trước. Thao tác push/pop ở đỉnh, O(1).",
                "Dùng khi cần 'quay lại điều gần nhất': kiểm tra ngoặc, Undo, ngăn xếp lời gọi hàm, DFS.",
            ]),
            ("Queue – FIFO", [
                "Vào trước ra trước. enqueue ở cuối, dequeue ở đầu, O(1).",
                "Dùng khi phục vụ theo thứ tự đến: máy in, hàng chờ request, BFS.",
            ]),
            ("Nhận biết bẫy", [
                "Kiểm tra ngoặc bằng Queue là SAI: ngoặc đóng phải khớp ngoặc mở GẦN NHẤT.",
                "Xử lý lệnh in bằng Stack là SAI: lệnh đến sau lại được in trước.",
                "→ Thực hành: thử thách 'Undo theo thứ tự LIFO'.",
            ]),
        ],
    },
    {
        "id": "t2", "title": "Sắp xếp & Tìm kiếm", "puzzle": "p1",
        "pages": [
            ("Độ phức tạp", [
                "Bubble Sort O(n²) – ổn định nhưng chậm.",
                "Quick Sort O(n log n) trung bình – nhanh nhưng KHÔNG ổn định.",
                "Merge Sort O(n log n) luôn luôn – ỔN ĐỊNH, tốn thêm bộ nhớ.",
            ]),
            ("Tìm kiếm", [
                "Tuyến tính O(n): không cần điều kiện gì.",
                "Nhị phân O(log n): BẮT BUỘC dữ liệu đã sắp xếp.",
                "Hai con trỏ O(n): trên mảng đã sắp xếp, ví dụ tìm cặp có tổng K.",
            ]),
            ("Khi nào sắp xếp trước?", [
                "Nếu cần tìm kiếm nhiều lần: sắp xếp 1 lần O(n log n) + mỗi lần tìm O(log n).",
                "Trong game: chơi thẻ Sắp xếp để có trạng thái ĐÃ SẮP XẾP rồi mới dùng Tìm nhị phân.",
                "→ Thực hành: 'Tiền điều kiện của tìm kiếm nhị phân'.",
            ]),
        ],
    },
    {
        "id": "t3", "title": "Đồ thị", "puzzle": "p3",
        "pages": [
            ("Duyệt đồ thị", [
                "BFS (hàng đợi): đường ngắn nhất trên đồ thị KHÔNG trọng số.",
                "DFS (ngăn xếp/đệ quy): phát hiện chu trình, sắp xếp topo, duyệt mọi đỉnh.",
            ]),
            ("Đường đi ngắn nhất có trọng số", [
                "Dijkstra: trọng số KHÔNG ÂM, O((V+E) log V).",
                "Bellman-Ford: cho phép cạnh ÂM, phát hiện chu trình âm, O(V·E).",
            ]),
            ("Cây khung nhỏ nhất", [
                "Kruskal: sắp cạnh tăng dần + Union-Find tránh chu trình.",
                "Đừng nhầm cây đường đi ngắn nhất (Dijkstra) với cây khung nhỏ nhất!",
                "→ Thực hành: 'Cạnh âm trên đồ thị tỷ giá'.",
            ]),
        ],
    },
    {
        "id": "t4", "title": "Tham lam vs Quy hoạch động", "puzzle": "p2",
        "pages": [
            ("Tham lam (Greedy)", [
                "Mỗi bước chọn phương án tốt nhất trước mắt, không quay lại.",
                "Đúng khi bài toán có 'tính chất lựa chọn tham lam': đổi tiền mệnh giá chuẩn, chọn hoạt động.",
            ]),
            ("Quy hoạch động (DP)", [
                "Chia thành bài toán con chồng lấp, LƯU kết quả để dùng lại (memoization).",
                "Đúng cho Balo 0/1, Fibonacci, dãy con chung dài nhất, đổi tiền mệnh giá bất kỳ.",
            ]),
            ("Bẫy kinh điển", [
                "Balo 0/1 giải bằng Greedy theo tỉ lệ giá trị/khối lượng → SAI.",
                "Fibonacci bằng đệ quy thuần → O(2^n). Dùng DP → O(n).",
                "→ Thực hành: 'Balo 0/1 – đừng tham lam!' và 'Điểm dừng của đệ quy'.",
            ]),
        ],
    },
    {
        "id": "t5", "title": "Heap & Đệ quy", "puzzle": "p5",
        "pages": [
            ("Heap", [
                "Cây nhị phân gần đầy, cha luôn ≥ con (max-heap).",
                "Lấy max O(1), xoá max/chèn O(log n): lập lịch ưu tiên, Top-K, Dijkstra.",
            ]),
            ("Đệ quy", [
                "Hàm gọi lại chính nó với bài toán nhỏ hơn và PHẢI có điểm dừng.",
                "Mỗi lời gọi chiếm một khung trên ngăn xếp – quá sâu sẽ Stack Overflow.",
                "→ Thực hành: 'Ai nguy kịch nhất?' và 'Điểm dừng của đệ quy'.",
            ]),
        ],
    },
]

TUTORIAL_BY_ID = {t["id"]: t for t in TUTORIALS}
