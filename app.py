import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 設定網頁
st.set_page_config(page_title="英國工資歷史紀錄 App", layout="centered")
st.title("🇬🇧 英國每週工資歷史紀錄與估算")

DB_FILE = "salary_history.csv"

# --- 1. 定義 2020-2026 歷史稅務大數據 (以每週 Weekly 計算) ---
# 註：英國稅年度由 4 月 6 日開始。NI 稅率在 2022 與 2024 年中有過特別調整，此處取最核心或年度主要稅率。
def get_uk_tax_rules(date_obj):
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    
    # 將日期轉換成「稅務年度」
    # 如果是 4 月 6 日前，屬於前一個稅年度
    if (month < 4) or (month == 4 and day < 6):
        tax_year = year - 1
    else:
        tax_year = year

    # 預設參數 (若超出範圍則用 2026 最新)
    rules = {
        "year_label": f"{tax_year}/{str(tax_year+1)[2:]}",
        "ni_threshold": 242.0,
        "ni_rate": 0.08,
        "pension_threshold": 120.0
    }
    
    if tax_year <= 2020:
        rules.update({"year_label": "2020/21", "ni_threshold": 183.0, "ni_rate": 0.12, "pension_threshold": 120.0})
    elif tax_year == 2021:
        rules.update({"year_label": "2021/22", "ni_threshold": 184.0, "ni_rate": 0.12, "pension_threshold": 120.0})
    elif tax_year == 2022:
        # 2022年 7月起 NI 門檻大幅調高至與所得稅同步
        if (month > 7) or (month == 7 and day >= 6):
            rules.update({"year_label": "2022/23 (Late)", "ni_threshold": 242.0, "ni_rate": 0.12, "pension_threshold": 120.0})
        else:
            rules.update({"year_label": "2022/23 (Early)", "ni_threshold": 190.0, "ni_rate": 0.1325, "pension_threshold": 120.0}) # 曾短暫有 1.25% 醫療附加稅
    elif tax_year == 2023:
        # 2024年1月起 NI 員工稅率由 12% 減至 10%
        if (month == 1 and day >= 6) or month > 1:
            rules.update({"year_label": "2023/24 (Late)", "ni_threshold": 242.0, "ni_rate": 0.10, "pension_threshold": 120.0})
        else:
            rules.update({"year_label": "2023/24 (Early)", "ni_threshold": 242.0, "ni_rate": 0.12, "pension_threshold": 120.0})
    elif tax_year == 2024:
        # 2024年4月起 再減至 8%
        rules.update({"year_label": "2024/25", "ni_threshold": 242.0, "ni_rate": 0.08, "pension_threshold": 120.0})
    elif tax_year == 2025:
        rules.update({"year_label": "2025/26", "ni_threshold": 242.0, "ni_rate": 0.08, "pension_threshold": 120.0})
    # 2026 年或以後
    else:
        rules.update({"year_label": f"{tax_year}/{str(tax_year+1)[2:]}", "ni_threshold": 242.0, "ni_rate": 0.08, "pension_threshold": 120.0})
        
    return rules

# --- 2. 讀取 / 初始化 CSV 本地資料庫 ---
columns_list = ["Date", "Year", "Month", "Gross Pay (£)", "PAYE Tax (£)", "NI (£)", "Pension EE (£)", "Pension ER (£)", "Net Pay (£)"]

if os.path.exists(DB_FILE):
    try:
        df_all = pd.read_csv(DB_FILE)
        # 確保格式正確
        for col in columns_list:
            if col not in df_all.columns:
                df_all[col] = 0.0 if col != "Date" and col != "Year" and col != "Month" else ""
    except:
        df_all = pd.DataFrame(columns=columns_list)
else:
    df_all = pd.DataFrame(columns=columns_list)

# --- 3. 新增紀錄表單 ---
st.header("➕ 新增薪資紀錄")

