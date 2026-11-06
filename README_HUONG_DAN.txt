========================================
    AYY NetOps - Huong dan su dung
    Network Operations Analytics
    Chi nhanh AYY - VCM Myanmar
========================================

NGUOI VAN HANH: Le Duc Quyen

1. CAI DAT (chi can lam 1 lan):
   pip install streamlit plotly openpyxl python-pptx xlsxwriter

2. CHAY CHUONG TRINH:
   cd ~/MYTEL/ayy-netops
   streamlit run app.py

   Trinh duyet se tu dong mo tai: http://localhost:8501

3. DU LIEU:
   - Dat cac file Excel vao thu muc ~/MYTEL/
   - File Cellhr Daily review*.xlsx (du lieu Cell*h)
   - File SUMMARY_AYY Database.xlsx (co so du lieu tram, nhan su)

4. LUU DU LIEU VAO DATABASE:
   - Moi khi them file Cellhr Daily moi, click "Luu vao Database"
   - Du lieu se tu dong luu vao SQLite de tra cuu lich su
   - File DB: ~/MYTEL/ayy_netops.db

5. CAC TRANG:
   - Tong quan (Dashboard): KPI, bieu do xu huong, phan bo nguyen nhan
   - Phan tich Cell*h: Bieu do cot chong, heatmap, chi tiet tram
   - Quan ly Nguon dien: TCO power, Mytel power, tong quan
   - Truyen dan: Su co, tuyen lap, chi tiet
   - Quan ly Tram: CSDL tram, chi tiet, tram dac biet
   - Nhan su: Theo doi, tai cong viec
   - Bao cao: Xuat PPTX, Excel, bao cao tu DB
   - Trung tam Chi huy: SLA gauge, hieu suat doi
   - Canh bao: Vuot nguong, loi lap, bat thuong
   - Theo doi Hanh dong: De xuat tu dong, them/xoa hanh dong

6. CHUYEN NGON NGU:
   - Click nut tren sidebar de chuyen EN <-> VI
