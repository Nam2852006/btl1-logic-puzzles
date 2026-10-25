# Pipes: ghi chú của TV2

Gửi TV1 (engine), TV4 (GUI), TV5 (báo cáo). Code nằm ở `puzzles/pipes.py`, input ở `inputs/pipes/`.

## 1. Cách dùng nhanh

Chạy từ thư mục gốc repo:

```bash
python main.py --puzzle pipes --algo dfs --input inputs/pipes/05.txt
python main.py --puzzle pipes --algo hc  --input inputs/pipes/03.txt --restarts 500 --sideways 50 --trace
python -m unittest tests.test_pipes -v
```

Input: `inputs/pipes/01.txt` … `05.txt` (4×4, 5×5, 7×7, 10×10, 15×15). Lời giải đúng nằm ở `inputs/pipes/solutions/`, tách ra thư mục con để benchmark (đọc `inputs/pipes/*.txt`) không chạy nhầm file lời giải như input.

| Hàm | Dùng cho | Ghi chú |
|---|---|---|
| `load_problem(path)` | registry | Hàm cấp module theo `core/registry.py` |
| `initial_state()` | DFS | `()`: chưa gán ô nào |
| `actions(s)` | DFS | Các góc xoay (mask) của ô thứ `len(s)`, đi theo hàng → cột |
| `result(s, a)` | DFS | `s + (a,)`, tuple mới |
| `is_valid(s)` | DFS | Gọi **sau khi sinh nút con**; chỉ kiểm tra ô vừa gán |
| `goal_test(s)` | cả hai | Đủ ô, khớp hết, liên thông, không vòng |
| `h(s)` | cả hai | Nhận cả trạng thái dở dang (ô chưa gán coi như trống) |
| `random_state(rng)` | Hill Climbing | Dùng `rng` do `hill_climbing` truyền vào, nên cùng seed thì cùng kết quả |
| `neighbors(s)` | Hill Climbing | Xoay 1 ô, hoặc xoay 2 ô kề nhau quanh một đầu ống hở |
| `start_state()` | GUI | Màn chơi đúng như trên web (góc xoay ban đầu) |
| `encode(s)` | GUI, trace | Lưới `rows × cols` các chuỗi 1 ký tự: `"0"`..`"F"` = mask hex, `"."` = ô chưa gán |
| `size_label()` | benchmark | Ví dụ `"15x15"` |

Mask một ô: Trên = 1, Phải = 2, Dưới = 4, Trái = 8. TV4 đổi ký tự trong trace về số bằng `int(c, 16)`, rồi vẽ ống theo từng bit.

## 2. Gửi TV1

1. **Benchmark Pipes phải chạy với `--restarts 500 --sideways 50`.** Với mặc định (20 restart, không đi ngang), Hill Climbing chỉ giải được 1/5 input (4×4), không đạt yêu cầu 3/5. Với 500/50 thì giải được 4/5 (15×15 timeout). Tents không dùng Hill Climbing nên truyền hai tham số này cho cả lệnh cũng không ảnh hưởng: `python -m core.benchmark --restarts 500 --sideways 50`.
2. Nếu muốn có bảng so sánh "Hill Climbing thuần và có đi ngang" cho báo cáo, chạy thêm một lần riêng: `python -m core.benchmark --puzzles pipes --algos hc --restarts 500 --sideways 0 --out results/benchmark_pipes_hc_pure.csv`.
3. (Tùy chọn) Với Pipes, không gian trạng thái của DFS là cây (gán lần lượt từng ô, không trạng thái nào lặp lại), nên `dfs(..., check_visited=False)` vẫn đúng mà giảm bộ nhớ đỉnh trên 15×15 từ khoảng 800 KB xuống khoảng 330 KB. Hiện registry/benchmark chưa có cách truyền tham số này theo từng bài; để mặc định cũng không sai.
4. `tools/tv2_dev_search.py` đã lỗi thời, **không merge vào repo**.

## 3. Thiết kế (nội dung cho phiếu bàn giao)

**DFS.** Trạng thái là tuple các mask đã chọn cho k ô đầu (theo hàng → cột). Hành động là chọn góc xoay cho ô kế tiếp. `is_valid` loại ô vừa gán nếu:
- (a) có lỗ chĩa ra biên;
- (b) không khớp với ô trên hoặc ô trái;
- (c) tạo vòng: ô nối cả lên trên lẫn sang trái, mà hai ô đó đã cùng một cụm;
- (d) tạo một cụm kín hết lỗ trong khi còn ô chưa gán.

