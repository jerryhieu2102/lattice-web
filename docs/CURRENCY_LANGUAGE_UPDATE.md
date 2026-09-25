# LATTICE — cập nhật tiền tệ và ngôn ngữ (24/09/2026)

## Nội dung đã bổ sung

- 13 tiền tệ: EUR, USD, CNY, VND, GBP, JPY, KRW, SGD, HKD, AUD, CAD, CHF, THB.
- 169 cặp có hướng, gồm cả cùng tiền tệ; 170 tuyến demo vì VND → EUR có thêm tuyến nhanh. Có USD ↔ VND, CNY ↔ VND và các cặp tiền khác với USD/CNY.
- API, trích xuất mã tiền tệ từ tài liệu, nguồn tiền, nghĩa vụ, bộ tối ưu, biểu đồ và mô phỏng cùng dùng danh mục tiền tệ chung.
- English, Tiếng Việt và 简体中文 trên 11 trang. Lựa chọn ngôn ngữ được nhớ trong trình duyệt. Có định dạng tiền, ngày và phông chữ Trung Quốc đi kèm, không cần tải phông từ CDN.

## Cách sử dụng

1. Khởi động theo README. Chọn ngôn ngữ ở màn hình đăng nhập hoặc thanh trên cùng.
2. Vào **Nguồn tiền / Funding / 资金**, tìm bảng chọn cặp tiền. Chọn tiền nguồn và tiền đích để xem tỷ giá demo, phí và thời gian đến dự kiến.
3. Dùng **Thêm nguồn tiền** để nhập số dư USD, CNY hoặc một tiền tệ được hỗ trợ. Chọn tiền tệ của khoản phải trả trong **Khoản phải trả**.
4. Xác nhận bằng chứng, tạo kế hoạch. Bộ tối ưu tự chọn tuyến hợp lệ theo tiền tệ, hạn thanh toán, phí, quyền và dự phòng.
5. Trên database demo cũ, API tự thêm những tuyến còn thiếu; tiền và tài liệu đang có được giữ lại. Kế hoạch cũ cần tạo lại vì tập tuyến đã thay đổi. Không cần đặt lại Maya để nhận các tuyến mới.

## Kết quả kiểm thử

297/297 backend, 15/15 frontend và 7/7 Playwright đạt. TypeScript, Ruff, ESLint, build production, migration và khởi động PostgreSQL/API/web đều đạt. FAST 48/48 và FULL 500/500 là kết quả tính toán thực tế, có JSON/CSV.

Các lệnh và kết quả chính xác nằm trong `verification/final-results.json`; dữ liệu benchmark tại `../benchmark/results/`. Ảnh giao diện nằm trong `screenshots/`.

## Phạm vi

Tỷ giá là dữ liệu demo cố định; giao dịch chỉ diễn ra trong mô phỏng. Tổng hợp so sánh, điểm khắc phục và chi phí phát sinh vẫn dùng EUR làm đơn vị chung có ghi nhãn. Từng nguồn và khoản phải trả giữ đúng tiền tệ của mình.

VND, JPY và KRW không nhận phần thập phân. Các tiền khác hỗ trợ hai chữ số thập phân. Phí và tiền trừ tại nguồn được làm tròn lên để không thiếu tiền đích; phần chênh lệch làm tròn được ghi trong kế hoạch.

Nội dung gốc, trích dẫn bằng chứng, mã tài khoản và JSON nhật ký không được dịch hoặc sửa. Bộ trích xuất dùng tài liệu có nhãn tiếng Anh và mã ISO; chưa có OCR tổng quát cho tài liệu tiếng Việt/Trung. Bộ phân loại mục tiêu nhận các câu cơ bản của cả ba ngôn ngữ và không có quyền phê duyệt thanh toán.

Docker chưa được chạy trong môi trường kiểm thử này vì không có Docker CLI/daemon. Bộ chạy PostgreSQL cục bộ đã được kiểm chứng.
