"""
core/tracer.py — Ghi lại từng bước tìm kiếm để GUI (TV4) phát lại.
Người sở hữu: TV1.

Định dạng file trace (JSON Lines, mỗi dòng một object):
  Dòng 1      : {"type": "meta", "puzzle": ..., "algorithm": ..., "input": ...,
                 "total_steps": ..., "recorded_steps": ..., "truncated": ...}
  Các dòng giữa: {"type": "step", "step": 1, "event": "expand", "grid": [[...]],
                 "h": 3, "frontier": 5, "depth": 2}
  Dòng cuối   : {"type": "result", "success": true, "grid": [[...]] hoặc null,
                 "nodes_expanded": ..., "restarts": ...}

Giá trị "event":
  "expand"  : DFS/BrFS/A* mở rộng một nút
  "move"    : Hill Climbing chuyển sang láng giềng tốt nhất
  "restart" : Hill Climbing bắt đầu lại từ một trạng thái ngẫu nhiên

LƯU Ý: khi chạy benchmark luôn để tracer=None, vì ghi trace làm chậm
giải thuật và làm sai số đo thời gian.
"""
from __future__ import annotations

import json
import os
from typing import Optional


class Tracer:
    def __init__(self, max_steps: int = 5000):
        self.max_steps = max_steps   # giới hạn số bước lưu, tránh file quá lớn
        self.events: list = []
        self.total_steps = 0         # tổng số bước thực tế (kể cả bước không lưu)
        self.truncated = False

    def log(self, problem, state, frontier: int, event: str = "expand",
            depth: Optional[int] = None) -> None:
        self.total_steps += 1
        if len(self.events) >= self.max_steps:
            self.truncated = True
            return
        self.events.append({
            "type": "step",
            "step": self.total_steps,
            "event": event,
            "grid": problem.encode(state),
            "h": problem.h(state),
            "frontier": frontier,
            "depth": depth,
        })

    def save(self, path: str, meta: dict, result=None, problem=None) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        header = {
            "type": "meta",
            **meta,
            "total_steps": self.total_steps,
            "recorded_steps": len(self.events),
            "truncated": self.truncated,
        }
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(header, ensure_ascii=False) + "\n")
            for ev in self.events:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            if result is not None:
                final = {
                    "type": "result",
                    "success": result.success,
                    "grid": problem.encode(result.solution)
                    if (result.success and problem is not None) else None,
                    "nodes_expanded": result.nodes_expanded,
                    "restarts": result.restarts,
                }
                f.write(json.dumps(final, ensure_ascii=False) + "\n")


def load_trace(path: str):
    """Đọc file trace, trả về (meta, steps, result). TV4 có thể dùng hàm này."""
    meta, steps, result = None, [], None
    with open(path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj["type"] == "meta":
                meta = obj
            elif obj["type"] == "step":
                steps.append(obj)
            elif obj["type"] == "result":
                result = obj
    return meta, steps, result