with st.form("salary_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("出糧日期 (Date)", value=datetime.today())
        gross_pay = st.number_input("稅前人工 (Gross Pay £)", min_value=0.0, step=10.0, value=500.0)
    with col2:
        paye_tax = st.number_input("預扣入息稅 (PAYE Tax £)", min_value=0.0, step=5.0, value=0.0)
    
    # 根據輸入日期獲取歷史稅率
    current_rules = get_uk_tax_rules(date_input)
    
    # 計算歷史自動值
    calc_ni = max(0.0, (gross_pay - current_rules["ni_threshold"]) * current_rules["ni_rate"]) if gross_pay > current_rules["ni_threshold"] else 0.0
    calc_pension_ee = max(0.0, (gross_pay - current_rules["pension_threshold"]) * 0.05) if gross_pay > current_rules["pension_threshold"] else 0.0
    calc_pension_er = max(0.0, (gross_pay - current_rules["pension_threshold"]) * 0.03) if gross_pay > current_rules["pension_threshold"] else 0.0
    
    st.info(f"📜 偵測至屬英國 **{current_rules['year_label']}** 稅期規則：\n"
            f"免稅額 NI 起點 £{current_rules['ni_threshold']} (稅率 {current_rules['ni_rate']*100}%) | Pension 起點 £{current_rules['pension_threshold']}\n"
            f"💡 系統自動估算：NI ~£{calc_ni:.2f} | 員工 Pension ~£{calc_pension_ee:.2f}")
    
    # 用戶確認欄
    final_ni = st.number_input("確認實際扣除 NI (£)", min_value=0.0, value=round(calc_ni, 2))
    final_pension_ee = st.number_input("確認實際員工 Pension (£)", min_value=0.0, value=round(calc_pension_ee, 2))
    final_pension_er = st.number_input("確認實際僱主 Pension (£)", min_value=0.0, value=round(calc_pension_er, 2))
    
    final_net_pay = gross_pay - paye_tax - final_ni - final_pension_ee
    
    submit_btn = st.form_submit_button("💾 儲存並寫入檔案")
    
    if submit_btn:
        new_row = {
            "Date": date_input.strftime("%Y-%m-%d"),
            "Year": str(date_input.year),
            "Month": f"{date_input.month:02d}", # 格式化成 01, 02 方便排列
            "Gross Pay (£)": round(gross_pay, 2),
            "PAYE Tax (£)": round(paye_tax, 2),
            "NI (£)": round(final_ni, 2),
            "Pension EE (£)": round(final_pension_ee, 2),
            "Pension ER (£)": round(final_pension_er, 2),
            "Net Pay (£)": round(final_net_pay, 2)
        }
        
        # 附加至 DataFrame 並儲存
        df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
        df_all.to_csv(DB_FILE, index=False)
        st.success(f"🎉 成功寫入 {DB_FILE}！")
        st.rerun() # 重新整理畫面顯示最新數據

st.markdown("---")

# --- 4. 長期數據歷史篩選區 ---
st.header("🔍 歷史數據篩選與統計")

if not df_all.empty:
    # 確保資料型態正確以便篩選
    df_all["Year"] = df_all["Year"].astype(str)
    df_all["Month"] = df_all["Month"].astype(str)
    
    # 建立篩選器排版
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        # 年份篩選
        available_years = sorted(list(df_all["Year"].unique()), reverse=True)
        # 加入全選功能
        year_options = ["全部年份"] + available_years
        selected_year = st.selectbox("📅 選擇年份", options=year_options)
        
    with filter_col2:
        # 根據選定的年份來縮小月份選擇，或是直接顯示全部
        if selected_year != "全部年份":
            available_months = sorted(list(df_all[df_all["Year"] == selected_year]["Month"].unique()))
        else:
            available_months = sorted(list(df_all["Month"].unique()))
        month_options = ["全部月份"] + available_months
        selected_month = st.selectbox("📆 選擇月份", options=month_options)
        
    # --- 執行篩選邏輯 ---
    filtered_df = df_all.copy()
    if selected_year != "全部年份":
        filtered_df = filtered_df[filtered_df["Year"] == selected_year]
    if selected_month != "全部月份":
        filtered_df = filtered_df[filtered_df["Month"] == selected_month]
        
    # --- 顯示篩選後的數據與統計 ---
    if not filtered_df.empty:
        total_gross = filtered_df["Gross Pay (£)"].sum()
        total_net = filtered_df["Net Pay (£)"].sum()
        total_ni = filtered_df["NI (£)"].sum()
        total_pension_ee = filtered_df["Pension EE (£)"].sum()
        
        # 數據卡片
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("範圍總 Gross", f"£{total_gross:,.2f}")
        m2.metric("範圍總 Net Pay", f"£{total_net:,.2f}")
        m3.metric("範圍總 NI", f"£{total_ni:,.2f}")
        m4.metric("範圍自供 Pension", f"£{total_pension_ee:,.2f}")
        
        # 顯示歷史表格 (按最新日期排序)
        st.dataframe(filtered_df.sort_values(by="Date", ascending=False), use_container_width=True, index=False)
    else:
        st.warning("⚠️ 該篩選範圍內沒有找到任何紀錄。")
else:
    st.info("👋 歡迎使用！目前尚未有任何歷史紀錄，請於上方輸入你的第一筆糧單資料。")
