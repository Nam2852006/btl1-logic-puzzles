# BTL1 – Tìm kiếm trên Logic Puzzles

Môn Nhập môn Trí tuệ nhân tạo, HK1 2026–2027. Hai bài toán: **Pipes** (DFS + Hill Climbing) và **Tents** (DFS + A\*).

## Cài đặt

Yêu cầu Python 3.9 trở lên.

```bash
git clone <link repo>
cd btl1
python -m venv .venv
# Windows: .venv\Scripts\activate    |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Mọi lệnh bên dưới chạy từ **thư mục gốc** `btl1/`.

## Chạy một bài toán

```bash
python main.py --puzzle tents --algo astar --input inputs/tents/01.txt
python main.py --puzzle pipes --algo hc --input inputs/pipes/01.txt --restarts 50
python main.py --puzzle tents --algo dfs --input inputs/tents/01.txt --trace   # ghi trace cho GUI
```

Giải thuật: `dfs`, `bfs`, `astar`, `hc`. Bài đồ chơi để thử: `--puzzle nqueens --input inputs/nqueens/08.txt`.

## Chạy benchmark (TV1)

```bash
python -m core.benchmark                              # chạy chính thức: pipes + tents, timeout 300 s, đo 3 lần
python -m core.benchmark --timeout 30 --repeats 1     # chạy nhanh khi đang thử
python -m core.benchmark --puzzles nqueens            # thử với bài đồ chơi
```

Kết quả: `results/benchmark.csv` (mở được bằng Excel) và biểu đồ trong `results/charts/`.

**Bảng phụ so sánh biến thể** (cho phần giải thích trong báo cáo):

```bash
python -m core.benchmark --variants --restarts 100 --timeout 120 --repeats 1
```

So sánh Tents A\* với `h=tension` và `h=naive`, Pipes Hill Climbing với `sideways=50` và `sideways=0`.
Danh sách biến thể nằm trong `VARIANTS` của `core/registry.py`. Kết quả ghi riêng vào
`results/benchmark_variants.csv` và các biểu đồ `results/charts/variants_*.png`, không ảnh hưởng bảng chính.
Bản chạy chính thức phải chạy trên **một máy duy nhất**, đóng các ứng dụng nặng khi chạy.

Ý nghĩa các cột CSV:

| Cột | Ý nghĩa |
| --- | --- |
| `status` | `ok`, `timeout` (vượt thời gian), `error` (lỗi khi chạy) |
| `success` | Có tìm ra lời giải hay không |
| `time_s` | Thời gian chạy giải thuật, trung vị của các lần đo (giây) |
| `peak_kb` | Bộ nhớ đỉnh trong lúc giải thuật chạy, đo bằng `tracemalloc` (KB) |
| `nodes_expanded` | Số nút được lấy khỏi frontier và mở rộng |
| `nodes_generated` | Số nút con được sinh ra |
| `max_frontier` | Số nút lớn nhất cùng lúc trong frontier |
| `restarts` | Số lần random restart (chỉ Hill Climbing) |

## Cấu trúc thư mục và người sở hữu

```text
btl1/
├── main.py              TV1  chạy 1 cặp bài – giải thuật – input
├── core/                TV1  problem.py, search.py, tracer.py, benchmark.py, registry.py, check.py
├── examples/nqueens.py  TV1  bài đồ chơi + ví dụ mẫu cách cài một Problem
├── puzzles/_template.py TV1  file mẫu để TV2, TV3 chép
├── puzzles/pipes.py     TV2
├── puzzles/tents.py     TV3
├── inputs/pipes/        TV2  file input + lời giải đúng
├── inputs/tents/        TV3  file input + lời giải đúng
├── gui/                 TV4
├── results/             TV1  benchmark.csv, biểu đồ, file trace
├── report/              TV5
└── slides/              TV5
```

Mỗi người **chỉ sửa thư mục của mình**. Chỉ TV1 sửa `core/`.

## Dành cho TV2, TV3: cách cài một bài toán

1. Chép `puzzles/_template.py` thành `puzzles/pipes.py` (hoặc `tents.py`).
2. Cài các hàm theo interface trong `core/problem.py`. Ví dụ hoàn chỉnh: `examples/nqueens.py`.
3. Module phải có hàm `load_problem(path) -> Problem`.
4. Đặt file input vào `inputs/pipes/` (hoặc `inputs/tents/`), đặt tên `01.txt`, `02.txt`… theo độ khó tăng dần. File lời giải đặt tên `01.sol.txt`, `02.sol.txt`… để benchmark tự bỏ qua.
5. **Trước khi tạo Pull Request**, tự kiểm tra code bằng:

   ```bash
   python -m core.check pipes inputs/pipes/01.txt
   ```

   Script báo `0 lỗi` thì mới gửi Pull Request. Mỗi lỗi đều kèm gợi ý cách sửa.

**Ba quy ước bắt buộc:**

- Trạng thái là `tuple` (hashable), **không** dùng `list`.
- `result(state, action)` trả về trạng thái **mới**, không sửa trạng thái cũ.
- `encode(state)` trả về list các list (str/int) để GUI vẽ.

Hàm cần cài:

| Hàm | DFS | A\* (Tents) | Hill Climbing (Pipes) |
| --- | --- | --- | --- |
| `initial_state`, `actions`, `result`, `is_valid`, `goal_test` | Bắt buộc | Bắt buộc | `goal_test` bắt buộc |
| `h` | Không cần | Bắt buộc | Bắt buộc |
| `random_state`, `neighbors` | Không cần | Không cần | Bắt buộc |
| `encode`, `size_label` | Bắt buộc | Bắt buộc | Bắt buộc |

## Dành cho TV4: định dạng file trace

File `.jsonl`, mỗi dòng một JSON. Mẫu thật: `results/traces/sample_trace.jsonl` (DFS giải 4-Queens).

```text
{"type": "meta", "puzzle": "nqueens", "algorithm": "dfs", "input": "...", "size": "4x4",
 "total_steps": 9, "recorded_steps": 9, "truncated": false}
{"type": "step", "step": 1, "event": "expand", "grid": [[".", "."], ...], "h": 4, "frontier": 0, "depth": 0}
...
{"type": "result", "success": true, "grid": [[...]], "nodes_expanded": 9, "restarts": 0}
```

- `event`: `expand` (DFS/BrFS/A\*), `move` hoặc `restart` (Hill Climbing).
- `grid` là kết quả `encode()` của bài toán; ký hiệu trong ô do TV2, TV3 quy định.
- Đọc file bằng `core.tracer.load_trace(path)` → `(meta, steps, result)`.
- Trace bị giới hạn 5.000 bước đầu (`--max-trace-steps` để đổi); `truncated: true` nghĩa là đã cắt bớt.

## Quy trình Git

- Mỗi người làm trên nhánh riêng: `tv1-core`, `tv2-pipes`, `tv3-tents`, `tv4-gui`, `tv5-report`.
- Chạy được rồi mới tạo Pull Request vào `main`; TV1 duyệt và merge.
- Không commit thư mục `.venv/` và `__pycache__/`.
