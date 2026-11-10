# -*- coding: utf-8 -*-

"""
3MW 풍력 터빈 제원 기반 시도별 잠재발전량 집계 및 월별 시각화 차트 생성

입력:
    1. 격자별 월평균 풍력 데이터 (.npz):
       - output/wind_grid/2026_02.npz ~ 2026_08.npz
    2. 공통 지역 캐시 파일:
       - output/region/region_index.npy
       - output/region/region_name.csv

출력:
    1. 시도별 잠재발전량 DB 집계 데이터 (CSV):
       - output/wind_generation/wind_generation_sido.csv
    2. 월별 시도 잠재발전량 시각화 그래프 (PNG):
       - output/charts/wind_generation_2026_02.png ~ wind_generation_2026_08.png
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =====================================================
# 0. 한글 폰트 및 마이너스 깨짐 설정
# =====================================================

plt.rcParams['font.family'] = 'NanumGothic'  # 시스템 설치 폰트에 맞춰 변경 가능
plt.rcParams['axes.unicode_minus'] = False


# =====================================================
# 1. PATH 및 기본 설정
# =====================================================

BASE_DIR = "/data/jyy/S82_2025/KIML_monthly"

# 입력 경로 (.npz 파일 및 캐시 파일 위치)
GRID_DIR = os.path.join(BASE_DIR, "output", "wind_grid")
REGION_DIR = os.path.join(BASE_DIR, "output", "region")

# 출력 경로 (CSV 및 차트 저장 위치)
OUT_DIR = os.path.join(BASE_DIR, "output", "wind_generation")
CHART_DIR = os.path.join(BASE_DIR, "output", "charts")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

# 3MW 터빈 정격 용량
HUB_HEIGHT = 80
P_RATED_KW = 3000.0  # 3MW (3000 kW)

# 시도별 [stn_id, capacity_kW] 매핑
sido_info = {
    '서울': {'stn_id': 11, 'capacity': 105},
    '부산': {'stn_id': 21, 'capacity': 45},
    '대구': {'stn_id': 22, 'capacity': 11563},
    '인천': {'stn_id': 23, 'capacity': 49138},
    '광주': {'stn_id': 24, 'capacity': 4},
    '대전': {'stn_id': 25, 'capacity': 200},
    '울산': {'stn_id': 26, 'capacity': 1660},
    '세종': {'stn_id': 29, 'capacity': 0},
    '경기': {'stn_id': 31, 'capacity': 5311},
    '강원': {'stn_id': 32, 'capacity': 529131},
    '충북': {'stn_id': 33, 'capacity': 38},
    '충남': {'stn_id': 34, 'capacity': 2095},
    '전북': {'stn_id': 35, 'capacity': 82530},
    '전남': {'stn_id': 36, 'capacity': 456482},
    '경북': {'stn_id': 37, 'capacity': 515775},
    '경남': {'stn_id': 38, 'capacity': 87021},
    '제주': {'stn_id': 39, 'capacity': 423623}
}


# =====================================================
# 2. 캐시 데이터 로드
# =====================================================

INDEX_FILE = os.path.join(REGION_DIR, "region_index.npy")
NAME_FILE = os.path.join(REGION_DIR, "region_name.csv")

if not os.path.exists(INDEX_FILE) or not os.path.exists(NAME_FILE):
    raise FileNotFoundError("지역 캐시 파일이 없습니다. make_region_index.py를 확인해 주세요!")

region_index = np.load(INDEX_FILE)
df_region_names = pd.read_csv(NAME_FILE)


# =====================================================
# 3. .npz 파일 로드 및 시도별 잠재발전량 연산
# =====================================================

results = []
idkey = 1

# GRID_DIR에서 2026_02.npz ~ 2026_08.npz 검색
grid_files = sorted([f for f in os.listdir(GRID_DIR) if f.endswith(".npz")])

print(f"FOUND {len(grid_files)} NPZ FILES FOR CALCULATION.\n")

for fname in grid_files:
    print(f"PROCESSING: {fname}")
    
    # 파일명 해석 (예: 2026_02.npz -> year: 2026, month: 2)
    ym = fname.replace(".npz", "").split("_")
    year = int(ym[0])
    month = int(ym[1])

    # .npz 불러오기
    npz_data = np.load(os.path.join(GRID_DIR, fname))
    flat_density = npz_data["density"].ravel()
    flat_e_turbine = npz_data["e_turbine"].ravel()

    for _, row in df_region_names.iterrows():
        region_id = row["region_id"]
        sido = row["sido"]

        if sido not in sido_info:
            continue

        sido_mask = (region_index == region_id)
        
        vals_density = flat_density[sido_mask]
        vals_density = vals_density[~np.isnan(vals_density)]

        vals_e_turbine = flat_e_turbine[sido_mask]
        vals_e_turbine = vals_e_turbine[~np.isnan(vals_e_turbine)]

        if len(vals_density) == 0 or len(vals_e_turbine) == 0:
            continue

        mean_density = float(np.mean(vals_density))
        mean_e_turbine = float(np.mean(vals_e_turbine))  # 시도별 3MW 터빈 1기일일 발전량 (kWh)

        cap_kw = sido_info[sido]['capacity']
        stn_id = sido_info[sido]['stn_id']

        # Potential = (Capacity_region / 3000kW) * E_turbine / 1000  [MWh/day]
        turbine_count = cap_kw / P_RATED_KW
        gen_mwh_day = (turbine_count * mean_e_turbine) / 1000.0

        results.append({
            "IDKEY": idkey,
            "year": year,
            "month": month,
            "stn_id": stn_id,
            "sido": sido,
            "hub_height_m": HUB_HEIGHT,
            "energy_density_kWh_m2_day": round(mean_density, 4),
            "capacity_kW": cap_kw,
            "generation_MWh_day": round(gen_mwh_day, 3)
        })
        idkey += 1


# =====================================================
# 4. CSV 저장 (DB 스키마 맞춤)
# =====================================================

df = pd.DataFrame(results)

# DB 입력용 CSV 생성 (시도명 필드 제외)
df_db = df.drop(columns=["sido"])
outfile_csv = os.path.join(OUT_DIR, "wind_generation_sido.csv")
df_db.to_csv(outfile_csv, index=False, encoding="utf-8-sig")
print("\nSAVED CSV:", outfile_csv)


# =====================================================
# 5. 월별 차트 이미지 저장
# =====================================================

print("\nGENERATING MONTHLY CHARTS...")

for mm in df['month'].unique():
    df_month = df[df['month'] == mm].sort_values(by="generation_MWh_day", ascending=False)
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(df_month['sido'], df_month['generation_MWh_day'], color='skyblue', edgecolor='navy')
    
    plt.title(f"2026년 {mm:02d}월 시도별 풍력 일일 잠재발전량 (MWh/day)", fontsize=16, fontweight='bold', pad=15)
    plt.xlabel("행정구역 (시도)", fontsize=12, labelpad=10)
    plt.ylabel("잠재발전량 (MWh/day)", fontsize=12, labelpad=10)
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # 막대 상단 수치 표출
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.text(
                bar.get_x() + bar.get_width() / 2.0, 
                height, 
                f"{height:,.1f}", 
                ha='center', 
                va='bottom', 
                fontsize=9
            )

    plt.tight_layout()
    chart_path = os.path.join(CHART_DIR, f"wind_generation_2026_{mm:02d}.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    
    print(f"SAVE CHART: {chart_path}")

print("\n==========================================")
print("ALL PROCESSES AND CHART SAVINGS COMPLETED!")
print("==========================================")