Ràng buộc (b) gần như cố định góc xoay của mỗi ô, nên cây tìm kiếm rất hẹp. Đây là lý do DFS giải 15×15 chỉ trong vài phần trăm giây.

**Hill Climbing.**
- Trạng thái đầy đủ (mọi ô có góc xoay). Miền giá trị bỏ sẵn các góc chĩa ra biên.
- Láng giềng:
  - xoay 1 ô;
  - xoay đồng thời 2 ô kề nhau quanh một đầu ống đang hở. Đây là cách thoát *ridge* trong slide: hai bước liền nhau mới làm h giảm.
- Khởi tạo `greedy`: đi theo hàng → cột, mỗi ô chọn ngẫu nhiên trong các góc khớp với ô trên/trái, không có thì chọn ngẫu nhiên. Ứng với câu "getting it started right in the right general neighborhood" trong slide.

**Heuristic.**
- `h1` (local heuristic) = số đầu ống hở (chĩa ra biên hoặc chĩa vào ô không có lỗ quay lại).
- `h2` (global heuristic) = `h1 + (số cụm − 1) + số vòng`, trong đó số vòng = số cạnh khớp − số ô + số cụm.
- `h2 = 0` ⇔ lời giải. `h1 = 0` chưa chắc là lời giải (có thể tách cụm hoặc có vòng), nên engine phải luôn kiểm tra `goal_test`, không dừng chỉ vì h = 0. Nếu kẹt ở trạng thái h1 = 0 mà chưa phải đích, Hill Climbing coi đó là cực tiểu địa phương và restart.
- Admissible? Không áp dụng cho Hill Climbing (không có g, không cần tối ưu đường đi). Nếu coi mỗi lần xoay là một bước, h1 **không admissible**: một lần xoay sửa được tới 8 đầu hở, nên h1 có thể lớn hơn số bước thật. `h1/8` thì admissible nhưng không có ích cho Hill Climbing.

**Ví dụ tính tay** (lưới 2×2, trạng thái `6 C / 2 8`, tức hàng trên R+D, L+D, hàng dưới R, L):
- Ô (0,0) mở Phải, Dưới: Phải khớp với (0,1) có Trái; Dưới chĩa vào (1,0) không có lỗ Trên, nên **1 đầu hở**.
- Ô (0,1) mở Trái, Dưới: Dưới chĩa vào (1,1) không có lỗ Trên, nên **1 đầu hở**.
- Ô (1,0) và (1,1) nối nhau.
- h1 = 2. Có 2 cụm {(0,0),(0,1)} và {(1,0),(1,1)}, 0 vòng, nên h2 = 2 + 1 + 0 = 3.

## 4. Kết quả chạy thử (engine tạm của TV2, máy cloud, giới hạn 300 giây, 500 restart)

Đã chạy lại bằng `core.benchmark` của TV1 (`--restarts 500 --sideways 50`): DFS giải 5/5 (15×15 mất 0,008 s), Hill Climbing giải 4/5 (10×10 mất 4 s, 15×15 timeout). Bảng dưới là số liệu thử nghiệm để chọn thiết kế; số liệu chính thức cho báo cáo lấy từ `results/benchmark.csv` do TV1 chạy.


