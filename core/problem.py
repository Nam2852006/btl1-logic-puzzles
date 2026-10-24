"""
core/problem.py — Interface chung cho mọi bài toán.
Người sở hữu: TV1. CHỈ TV1 được sửa file này. Cần thêm hàm thì báo nhóm.

Ba quy ước BẮT BUỘC với mọi bài toán (TV2: Pipes, TV3: Tents):
  1. Trạng thái (state) phải HASHABLE: dùng tuple (hoặc tuple lồng tuple),
     KHÔNG dùng list/dict. A* và DFS lưu state vào set nên list sẽ báo lỗi.
  2. Trạng thái là BẤT BIẾN: result(state, action) phải trả về state MỚI,
     không được sửa state cũ tại chỗ.
  3. encode(state) trả về lưới đơn giản (list các list chứa str/int) để GUI
     vẽ và để lưu vào file trace dạng JSON.

Khuyến nghị: dùng CÙNG MỘT cách biểu diễn cho tìm kiếm có hệ thống (DFS/A*)
và tìm kiếm cục bộ (Hill Climbing), ví dụ tuple các ô, ô chưa gán là None.
Khi đó goal_test và h dùng chung được cho cả hai.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Hashable, List, Optional

State = Hashable
Action = Any


class Problem(ABC):
    """Lớp cha của mọi bài toán. Puzzle con kế thừa và cài các hàm bên dưới."""

    #: Tên ngắn của bài toán, ví dụ "pipes", "tents".
    name: str = "problem"

    # ------------------------------------------------------------------
    # Dùng cho DFS, BrFS, A* (tìm kiếm theo đường đi trong không gian trạng thái)
    # ------------------------------------------------------------------
    @abstractmethod
    def initial_state(self) -> State:
        """Trạng thái đầu."""

    @abstractmethod
    def actions(self, state: State) -> List[Action]:
        """Danh sách hành động áp dụng được tại state (thứ tự = thứ tự duyệt)."""

    @abstractmethod
    def result(self, state: State, action: Action) -> State:
        """Sinh nút con: áp dụng action lên state, trả về state MỚI."""

    def is_valid(self, state: State) -> bool:
        """Kiểm tra ràng buộc hợp lệ. Được gọi SAU khi sinh nút con;
        trả về False thì nút con bị loại (cắt nhánh)."""
        return True

    @abstractmethod
    def goal_test(self, state: State) -> bool:
        """True nếu state là trạng thái đích."""

    def step_cost(self, state: State, action: Action) -> float:
        """Chi phí một bước. Mặc định mỗi bước tốn 1."""
        return 1

    # ------------------------------------------------------------------
    # Heuristic
    # ------------------------------------------------------------------
    def h(self, state: State) -> float:
        """Ước lượng khoảng cách từ state tới đích (càng nhỏ càng gần).
        A* dùng f = g + h; Hill Climbing tìm cách giảm h về 0."""
        return 0

    # ------------------------------------------------------------------
    # Dùng cho Hill Climbing (tìm kiếm cục bộ trên trạng thái đầy đủ)
    # ------------------------------------------------------------------
    def random_state(self, rng: random.Random) -> State:
        """Một trạng thái ĐẦY ĐỦ ngẫu nhiên, dùng làm điểm xuất phát và
        cho random restart. Luôn dùng rng được truyền vào (không dùng
        random toàn cục) để kết quả lặp lại được với cùng seed."""
        raise NotImplementedError(f"{self.name}: chưa cài random_state()")

    def neighbors(self, state: State) -> List[State]:
        """Các trạng thái láng giềng của một trạng thái đầy đủ."""
        raise NotImplementedError(f"{self.name}: chưa cài neighbors()")

    # ------------------------------------------------------------------
    # Dùng cho GUI và báo cáo
    # ------------------------------------------------------------------
    def encode(self, state: State) -> list:
        """Chuyển state thành lưới (list các list str/int) để vẽ và lưu trace."""
        return [[str(state)]]

    def size_label(self) -> str:
        """Nhãn kích thước để ghi vào bảng benchmark, ví dụ "5x5"."""
        return ""


@dataclass
class SearchResult:
    """Kết quả trả về của mọi giải thuật trong core/search.py."""

    algorithm: str
    success: bool
    solution: Optional[State] = None          # trạng thái đích (None nếu thất bại)
    path: List[Action] = field(default_factory=list)  # chuỗi hành động (rỗng với Hill Climbing)
    nodes_expanded: int = 0                   # số nút đã mở rộng
    nodes_generated: int = 0                  # số nút con đã sinh ra
    max_frontier: int = 0                     # kích thước frontier lớn nhất
    restarts: int = 0                         # số lần random restart (chỉ Hill Climbing)
    note: str = ""                            # ghi chú, ví dụ lý do thất bại

    def summary(self) -> str:
        status = "TÌM THẤY lời giải" if self.success else "KHÔNG tìm thấy lời giải"
        lines = [
            f"[{self.algorithm}] {status}",
            f"  Số nút mở rộng   : {self.nodes_expanded}",
            f"  Số nút sinh ra   : {self.nodes_generated}",
            f"  Frontier lớn nhất: {self.max_frontier}",
        ]
        if self.algorithm == "hc":
            lines.append(f"  Số lần restart   : {self.restarts}")
        if self.path:
            lines.append(f"  Độ dài đường đi  : {len(self.path)}")
        if self.note:
            lines.append(f"  Ghi chú          : {self.note}")
        return "\n".join(lines)
