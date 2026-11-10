import pandas as pd
import geopandas as gpd
from pathlib import Path

# =========================
# 0. 경로
# =========================
base_path = Path(r"D:\data\data_clim")

excel_path = base_path / "AR6_SSP126_5ENSMN_skorea_WS_sgg261_monthly_2021_2100.xlsx"
shp_path = base_path / "bnd_sigungu_00_2024_2Q/bnd_sigungu_00_2024_2Q.shp"

# =========================
# 1. Excel 로드
# =========================
raw = pd.read_excel(excel_path, header=None)

# 구조
# row0: Column명 (Column1, Column2...)
# row1: 코드 (1101000000)
# row2: 시도
# row3: 시군구

code_row = raw.iloc[1, 1:]
sido_row = raw.iloc[2, 1:]
sigungu_row = raw.iloc[3, 1:]

meta = pd.DataFrame({
    "COL": raw.iloc[0, 1:],         # Column2
    "SIGUNGU_CD_excel": code_row.values,
    "SIDO_excel": sido_row.values,
    "SIGUNGU_NM_excel": sigungu_row.values
})

meta["SIGUNGU_CD_excel"] = meta["SIGUNGU_CD_excel"].astype(str)

# 앞 2자리 코드
meta["SIDO_CD"] = meta["SIGUNGU_CD_excel"].str[:2]

# 이름 KEY
meta["KEY"] = meta["SIDO_excel"].astype(str) + "_" + meta["SIGUNGU_NM_excel"].astype(str)

# =========================
# 2. SHP 로드
# =========================
gdf = gpd.read_file(shp_path, encoding="utf-8")

gdf["SIGUNGU_CD"] = gdf["SIGUNGU_CD"].astype(str)
gdf["SIGUNGU_NM"] = gdf["SIGUNGU_NM"].astype(str)

gdf.drop(columns="geometry").to_csv(
    "output_shp.csv",
    index=False,
    encoding="utf-8-sig"
)
# =========================
# 3. 세종 처리
# =========================
gdf.loc[gdf["SIGUNGU_NM"].str.contains("세종"), "SIGUNGU_NM"] = "세종특별자치시"

# =========================
# 4. SHP 시도코드 생성 (앞 2자리)
# =========================
gdf["SIDO_CD"] = gdf["SIGUNGU_CD"].str[:2]

# =========================
# 5. SHP 이름 KEY
# =========================
# 시도명 매핑
SIDO_MAP = {
    "11": "서울특별시",
    "21": "부산광역시",
    "22": "대구광역시",
    "23": "인천광역시",
    "24": "광주광역시",
    "25": "대전광역시",
    "26": "울산광역시",
    "29": "세종특별자치시",
    "31": "경기도",
    "32": "강원특별자치도",
    "33": "충청북도",
    "34": "충청남도",
    "35": "전라북도",
    "36": "전라남도",
    "37": "경상북도",
    "38": "경상남도",
    "39": "제주특별자치도"
}

gdf["SIDO"] = gdf["SIDO_CD"].map(SIDO_MAP)

gdf["KEY"] = gdf["SIDO"] + "_" + gdf["SIGUNGU_NM"]

# =========================
# 6.  코드 + 이름 동시 매칭
# =========================
merged = meta.merge(
    gdf,
    on=["SIDO_CD", "KEY"],   
    how="left"
)

merged["match_flag"] = merged["geometry"].notna()

# =========================
# 7. 결과 출력
# =========================
print("\n====================")
print("매칭 결과")
print("====================")
print("전체:", len(merged))
print("성공:", merged["match_flag"].sum())
print("실패:", (~merged["match_flag"]).sum())

# =========================
# 8. 요청한 형태 출력
# =========================
view = merged[[
    "SIGUNGU_CD",           # SHP 코드
    "SIGUNGU_NM",           # SHP 한글
    "SIGUNGU_CD_excel",     # Excel 코드
    "SIDO_excel",           # Excel 시도
    "SIGUNGU_NM_excel",     # Excel 시군구
    "match_flag"
]].drop_duplicates()

print("\n====================")
print(" 최종 결과 (요청형식)")
print("====================")
print(view.head(50))

# =========================
# 9. 실패 확인
# =========================
fail = view[view["match_flag"] == False]

print("\n====================")
print(" 실패")
print("====================")
print(fail)

print("\nDONE")


# =========================
# 10. 엑셀 저장
# =========================
output_path = base_path / "matching_result.xlsx"

# 저장용 컬럼 정리
export_df = merged[[
    "SIGUNGU_CD",           # SHP 코드
    "SIGUNGU_NM",           # SHP 한글
    "SIGUNGU_CD_excel",     # Excel 코드
    "SIDO_excel",           # Excel 시도
    "SIGUNGU_NM_excel",     # Excel 시군구
    "match_flag"
]].drop_duplicates()

# 저장
#export_df.to_excel(output_path, index=False)

print("\n====================")
print("엑셀 저장 완료")
print("====================")
print(output_path)