| Input | Giải thuật | Kết quả | Thời gian (s) | Bộ nhớ đỉnh (KB) | Nút mở rộng | Ghi chú |
|---|---|---|---:|---:|---:|---|
| 01 (4×4) | DFS | ok | 0.001 | 5.0 | 26 | max_frontier 4 |
| 01 | HC-h1 | ok | 0.003 | 17.8 | 6 | 4 restart |
| 01 | HC-h1 + đi ngang | ok | 0.002 | 6.6 | 4 | 1 restart |
| 01 | HC-h2 | ok | 0.009 | 7.8 | 6 | 4 restart |
| 01 | HC-h2 + đi ngang | ok | 0.005 | 6.6 | 4 | 1 restart |
| 02 (5×5) | DFS | ok | 0.001 | 7.0 | 30 | max_frontier 3 |
| 02 | HC-h1 | ok | 0.067 | 83.0 | 30 | 23 restart |
| 02 | HC-h1 + đi ngang | ok | 0.067 | 59.4 | 38 | 1 restart |
| 02 | HC-h2 | ok | 0.224 | 82.7 | 36 | 23 restart |
| 02 | HC-h2 + đi ngang | ok | 0.067 | 56.7 | 13 | 1 restart |
| 03 (7×7) | DFS | ok | 0.001 | 5.7 | 65 | max_frontier 7 |
| 03 | HC-h1 | ok | 9.548 | 365.6 | 819 | 225 restart |
| 03 | HC-h1 + đi ngang | ok | 0.094 | 280.8 | 11 | 1 restart |
| 03 | HC-h2 | ok | 28.145 | 363.3 | 865 | 225 restart |
| 03 | HC-h2 + đi ngang | ok | 0.302 | 280.9 | 11 | 1 restart |
| 04 (10×10) | DFS | ok | 0.004 | 18.1 | 173 | max_frontier 15 |
| 04 | HC-h1 | thất bại | 106.180 | 1554.0 | 2090 | hết 500 restart, h tốt nhất 6 |
| 04 | HC-h1 + đi ngang | ok | 45.135 | 1340.1 | 1201 | 13 restart |
| 04 | HC-h2 | timeout | 300.012 | 1487.9 | 2016 | 375 restart, h tốt nhất 9 |
| 04 | HC-h2 + đi ngang | ok | 31.701 | 1128.2 | 272 | 3 restart |
| 05 (15×15) | DFS | ok | 0.025 | 49.0 | 822 | max_frontier 46 |
| 05 | HC-h1 | timeout | 300.2 | 7701.2 | 1013 | 87 restart, h tốt nhất 20 |
| 05 | HC-h1 + đi ngang | timeout | 300.0 | 7028.2 | 1558 | 8 restart, h tốt nhất 4 |
| 05 | HC-h2 | timeout | 300.5 | 7605.8 | 341 | 24 restart, h tốt nhất 43 |
| 05 | HC-h2 + đi ngang | timeout | 300.3 | 6879.0 | 522 | 2 restart, h tốt nhất 5 |

Thời gian đo bằng `time.perf_counter`, bộ nhớ bằng `tracemalloc` (bật `tracemalloc` làm code chạy chậm hơn khoảng 2–3 lần). Hill Climbing dùng seed 0, khởi tạo greedy, láng giềng 1–2 ô; "đi ngang" là tối đa 50 bước liên tiếp.

**Nhận xét nhanh:**
- DFS giải cả 5 input dưới 0,03 giây và tốn rất ít bộ nhớ, nhờ `is_valid` cắt nhánh mạnh (ràng buộc khớp với ô trên/trái gần như cố định góc xoay).
- Hill Climbing bản cơ bản giải được 3/5 (4×4, 5×5, 7×7) nếu cho đủ restart. Có đi ngang thì giải được 4/5, và mỗi input chỉ cần 1–13 restart, chứng tỏ vấn đề chính là **vùng bằng phẳng (plateau)**. 15×15 vẫn timeout nhưng đã xuống còn 4–5 đầu hở.
- h2 và h1 ngang nhau về khả năng giải, nhưng h2 chậm hơn mỗi bước (phải chạy union-find). Có đi ngang thì h2 cần ít restart hơn.
- Bộ nhớ của Hill Climbing lớn hơn DFS vì mỗi bước phải sinh toàn bộ láng giềng (hàng nghìn trạng thái đầy đủ với 15×15).

## 5. Khó khăn và cách xử lý

- **Input chỉ có dạng ảnh chụp web:** viết script đọc ảnh tự động, rồi kiểm tra chéo (lời giải phải là một cây và khớp hết lỗ; mỗi ô input phải là phép xoay của ô lời giải).
- **Hill Climbing bản cơ bản** (xoay 1 ô, khởi tạo ngẫu nhiên, 20 restart) chỉ giải được 4×4. Nguyên nhân là cực tiểu địa phương và vùng bằng phẳng: nhiều trạng thái chỉ còn 2–4 đầu hở mà không lần xoay đơn nào làm h giảm. Đã xử lý bằng miền không chĩa ra biên, láng giềng 2 ô, khởi tạo greedy, tăng số restart và đi ngang.
- **h2 không giải được nhiều hơn h1 mà mỗi bước lại chậm hơn:** số cụm chỉ giảm khi nối đúng hai cụm, mà việc đó thường cần nhiều bước, nên khi không có đi ngang thì h2 hay kẹt hơn. Tính h2 cũng tốn thời gian hơn (phải chạy union-find). Mặc định giữ h1, h2 dùng để so sánh trong báo cáo.
