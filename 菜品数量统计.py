import streamlit as st
import pandas as pd
import json

def extract_core_name(name: str, spec: str = "") -> str:
    if not isinstance(name, str):
        return name
    if name == "加面":
        if "宽面" in spec:
            return "宽面"
        elif "细面" in spec:
            return "细面"
        else:
            return "面"
    if name.startswith("加"):
        core = name[1:]
        if core in ["宽面", "细面"]:
            return core
        return core
    mapping = {
        "宫保鸡丁": "鸡丁", "宫保板筋": "板筋", "宫保猪肝": "猪肝",
        "宫保牛肉": "牛肉", "宫保鸡胗花": "鸡胗花", "宫保鱿鱼": "鱿鱼",
        "宫保大虾": "大虾", "泡椒板筋": "板筋", "泡椒鸡杂": "鸡杂",
        "番茄炒蛋": "番茄炒蛋", "怪噜炒面": "炒面", "卤鸡蛋": "卤蛋",
        "卤豆腐": "卤豆腐", "香煎大排": "大排", "正大蜂蜜水": "蜂蜜水",
        "正大所以所以润矿泉水": "矿泉水", "打包盒": "打包盒",
        "加宽面": "宽面", "加细面": "细面", "打包必选": "打包必选",
        "单加米饭(仅无主菜时选择)": "米饭",
    }
    return mapping.get(name, name.strip())

def process_row(row):
    dish_name = row["菜品名称"]
    qty = row["菜品数量"]
    status = row["菜品状态"]
    spec = row["规格名称"] if pd.notna(row["规格名称"]) else ""
    practices = row["做法"]
    if isinstance(practices, str):
        try:
            practices = json.loads(practices) if practices and practices != "[]" else []
        except:
            practices = []
    elif not isinstance(practices, list):
        practices = []
    sign = 1 if status == "正常菜品" else -1
    delta = sign * qty
    dish_delta = {dish_name: delta}
    topping_delta = {}
    spec_delta = {}
    merged_dt_delta = {extract_core_name(dish_name, spec): delta}
    merged_spec_delta = {}
    for prac in practices:
        if not isinstance(prac, dict):
            continue
        name = prac.get("name", "")
        if not name:
            continue
        if name == "加面":
            if "宽面" in spec:
                name = "加宽面"
            elif "细面" in spec:
                name = "加细面"
        topping_delta[name] = topping_delta.get(name, 0) + delta
        core = extract_core_name(name, spec)
        merged_dt_delta[core] = merged_dt_delta.get(core, 0) + delta
    if spec and spec != "":
        spec_delta[spec] = delta
        merged_spec_delta[extract_core_name(spec, spec)] = delta
    for name, val in topping_delta.items():
        if name in ["加宽面", "加细面"]:
            core = extract_core_name(name, spec)
            merged_spec_delta[core] = merged_spec_delta.get(core, 0) + val
    return dish_delta, topping_delta, spec_delta, merged_dt_delta, merged_spec_delta

def analyze_excel(df):
    total_dish, total_topping, total_spec = {}, {}, {}
    total_merged_dt, total_merged_spec = {}, {}
    for _, row in df.iterrows():
        d1, d2, d3, d4, d5 = process_row(row)
        for k, v in d1.items(): total_dish[k] = total_dish.get(k, 0) + v
        for k, v in d2.items(): total_topping[k] = total_topping.get(k, 0) + v
        for k, v in d3.items(): total_spec[k] = total_spec.get(k, 0) + v
        for k, v in d4.items(): total_merged_dt[k] = total_merged_dt.get(k, 0) + v
        for k, v in d5.items(): total_merged_spec[k] = total_merged_spec.get(k, 0) + v
    df_dish = pd.DataFrame(total_dish.items(), columns=["菜品名称", "净份数"]).sort_values("净份数", ascending=False)
    df_topping = pd.DataFrame(total_topping.items(), columns=["做法加项", "净份数"]).sort_values("净份数", ascending=False)
    df_spec = pd.DataFrame(total_spec.items(), columns=["规格名称", "净份数"]).sort_values("净份数", ascending=False)
    df_merged_dt = pd.DataFrame(total_merged_dt.items(), columns=["合并类（菜品+加项）", "净份数"]).sort_values("净份数", ascending=False)
    df_merged_spec = pd.DataFrame(total_merged_spec.items(), columns=["合并类（规格+加面）", "净份数"]).sort_values("净份数", ascending=False)
    return df_dish, df_topping, df_spec, df_merged_dt, df_merged_spec

st.set_page_config(page_title="订单菜品统计分析", layout="wide")
st.title("📊 订单菜品统计分析")
st.markdown("上传 **Excel (.xlsx/.xls)** 或 **CSV** 文件（需包含列：`菜品名称`、`菜品数量`、`规格名称`、`做法`、`菜品状态`）")

uploaded_file = st.file_uploader("选择文件", type=["xlsx", "xls", "csv"])
if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    try:
        if ext == "csv":
            df = pd.read_csv(uploaded_file)
        elif ext == "xls":
            df = pd.read_excel(uploaded_file, engine="xlrd")
        else:  # xlsx
            df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as e:
        st.error(f"❌ 文件读取失败：{e}")
        st.info("请确认文件是真正的 Excel 文件（.xlsx 或 .xls），而不是改名后的文本文件。\n\n"
                "👉 如果您只有表格文本，请打开 Excel → 粘贴数据 → 另存为 .xlsx 后再上传。")
        st.stop()
    
    required = ["菜品名称", "菜品数量", "规格名称", "做法", "菜品状态"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"缺少列：{missing}")
        st.stop()
    
    df["菜品数量"] = pd.to_numeric(df["菜品数量"], errors="coerce").fillna(1).astype(int)
    df["菜品状态"] = df["菜品状态"].astype(str)
    
    with st.spinner("分析中..."):
        dish_df, top_df, spec_df, merged_dt, merged_spec = analyze_excel(df)
    st.success("完成")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["菜品份数", "做法加项", "规格份数", "合并(菜品+加项)", "合并(规格+加面)"])
    with tab1:
        st.dataframe(dish_df)
        st.download_button("下载 CSV", dish_df.to_csv(index=False), "dish.csv")
    with tab2:
        st.dataframe(top_df)
        st.download_button("下载 CSV", top_df.to_csv(index=False), "topping.csv")
    with tab3:
        st.dataframe(spec_df)
        st.download_button("下载 CSV", spec_df.to_csv(index=False), "spec.csv")
    with tab4:
        st.dataframe(merged_dt)
        st.download_button("下载 CSV", merged_dt.to_csv(index=False), "merged_dt.csv")
    with tab5:
        st.dataframe(merged_spec)
        st.download_button("下载 CSV", merged_spec.to_csv(index=False), "merged_spec.csv")