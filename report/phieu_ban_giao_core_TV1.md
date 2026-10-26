# Phiếu bàn giao kỹ thuật – Phần lõi (engine, benchmark, tích hợp) – TV1

Ngày 26/10/2026 · TV1 (trưởng nhóm)

Phiếu này mô tả phần dùng chung cho cả hai bài toán: interface, bốn giải thuật tìm kiếm, tracer cho GUI, benchmark và công cụ kiểm tra. Phần mô hình hóa riêng của từng bài nằm trong phiếu của TV2 (Pipes) và TV3 (Tents).

## 1. Phạm vi phần lõi

| File | Nội dung |
| --- | --- |
| `core/problem.py` | Interface `Problem` mà mọi bài toán phải cài, và `SearchResult` mà mọi giải thuật trả về |
| `core/search.py` | Bốn giải thuật tổng quát: DFS, BrFS, A\*, Hill Climbing |
| `core/tracer.py` | Ghi từng bước tìm kiếm ra file `.jsonl` để GUI phát lại |
| `core/benchmark.py` | Đo thời gian, bộ nhớ, số nút; xuất CSV và biểu đồ |
| `core/check.py` | Kiểm tra tự động code của một bài toán có đúng interface không |
| `core/registry.py` | Danh sách bài toán, cặp giải thuật và biến thể dùng trong benchmark |
| `main.py` | Chạy một cặp bài toán – giải thuật – input từ dòng lệnh |
| `examples/nqueens.py` | Bài đồ chơi N-Queens để kiểm thử giải thuật trước khi có Pipes và Tents |

## 2. Kiến trúc chung

Ý tưởng chính: **giải thuật không biết gì về luật chơi**. Mỗi bài toán cài cùng một interface; các giải thuật chỉ gọi hàm của interface đó. Nhờ vậy:

- Một bản cài đặt DFS, A\*, Hill Climbing dùng chung cho cả Pipes, Tents và N-Queens.
- Bốn người (engine, Pipes, Tents, GUI) code song song mà không sửa file của nhau.
- So sánh giữa các bài là công bằng: mọi bài chạy qua đúng cùng một đoạn code tìm kiếm và cùng một cách đo.

Luồng dữ liệu: `puzzles/*.py` cài interface → `core/search.py` gọi interface để tìm lời giải → `core/tracer.py` ghi từng bước → `gui/app.py` đọc file trace để phát lại; song song đó `core/benchmark.py` chạy mọi cặp và xuất `results/*.csv`. Sơ đồ kiến trúc có trong tài liệu phân công nhóm, mục 3.

## 3. Interface `Problem`

Các hàm theo đúng thành phần của không gian trạng thái trong slide chương 2:

| Hàm | Vai trò | Dùng bởi |
| --- | --- | --- |
| `initial_state()` | Trạng thái đầu | DFS, BrFS, A\* |
| `actions(s)` | Tập hành động áp dụng được tại s | DFS, BrFS, A\* |
| `result(s, a)` | Hàm chuyển trạng thái: sinh nút con | DFS, BrFS, A\* |
| `is_valid(s)` | Kiểm tra hợp lệ, gọi **sau khi** sinh nút con để loại nhánh sai | DFS, BrFS, A\* |
| `goal_test(s)` | Kiểm tra trạng thái đích | Cả bốn |
| `step_cost(s, a)` | Chi phí một bước, mặc định 1 | A\* |
| `h(s)` | Hàm heuristic (ký hiệu h\*(n) theo slide chương 3) | A\*, Hill Climbing |
| `random_state(rng)` | Trạng thái đầy đủ ngẫu nhiên, cho điểm xuất phát và random restart | Hill Climbing |
| `neighbors(s)` | Các trạng thái láng giềng | Hill Climbing |
| `encode(s)` | Chuyển trạng thái thành lưới để GUI vẽ | Tracer, GUI |

Ba quy ước bắt buộc với mọi bài toán:

1. Trạng thái là `tuple` (hashable), để lưu được vào tập `visited` / CLOSED.
2. `result()` trả về trạng thái **mới**, không sửa trạng thái cũ.
3. `encode()` trả về lưới (list các list) chuyển được sang JSON.

