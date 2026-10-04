# Graduate Admission Prediction System

## 1. Thành viên (Họ tên, MSSV, phần việc)
* **Thành viên 1:** Nguyễn Tiến Thành – 10123298 – Phụ trách: Xây dựng Backend
Làm báo cáo word,làm slide báo cáo
Phân tích EDA,tiền xử lý dữ liệu
Train model Linear Regression, GradientBoosting & Random Forest 
* **Thành viên 2:** Phạm Văn Hiệu – 10123135 – Phụ trách: Xây dựng Khung dự án
Làm ai-service, frontend
Train model SVR & KNN.

---

## 2. Bài toán (Mô tả, loại bài toán, cột mục tiêu, ý nghĩa thực tế)
* **Mô tả bài toán:** Xây dựng hệ thống dự đoán xác suất trúng tuyển chương trình sau đại học cho sinh viên dựa trên các chỉ số học thuật và hồ sơ cá nhân.
* **Loại bài toán:** Hồi quy (Regression).
* **Cột mục tiêu (Target):** `Chance of Admit` (giá trị thực từ 0.0 đến 1.0).
* **Ý nghĩa thực tế:** Giúp các ứng viên định hướng và đánh giá khách quan cơ hội trúng tuyển vào các trường đại học mong muốn, từ đó có kế hoạch cải thiện điểm số (GRE, TOEFL, CGPA) hoặc chuẩn bị hồ sơ (SOP, LOR) phù hợp hơn.

---

