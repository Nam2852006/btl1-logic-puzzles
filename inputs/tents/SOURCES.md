# Nguồn các input Tents

Tất cả là đề thật từ https://www.puzzle-tents.com/, chép từ ảnh chụp màn hình bằng nhận diện pixel; số gợi ý đọc từ ảnh phóng to.
Mỗi đề đã được solver kiểm tra: tổng gợi ý hàng = tổng gợi ý cột = số cây, và có đúng 1 nghiệm (lưu ở NN.sol.txt).

| File | Cỡ | Số cây | Loại / Puzzle ID |
|------|-----|--------|------------------|
| 01 | 6x6 | 7 | (chưa ghi) |
| 02 | 6x6 | 7 | (chưa ghi) |
| 03 | 8x8 | 12 | (chưa ghi) |
| 04 | 8x8 | 12 | (chưa ghi) |
| 05 | 10x10 | 20 | (chưa ghi) |
| 06 | 10x10 | 20 | (chưa ghi) |
| 07 | 15x15 | 45 | (chưa ghi) |
| 08 | 15x15 | 45 | (chưa ghi) |
| 09 | 20x20 | 80 | (chưa ghi) |
| 10 | 25x25 | 125 | Weekly |
| 11 | 30x30 | 180 | Monthly |

Định dạng: dòng 1 `R C`; R dòng lưới (`T` cây, `.` trống); 1 dòng R số lều theo hàng; 1 dòng C số lều theo cột. File `.sol.txt`: cùng lưới, `A` = lều.