Mỗi giải thuật trả về `SearchResult` gồm: có tìm thấy lời giải không, lời giải, đường đi, **số nút mở rộng**, **số nút sinh ra**, **kích thước frontier lớn nhất**, và số lần restart (riêng Hill Climbing).

## 4. Cài đặt bốn giải thuật

### 4.1. DFS

- Frontier là **stack** (LIFO). Các nút con được đẩy vào theo thứ tự đảo ngược, để hành động đầu tiên trong `actions()` được duyệt trước.
- `is_valid()` được gọi ngay sau khi sinh mỗi nút con; nút con vi phạm ràng buộc bị loại, không vào stack (cắt nhánh sớm).
- Có tập **`visited`**: một trạng thái đã gặp thì không đưa vào stack lần nữa. Đây là DFS dạng *graph search*, chọn để tránh lặp vô hạn nếu không gian trạng thái có chu trình.
- Lưu con trỏ cha thay vì lưu cả đường đi trong mỗi nút, dựng lại đường đi khi tìm thấy đích.

**Hệ quả về bộ nhớ (cần giải thích trong báo cáo).** Tập `visited` lưu mọi trạng thái hợp lệ đã sinh ra, nên bộ nhớ DFS tăng theo **số nút đã sinh**, không theo độ sâu như DFS trong sách. Ví dụ Tents đề 10: stack lớn nhất chỉ có 71 nút, nhưng DFS đã sinh 754.968 nút, và bộ nhớ đỉnh là 164.011,6 KB. Với Pipes và Tents, cách gán lần lượt từng ô/từng cây làm không gian trạng thái thành một cây (không có trạng thái lặp), nên có thể tắt `visited` để tiết kiệm bộ nhớ (`check_visited=False`); nhóm giữ mặc định bật cho an toàn và đo nhất quán.

### 4.2. BrFS

Cài sẵn để so sánh (frontier là hàng đợi FIFO, cũng dùng `visited`), nhưng **không nằm trong benchmark chính thức**, vì đề bài chỉ yêu cầu một trong hai DFS hoặc BrFS. Khi thử trên bài N-Queens, BrFS tốn bộ nhớ gấp hàng trăm lần DFS và timeout ở 12×12.

### 4.3. A\*

- Chọn nút có f\*(n) = g\*(n) + h\*(n) nhỏ nhất bằng hàng đợi ưu tiên (`heapq`).
- Khóa sắp xếp là bộ **(f\*, −g\*, thứ tự sinh)**:
  - f\* nhỏ hơn được chọn trước;
  - nếu f\* bằng nhau, ưu tiên nút **sâu hơn** (g\* lớn hơn). Với các bài mà mọi lời giải nằm cùng độ sâu (Pipes, Tents), cách phá hòa này giúp A\* đi sâu nhanh;
  - thứ tự sinh để hai nút không bao giờ phải so sánh trực tiếp với nhau.
- Tập **CLOSED** chứa các trạng thái đã mở rộng; bảng `best_g` giữ g\* tốt nhất đã biết của mỗi trạng thái, chỉ đưa nút con vào hàng đợi khi tìm được đường tốt hơn.
- Kiểm tra đích khi **lấy nút ra** khỏi hàng đợi (không phải khi sinh), đúng theo A\* chuẩn.
- Nút có h\* = ∞ (ngõ cụt, ở heuristic `tension` của Tents) vẫn được đưa vào hàng đợi nhưng nằm ở đáy, nên không bao giờ được mở rộng trước khi tìm thấy đích.

Hệ quả đáng chú ý: khi h\* không phân biệt được các nút (f\* như nhau ở mọi nút, như h\* `naive` của Tents), luật phá hòa "ưu tiên nút sâu, rồi nút sinh trước" làm A\* duyệt **đúng thứ tự của DFS**. Bảng phụ xác nhận số nút mở rộng trùng tuyệt đối với DFS ở cả 10 đề Tents giải được.

### 4.4. Hill Climbing

