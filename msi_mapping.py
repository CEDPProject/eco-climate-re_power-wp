import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# =========================================================
# 사용자 설정 영역
# =========================================================

PROJECT_ROOT = Path.cwd()

DATA_PATH = PROJECT_ROOT / "data"
FIG_PATH = PROJECT_ROOT / "figure"

FIG_PATH.mkdir(exist_ok=True)

# 입력 파일
CLIMATE_FILE = DATA_PATH / "climate_with_SPEI.csv"
MATCH_FILE = DATA_PATH / "matching_result.xlsx"
SHP_FILE = (
    DATA_PATH
    / "bnd_sigungu_00_2024_2Q"
    / "bnd_sigungu_00_2024_2Q.shp"
)

# 출력 파일
MSI_OUTPUT = DATA_PATH / "climate_with_MultiStressIndex.csv"

# =========================================================
# 함수 정의
# =========================================================

def zscore(x):
    """표준점수 계산"""
    std = x.std()
    if std == 0:
        return np.zeros(len(x))
    return (x - x.mean()) / std


def clean_code(series, length=5):
    """행정구역 코드 정리"""
    return (
        series.astype(str)
        .str.replace(".0", "", regex=False)
        .str.zfill(length)
    )


# =========================================================
# STEP 1. 기후 데이터 불러오기
# =========================================================

print("\n===== STEP 1 : LOAD CLIMATE DATA =====")

df = pd.read_csv(CLIMATE_FILE)

df["year_month"] = pd.to_datetime(
    df["year_month"],
    errors="coerce"
)

# =========================================================
# STEP 2. MSI 계산
# =========================================================

print("\n===== STEP 2 : CALCULATE MSI =====")

spei_col = "SPEI_3" if "SPEI_3" in df.columns else "SPEI"

df["SPEI_z"] = zscore(df[spei_col])
df["TAMAX_z"] = zscore(df["TAMAX"])
df["WS_z"] = zscore(df["WS"])
df["SI_z"] = zscore(df["SI"])

# Multi-Stress Index
df["MSI"] = (
    -df["SPEI_z"]
    + df["TAMAX_z"]
    + df["WS_z"]
    + df["SI_z"]
)

print("\nMSI Summary")
print(df["MSI"].describe())

# =========================================================
# STEP 3. MSI 저장
# =========================================================

print("\n===== STEP 3 : SAVE MSI =====")

df.to_csv(MSI_OUTPUT, index=False)

print(f"Saved: {MSI_OUTPUT}")

# =========================================================
# STEP 4. GIS 데이터 불러오기
# =========================================================

print("\n===== STEP 4 : LOAD GIS DATA =====")

gdf = gpd.read_file(SHP_FILE)
match = pd.read_excel(MATCH_FILE)

# =========================================================
# STEP 5. 코드 정리
# =========================================================

print("\n===== STEP 5 : CLEAN KEYS =====")

gdf["SIGUNGU_CD"] = clean_code(
    gdf["SIGUNGU_CD"],
    length=5
)

match["SIGUNGU_CD"] = clean_code(
    match["SIGUNGU_CD"],
    length=5
)

match["region_code"] = (
    match["region_code"]
    .astype(str)
    .str.strip()
)

match["match_flag"] = (
    match["match_flag"]
    .astype(str)
    .str.upper()
)

df["region_code"] = (
    df["region_code"]
    .astype(str)
    .str.strip()
)

match_true = match[
    match["match_flag"] == "TRUE"
].copy()

# =========================================================
# STEP 6. 지도 생성
# =========================================================

print("\n===== STEP 6 : CREATE MAPS =====")

YEARS = list(range(2025, 2101, 10))
MONTHS = ["01", "02", "03", "04", "05", "07", "10"]  #날짜 임의로 변경 가능

for year in YEARS:

    for month in MONTHS:

        date_str = f"{year}-{month}-01"

        print(f"Processing: {date_str}")

        # 해당 시점 MSI 추출
        msi_sub = df[
            df["year_month"] == date_str
        ][["region_code", "MSI"]]

        # 행정구역 매칭
        match_msi = match_true.merge(
            msi_sub,
            on="region_code",
            how="left"
        )

        # 공간 데이터 결합
        gdf_plot = gdf.merge(
            match_msi[
                ["SIGUNGU_CD", "MSI"]
            ],
            on="SIGUNGU_CD",
            how="left"
        )

        # 지도 작성
        fig, ax = plt.subplots(
            figsize=(12, 12)
        )

        gdf_plot.plot(
            column="MSI",
            cmap="RdYlBu_r",
            vmin=-5,
            vmax=5,
            legend=True,
            linewidth=0.3,
            edgecolor="black",
            ax=ax,
            missing_kwds={
                "color": "lightgrey"
            },
            legend_kwds={
                "shrink": 0.5,
                "aspect": 20,
                "pad": 0.02,
                "ticks": np.arange(-5, 6, 1)
            }
        )

        ax.set_title(
            f"Multi-Stress Index (MSI)\n{date_str}",
            fontsize=16
        )

        ax.axis("off")

        plt.tight_layout()

        output_png = (
            FIG_PATH
            / f"MSI_{year}_{month}.png"
        )

        plt.savefig(
            output_png,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close()

        print(f"Saved: {output_png}")

# =========================================================
# 종료
# =========================================================

print("\n===================================")
print("MSI Calculation and Mapping Complete")
print("===================================")