## 3. Dữ liệu (Link Kaggle, giấy phép, mô tả cột, cách giải nén dataset.zip)
* **Link Kaggle:** [Graduate Admissions Dataset trên Kaggle](https://www.kaggle.com/datasets/mohansacharya/graduate-admissions)
* **Giấy phép (License):** CC0: Public Domain.
* **Mô tả các cột đặc trưng (Features):**
  * `GRE Score`: Điểm thi GRE (290 - 340).
  * `TOEFL Score`: Điểm thi TOEFL (92 - 120).
  * `University Rating`: Đánh giá chất lượng trường đại học trước đó (1 - 5).
  * `SOP`: Điểm đánh giá Statement of Purpose (1.0 - 5.0, bước nhảy 0.5).
  * `LOR`: Điểm đánh giá Letter of Recommendation (1.0 - 5.0, bước nhảy 0.5).
  * `CGPA`: Điểm trung bình tích lũy bậc cử nhân (6.8 - 9.92).
  * `Research`: Kinh nghiệm nghiên cứu khoa học (0 hoặc 1).
* **Cách giải nén dataset:**
  Tải tệp `dataset.zip` từ Kaggle, đặt vào thư mục `ai-models/data/` và chạy lệnh tại terminal:
  ```bash
  unzip ai-models/data/dataset.zip -d ai-models/data/

```

---

## 4. Kết quả model (Bảng so sánh metric, model được chọn và lý do)

* **Bảng so sánh các mô hình:**
| Mô hình (Model) | MAE (Mean Absolute Error) | RMSE | $R^2$ Score |
| --- | --- | --- | --- |
| **Linear Regression** | ~0.042 | ~0.054 | ~0.81 |
| **Support Vector Regressor (SVR)** | ~0.045 | ~0.058 | ~0.78 |
| **K-Nearest Neighbors (KNN)** | ~0.048 | ~0.062 | ~0.75 |


* **Model được chọn:** `Linear Regression` (Lưu tại `models/graduate_admission_model.joblib` và hỗ trợ cả SVR `svr_regressor_personal.joblib`).
* **Lý do chọn:** Mô hình Linear Regression đạt độ chính xác ổn định, tốc độ suy luận (inference) cực nhanh, ít tốn tài nguyên và dễ dàng giải thích mối quan hệ tuyến tính giữa các đặc trưng đầu vào với xác suất trúng tuyển.

---


---

## 5. Đóng gói model (Đường dẫn file model trong repo, cách export từ Colab)

* **Đường dẫn file model trong repository:**
* `ai-models/models/graduate_admission_model.joblib`
* `ai-models/models/graduate_admission_model_metadata.json`
* `ai-models/models/svr_regressor_personal.joblib`


* **Cách export từ Google Colab:**
Sau khi huấn luyện mô hình bằng Scikit-learn trong Colab, sử dụng thư viện `joblib` để lưu artifact và metadata:
```python
import joblib
import json

# Lưu model
joblib.dump(best_model, "graduate_admission_model.joblib")

# Lưu metadata
metadata = {
    "model_name": "Linear Regression",
    "model_version": "1.0.0",
    "target": "Chance of Admit",
    "features": ["GRE Score", "TOEFL Score", "University Rating", "SOP", "LOR", "CGPA", "Research"],
    "test_metrics": {"mae": 0.042}
}
with open("graduate_admission_model_metadata.json", "w") as f:
    json.dump(metadata, f)

```



---

## 6. Kiến trúc hệ thống (Sơ đồ FE - BE - AI)

```text
[ Frontend (React / Vite) ] 
         │ (HTTP REST API / Port 3000 -> 80)
         ▼
[ Backend (FastAPI / Port 8000) ] 
         │ (HTTP REST API / Port 8001)
         ▼
[ AI Service (FastAPI + Scikit-learn / Port 8001) ] 
         │ (Loads model via Joblib in memory)
         ▼
[ ML Model Artifact (.joblib) ]

```

---

## 7. Chạy trên máy (Yêu cầu & Lệnh thực thi)

* **Yêu cầu hệ thống:** Đã cài đặt **Docker** và **Docker Compose**.
* **Các bước thực thi:**
1. Tạo tệp biến môi trường từ tệp mẫu:
```bash
cp .env.example .env

```


2. Khởi động toàn bộ hệ thống bằng Docker Compose:
```bash
docker compose up --build

```





---

## 8. Huấn luyện lại model (Link Colab, thứ tự chạy notebook)

* **Link Google Colab:** [Link tới Colab Notebook huấn luyện model] *(Cập nhật link của bạn tại đây)*
* **Thứ tự chạy các cell trong Notebook:**
1. **Cell 1:** Tải dữ liệu từ Kaggle API hoặc upload tệp dữ liệu gốc.
2. **Cell 2:** Tiền xử lý dữ liệu, kiểm tra giá trị khuyết thiếu và chuẩn hóa các cột đặc trưng.
3. **Cell 3:** Chia tập dữ liệu thành Train/Test (80/20).
4. **Cell 4:** Huấn luyện các mô hình (Linear Regression, SVR, KNN) và đánh giá qua các chỉ số MAE, RMSE.
5. **Cell 5:** Xuất file artifact `.joblib` và tệp `_metadata.json`.



---

## 9. Biến môi trường (Bảng từng biến, ý nghĩa)

| Tên biến (Variable) | Ý nghĩa mô tả | Giá trị mẫu / Mặc định |
| --- | --- | --- |
| `AI_SERVICE_URL` | Địa chỉ URL nội bộ kết nối từ Backend sang AI Service. | `http://ai-service:8001` |
| `API_URL` | Địa chỉ API public thông qua ngrok tunnel. | `https://snazzy-diffuser-skiing.ngrok-free.dev` |
| `CORS_ORIGINS` | Danh sách các nguồn gốc được phép gọi CORS. | `http://localhost:3000,https://two-pets-love.loca.lt` |
| `PORT` | Cổng lắng nghe của dịch vụ AI / Backend. | `8001` (AI) / `8000` (Backend) |
| `MODEL_PATH` | Đường dẫn tới tệp artifact mô hình bên trong container. | `models/model.joblib` |

---

## 10. Triển khai (Cách public: deploy/tunnel, các bước, cách cập nhật khi đổi link)

* **Giải pháp Tunneling:** Sử dụng `ngrok` hoặc `localtunnel` để public cổng cục bộ ra môi trường Internet công cộng có hỗ trợ HTTPS.
* **Các bước thực hiện:**
1. Khởi động ngrok trỏ tới cổng Backend (`8000`) hoặc Frontend (`3000`):
```bash
ngrok http 8000

```


2. Sao chép URL công cộng nhận được (ví dụ: `https://xxxx.ngrok-free.app`).
3. Cập nhật lại biến `API_URL` hoặc `CORS_ORIGINS` trong tệp `.env`.
4. Khởi động lại hệ thống bằng lệnh `docker compose up -d --build`.



---

## 11. Demo online (Địa chỉ App, địa chỉ AI Service/docs)

*(Cập nhật lại thông tin này mỗi khi thay đổi link tunnel)*

* **Địa chỉ Frontend App:** [https://two-pets-love.loca.lt](https://www.google.com/url?sa=E&source=gmail&q=https://two-pets-love.loca.lt)
* **Địa chỉ Backend API Docs (Swagger):** `https://snazzy-diffuser-skiing.ngrok-free.dev/docs`
* **Địa chỉ AI Service Docs:** `http://localhost:8001/docs` (Nội bộ Docker Network)

---

## 12. Nhật ký đổi cổng/tunnel (Thời điểm đổi, địa chỉ cũ → mới)

| Thời điểm (Date) | Dịch vụ (Service) | Địa chỉ cũ | Địa chỉ mới | Ghi chú |
| --- | --- | --- | --- | --- |
| *03/10/2026* | Backend API | `http://localhost:8000` | `https://snazzy-diffuser-skiing.ngrok-free.dev` | Khởi tạo ngrok tunnel công khai. |
| *03/10/2026* | Frontend App | `http://localhost:3000` | `https://two-pets-love.loca.lt` | Chuyển sang localtunnel để test giao diện. |

---

## 13. Kết quả kiểm thử hiệu năng

* **Kiểm thử tự động (Pytest):** Toàn bộ các kịch bản kiểm thử trên AI Service (kiểm tra trạng thái `/health`, schema `/model-info`, dự đoán `/predict` và xử lý lỗi dữ liệu đầu vào không hợp lệ) đều đạt kết quả **Passed** 100%.
* **Hiệu năng xử lý:**
* Mô hình được nạp sẵn vào bộ nhớ RAM (`app.state.model`) thông qua vòng đời `lifespan` của FastAPI, giúp thời gian phản hồi (latency) cho mỗi yêu cầu dự đoán đạt mức tối ưu dưới **15ms**.
* Hệ thống giám sát tự động (`healthcheck`) hoạt động ổn định với chu kỳ kiểm tra 10 giây/lần.



---

## 14. Hạn chế và hướng phát triển

* **Hạn chế:**
* Mô hình hiện tại là mô hình tĩnh, chưa hỗ trợ cơ chế tự động học hỏi và cập nhật liên tục (Online Learning / Retraining) từ dữ liệu mới của người dùng.
* Các đặc trưng đầu vào còn giới hạn ở các chỉ số học thuật truyền thống, chưa tích hợp thêm các yếu tố định tính như kỹ năng mềm hoặc hoạt động ngoại khóa.


* **Hướng phát triển:**
* Tích hợp công cụ giải thích mô hình (Explainable AI như **SHAP** hoặc **LIME**) để hiển thị trực quan các yếu tố tác động lớn nhất đến kết quả dự đoán của ứng viên.
* Nâng cấp kiến trúc lên nền tảng đám mây chính thức (Cloud Deployment như AWS ECS, Google Cloud Run) thay vì chạy trên Docker Compose cục bộ nhằm đảm bảo tính sẵn sàng cao (High Availability).



```

```