- **Steepest-Ascent Hill Climbing**: mỗi bước xét **toàn bộ** láng giềng, chọn láng giềng có h\* nhỏ nhất. Nhiều láng giềng cùng h\* nhỏ nhất thì chọn ngẫu nhiên một cái.
- h\* giảm thì đi tiếp; h\* bằng thì chỉ đi nếu còn lượt **đi ngang** (`sideways`); không có láng giềng tốt hơn thì coi là kẹt (cực tiểu địa phương hoặc vùng bằng phẳng) và **random restart** từ `random_state()`.
- Dừng khi `goal_test` đúng. Không dừng chỉ vì h\* = 0, vì với h1 của Pipes, h1 = 0 chưa chắc đã là lời giải.
- Mọi lựa chọn ngẫu nhiên dùng một `random.Random(seed)` riêng, không dùng random toàn cục, nên **cùng seed thì cùng kết quả**.
- Tham số chính thức: tối đa 100 lần restart, tối đa 50 bước đi ngang liên tiếp, seed 0, tối đa 10.000 bước mỗi lần thử.
- Quy ước đếm: "số nút mở rộng" = số trạng thái mà giải thuật đứng tại đó và xét láng giềng; "số nút sinh ra" = tổng số láng giềng đã đánh giá; "frontier lớn nhất" = số láng giềng nhiều nhất trong một bước.

## 5. Tracer và định dạng trace cho GUI

- Mỗi lần mở rộng một nút (hoặc mỗi bước của Hill Climbing), tracer ghi một dòng JSON gồm: số bước, loại sự kiện, lưới (từ `encode()`), giá trị h\*, kích thước frontier, độ sâu.
- Loại sự kiện: `start` (trạng thái xuất phát của Hill Climbing), `expand` (DFS/BrFS/A\* mở rộng nút), `move` (Hill Climbing chuyển sang láng giềng), `restart`.
- Dòng đầu ghi thông tin chung (bài, giải thuật, input, kích thước), dòng cuối ghi kết quả.
- Chỉ lưu tối đa 5.000 bước đầu để file không quá lớn.
- h\* = ∞ được ghi thành chuỗi `"inf"`, vì JSON chuẩn không có giá trị vô cực.
- **Khi chạy benchmark, tracer luôn tắt**, để việc ghi file không làm sai số đo thời gian.

## 6. Benchmark và phương pháp đo

Đoạn dưới đây có thể đưa thẳng vào báo cáo:

> Toàn bộ thực nghiệm chạy trên cùng một máy tính: Windows 11, Python 3.13.5, CPU Intel64 Family 6 Model 154. Với mỗi cặp bài toán, giải thuật và input, nhóm ghi nhận bốn chỉ số.
>
> **Thời gian chạy** đo bằng `time.perf_counter()`, chỉ tính phần thực thi giải thuật, không tính thời gian đọc file input. Mỗi cấu hình chạy 3 lần, lấy giá trị trung vị để giảm ảnh hưởng của tác vụ nền.
>
> **Bộ nhớ** là bộ nhớ đỉnh do giải thuật cấp phát, đo bằng module `tracemalloc` ở một lần chạy riêng, vì `tracemalloc` làm chương trình chậm đi đáng kể. `tracemalloc` chỉ theo dõi bộ nhớ do Python cấp phát trong lúc giải thuật chạy, không gồm bộ nhớ của trình thông dịch, nên số liệu dùng để so sánh giữa các giải thuật chứ không phải tổng bộ nhớ của chương trình.
>
> **Số nút mở rộng** là số nút được lấy ra khỏi frontier để xét nút con (với Hill Climbing: số trạng thái giải thuật đứng tại đó và xét láng giềng). **Kích thước frontier lớn nhất** là số nút nhiều nhất cùng lúc nằm trong frontier.
>
> Mỗi lần chạy đặt trong một tiến trình riêng với giới hạn 300 giây; lần chạy vượt giới hạn được ghi là "timeout". Hill Climbing dùng seed cố định 0, tối đa 100 lần random restart và tối đa 50 bước đi ngang liên tiếp, nên kết quả lặp lại được. Bảng phụ so sánh biến thể đo một lần với giới hạn 120 giây.

Lệnh đã chạy:

```text
python -m core.benchmark --restarts 100 --sideways 50
python -m core.benchmark --variants --restarts 100 --timeout 120 --repeats 1
```

Kết quả: `results/benchmark.csv` (bảng chính, 32 dòng), `results/benchmark_variants.csv` (bảng phụ, 32 dòng), 12 biểu đồ trong `results/charts/` (trục y thang log).

