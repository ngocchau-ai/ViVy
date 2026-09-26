@echo off
:: Script chuyển đổi Junction 91s_Vivy thành thư mục vật lý thực thụ (chạy khi tắt IDE)
cd /d D:\
if exist "D:\91s_Vivy" (
    echo [1/3] Xoa lien ket Junction D:\91s_Vivy...
    rmdir "D:\91s_Vivy"
)
if exist "D:\91s- Tái cấu trúc lân thứ 4" (
    echo [2/3] Bo thuoc tinh an cua thu muc goc...
    attrib -h "D:\91s- Tái cấu trúc lân thứ 4"
    echo [3/3] Doi ten D:\91s- Tái cấu trúc lân thứ 4 thanh D:\91s_Vivy...
    ren "D:\91s- Tái cấu trúc lân thứ 4" "91s_Vivy"
)
echo.
echo =======================================================
echo DA HOAN TAT CHUYEN DOI!
echo D:\91s_Vivy hien tai la thu muc vat ly chinh danh 100%.
echo =======================================================
pause