Bảng phụ gồm hai phép so sánh, mỗi bài một phép, chỉ đổi đúng một thành phần:

- Tents: A\* với h\* `tension` so với h\* `naive`.
- Pipes: Hill Climbing (h1) có đi ngang 50 bước so với không đi ngang.

## 7. Kiểm thử và công cụ hỗ trợ

- **Bài N-Queens** (`examples/nqueens.py`) dùng để kiểm thử cả bốn giải thuật trước khi Pipes và Tents có code; đồng thời là ví dụ mẫu cách cài một `Problem` cho TV2, TV3.
- **`python -m core.check <bài> <input>`** tự kiểm tra một bài toán: có `load_problem()`, trạng thái hashable, `result()` và `neighbors()` không sửa trạng thái cũ, `is_valid()`/`goal_test()` trả về bool, h\* là số không âm, `encode()` chuyển được sang JSON, `random_state()` lặp lại được với cùng seed, và chạy thử từng giải thuật. Mọi Pull Request của bài toán đều phải qua script này với 0 lỗi trước khi merge.
- **Unit test**: 36 test (20 của Pipes, 16 của Tents), chạy bằng `python -m unittest discover tests`, đều qua.

## 8. Khó khăn khi ghép code và cách xử lý

| Vấn đề | Nguyên nhân | Cách giải quyết |
| --- | --- | --- |
| Benchmark chạy nhầm file lời giải như một đề | Benchmark đọc mọi file `.txt` trong `inputs/`, mà lời giải nằm cạnh đề | Benchmark bỏ qua file `*.sol.txt`; Pipes chuyển lời giải vào thư mục con `solutions/` |
| GUI vẽ lưới Pipes trống | `encode()` của Pipes xuất mã hex, còn phần vẽ của GUI chờ chữ N/E/S/W | Thống nhất mã hex; GUI đọc bằng `int(c, 16)` |
| GUI không hiện số gợi ý hàng/cột của Tents | `encode()` chỉ trả về bàn chơi | `encode()` trả về lưới (R+1)×(C+1) có thêm cột và hàng gợi ý |
| GUI bị treo khi mở trace Tents – DFS | DFS đi vào các nút ngõ cụt có h\* = ∞; biểu đồ h của GUI lỗi khi co giãn theo vô cực | Tracer ghi `"inf"`; GUI vẽ nút ngõ cụt ở đỉnh biểu đồ |
| Hill Climbing của Pipes chỉ giải được đề nhỏ | Vùng bằng phẳng: rất nhiều láng giềng cùng h\* | Thêm tham số đi ngang vào engine; chính thức dùng 50 bước |
| Hill Climbing ở đề Pipes 15×15 quá chậm | Mỗi bước tính lại h1 trên cả lưới cho vài nghìn láng giềng | Tính h1 tăng dần: chỉ tính lại quanh các ô vừa xoay; kết quả giữ nguyên, nhanh hơn khoảng 5 lần |
| Không cài được `pygame` trên Python 3.14 | Bản `pygame` 2.6.1 chưa có gói dựng sẵn cho Python 3.14 | Đổi sang `pygame-ce` (cùng lệnh `import pygame`, không phải sửa code GUI) |

## 9. Kết quả tổng hợp và nhận xét chung

Số liệu từ `results/benchmark.csv`:

| Bài | Giải thuật | Số đề giải được | Đề lớn nhất giải được: thời gian / bộ nhớ đỉnh / số nút mở rộng |
| --- | --- | --- | --- |
| Pipes | DFS | 5/5 | Đề 05 (15×15): 0,0093 s / 687,9 KB / 823 nút |
| Pipes | Hill Climbing | 5/5 | Đề 05 (15×15): 99,7 s / 7.904,7 KB / 14.572 nút, 82 lần restart |
| Tents | DFS | 10/11 | Đề 10 (25×25): 58,1 s / 164.011,6 KB / 222.763 nút; đề 11 (30×30) timeout |
| Tents | A\* | 11/11 | Đề 11 (30×30): 1,96 s / 1.981,9 KB / 1.218 nút |

Bảng phụ (`results/benchmark_variants.csv`):

- **Pipes, Hill Climbing không đi ngang:** giải được đề 01–03 với lần lượt 2, 21, 63 lần restart; thất bại ở đề 04 và 05 sau 100 lần restart. Có đi ngang 50 bước: giải cả 5 đề, đề 01–03 không cần restart.
- **Tents, A\* với h\* `naive`:** số nút mở rộng trùng tuyệt đối với DFS ở cả 10 đề giải được; đề 11 timeout.

Nhận xét chung:

1. **Không có giải thuật nào tốt nhất cho mọi bài.** Ở Tents, A\* nhanh hơn DFS hàng trăm lần. Ở Pipes thì ngược lại, DFS nhanh hơn Hill Climbing khoảng 10.000 lần ở đề 05.
2. **Ở Pipes, ràng buộc chặt và cục bộ** nên `is_valid` của DFS cắt nhánh gần như ngay lập tức. Hill Climbing không có cơ chế cắt nhánh, phải mò qua cực tiểu địa phương và vùng bằng phẳng, nên cần đi ngang và rất nhiều lần restart.
3. **Ở Tents, sức mạnh của A\* đến từ heuristic chứ không phải từ công thức f = g + h:** cùng A\*, đổi sang h\* `naive` thì A\* chạy y hệt DFS.
4. **Bộ nhớ DFS lớn ở đề Tents lớn** là do tập `visited` (mục 4.1), không phải do stack.

## 10. Câu hỏi có thể bị hỏi

1. **Vì sao DFS của nhóm tốn tới 164 MB, trong khi DFS vốn tiết kiệm bộ nhớ?** Vì DFS dùng tập `visited` để không quay lại trạng thái cũ, và tập này lưu mọi trạng thái đã sinh. Bản thân stack chỉ có tối đa 71 nút ở đề đó. Với Pipes và Tents có thể tắt `visited` vì không có trạng thái lặp, nhưng nhóm giữ mặc định để engine an toàn với mọi bài.
2. **Vì sao đo thời gian và bộ nhớ ở hai lần chạy riêng?** Vì `tracemalloc` làm chương trình chậm đi nhiều lần; đo chung thì số thời gian bị thổi phồng.
3. **Làm sao bảo đảm kết quả Hill Climbing lặp lại được?** Mọi lựa chọn ngẫu nhiên lấy từ một `random.Random(seed)` riêng với seed cố định 0. Bằng chứng: hai lần chạy (bảng chính và bảng phụ) cho cùng số nút và cùng số restart ở mọi đề.
4. **Vì sao A\* phá hòa theo nút sâu hơn?** Với Pipes và Tents, mọi lời giải nằm cùng độ sâu, nên khi nhiều nút cùng f\*, đi sâu trước giúp tới đích nhanh hơn. Đó cũng là lý do A\* với h\* `naive` duyệt đúng thứ tự của DFS.

## 11. Ghi chú cho TV5 khi viết báo cáo

- Mọi con số chỉ lấy từ hai file CSV trong `results/`, không lấy từ tin nhắn hay số chạy thử.
- Kích thước đề Tents lấy theo bảng trong phiếu của TV3 (đề 10 là 25×25, chỉ đề 11 là 30×30).
- Không đưa bảng so sánh h1/h2 trong phiếu của TV2 vào báo cáo (không phải số liệu chính thức); chỉ giữ 2–3 câu giải thích vì sao chọn h1.
- Ký hiệu thống nhất theo slide chương 3: h(n) là chi phí thật, h\*(n) là ước lượng, f\*(n) = g\*(n) + h\*(n).

## 12. Tài liệu tham khảo

1. Vương Bá Thịnh, *Problems and Search* (slide chương 2), Khoa Khoa học và Kỹ thuật Máy tính, Trường Đại học Bách khoa – ĐHQG TP.HCM.
2. Vương Bá Thịnh, *Heuristic search* (slide chương 3), cùng nguồn.
3. Đặc tả Bài tập lớn 1 (HK1 26-27), Tìm kiếm (`BTL1.pdf`).
4. Tài liệu Python: `time.perf_counter`, `tracemalloc`, `heapq`, `multiprocessing`.
5. Mã nguồn và số liệu của nhóm: `core/`, `main.py`, `examples/nqueens.py`, `results/benchmark.csv`, `results/benchmark_variants.csv`.
