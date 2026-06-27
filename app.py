"""
Excel/CSV/Parquet SQL Workbench - High-Performance Local Disk Version
Optimized for zero-setup local machine data streaming via direct file paths.
"""

import streamlit as st
import duckdb
import pandas as pd
import tempfile
import os
import string
import time
import io
from datetime import datetime
from typing import Tuple
from streamlit_ace import st_ace 

# ==========================================================
# Configuration & Performance Tuning
# ==========================================================
st.set_page_config(page_title="Local SQL Workbench", layout="wide")

if "con" not in st.session_state:
    con = duckdb.connect()
    con.execute("SET memory_limit='6GB';") 
    con.execute("SET max_memory='6GB';")
    st.session_state.con = con
else:
    con = st.session_state.con

TEMP_DIR = os.path.join(tempfile.gettempdir(), "excel_sql_uploads")

if "datasets" not in st.session_state:
    st.session_state.datasets = {}
if "table_counter" not in st.session_state:
    st.session_state.table_counter = 0
if "query_result" not in st.session_state:
    st.session_state.query_result = None
if "query_time" not in st.session_state:
    st.session_state.query_time = None
if "query_row_count" not in st.session_state:
    st.session_state.query_row_count = None
if "query_history" not in st.session_state:
    st.session_state.query_history = []

# ==========================================================
# Utility Functions
# ==========================================================

def generate_table_name(index: int) -> str:
    alphabet = string.ascii_uppercase
    name = ""
    while True:
        name = alphabet[index % 26] + name
        index = index // 26 - 1
        if index < 0:
            break
    return f"data{name}"

def format_file_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def get_table_stats(table_name: str) -> dict:
    try:
        res = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        row_count = res[0] if res is not None else 0
        schema = con.execute(f"DESCRIBE {table_name}").fetchdf()
        return {"rows": row_count, "columns": len(schema), "schema": schema}
    except Exception:
        return None

def optimize_excel_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include=['int']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
    for col in df.select_dtypes(include=['float']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    return df

def register_file(file_name: str, file_path: str, file_size: int) -> Tuple[bool, list]:
    lower = file_name.lower()
    registered_tables = []
    try:
        if lower.endswith(".csv"):
            table_name = generate_table_name(st.session_state.table_counter)
            st.session_state.table_counter += 1
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{file_path}', parallel=true)")
            st.session_state.datasets[table_name] = {"filename": file_name, "path": file_path, "uploaded_at": datetime.now(), "size": file_size}
            registered_tables.append(table_name)
        elif lower.endswith(".parquet"):
            table_name = generate_table_name(st.session_state.table_counter)
            st.session_state.table_counter += 1
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{file_path}')")
            st.session_state.datasets[table_name] = {"filename": file_name, "path": file_path, "uploaded_at": datetime.now(), "size": file_size}
            registered_tables.append(table_name)
        elif lower.endswith((".xlsx", ".xls")):
            try:
                xl = pd.ExcelFile(file_path, engine='calamine')
                for sheet in xl.sheet_names:
                    table_name = f"{generate_table_name(st.session_state.table_counter)}_{sheet.replace(' ', '_')}"
                    st.session_state.table_counter += 1
                    df = pd.read_excel(xl, sheet_name=sheet, engine='calamine')
                    df = optimize_excel_dataframe(df)
                    con.register(table_name, df)
                    st.session_state.datasets[table_name] = {"filename": f"{file_name} ({sheet})", "path": file_path, "uploaded_at": datetime.now(), "size": file_size}
                    registered_tables.append(table_name)
            except Exception:
                xl = pd.ExcelFile(file_path)
                for sheet in xl.sheet_names:
                    table_name = f"{generate_table_name(st.session_state.table_counter)}_{sheet.replace(' ', '_')}"
                    st.session_state.table_counter += 1
                    first_chunk = True
                    for chunk in pd.read_excel(xl, sheet_name=sheet, chunksize=20000, engine='openpyxl'):
                        if first_chunk:
                            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM chunk WHERE 1=0")
                            first_chunk = False
                        con.append(table_name, chunk)
                    st.session_state.datasets[table_name] = {"filename": f"{file_name} ({sheet})", "path": file_path, "uploaded_at": datetime.now(), "size": file_size}
                    registered_tables.append(table_name)
        return True, registered_tables
    except Exception as e:
        return False, [str(e)]

# ==========================================================
# Sidebar UI & Dataset Management
# ==========================================================
with st.sidebar:
    st.header("⚙️ Workbench Settings")
    result_limit = st.slider("Max preview rows to load in UI", min_value=100, max_value=50000, value=5000, step=500)
    
    st.divider()
    st.header("📤 Load Datasets")
    upload_method = st.radio("Method", ["Direct File Path", "Upload via Browser"], horizontal=True)
    
    if upload_method == "Direct File Path":
        st.caption("💡 Mount local files sequentially. Add a path, hit load, then change the box to add another.")
        path_input = st.text_input("Absolute File Path", placeholder="C:/data/huge_dataset.csv", key="local_path_field")
        submit_load = st.button("⚡ Mount Local File", use_container_width=True)
        
        if submit_load and path_input:
            clean_path = path_input.strip().strip('"').strip("'")
            if os.path.isfile(clean_path):
                f_name = os.path.basename(clean_path)
                if any(info["filename"] == f_name for info in st.session_state.datasets.values()):
                    st.warning(f"⚠️ {f_name} is already registered inside your active catalog.")
                else:
                    with st.spinner(f"Converting and indexing {f_name} to Columnar Table..."):
                        success, msg = register_file(f_name, clean_path, os.path.getsize(clean_path))
                        if success:
                            st.success(f"Successfully loaded: {', '.join(msg)}")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"Failed to mount: {msg[0]}")
            else:
                st.error("File path invalid or unreachable. Verify spelling.")
    else:
        uploaded_files = st.file_uploader("Upload files (Max 5GB)", type=["csv", "parquet", "xlsx", "xls"], accept_multiple_files=True)
        submit_load = st.button("⚡ Process Uploaded Files", use_container_width=True)
        if submit_load and uploaded_files:
            os.makedirs(TEMP_DIR, exist_ok=True)
            new_additions = False
            for f in uploaded_files:
                if any(info["filename"] == f.name for info in st.session_state.datasets.values()):
                    continue
                temp_filepath = os.path.join(TEMP_DIR, f.name)
                with open(temp_filepath, "wb") as buffer:
                    buffer.write(f.getbuffer())
                with st.spinner(f"Ingesting {f.name}..."):
                    success, msg = register_file(f.name, temp_filepath, f.size)
                    if success:
                        new_additions = True
            if new_additions:
                st.rerun()

    st.divider()
    st.header("📁 Active Data Catalog")
    if st.session_state.datasets:
        for table, info in list(st.session_state.datasets.items()):
            col1, col2 = st.columns([4, 1])
            with col1:
                stats = get_table_stats(table)
                if stats:
                    with st.expander(f"📊 {table} ({stats['rows']:,} rows)"):
                        st.caption(f"Source: {info['filename']}")
                        st.caption(f"Weight: {format_file_size(info['size'])}")
                        st.dataframe(stats['schema'][['column_name', 'column_type']], use_container_width=True, hide_index=True)
                else:
                    st.caption(f"📊 {table} (Loading stats...)")
            with col2:
                if st.button("🗑", key=f"del_{table}"):
                    con.execute(f"DROP TABLE IF EXISTS {table}")
                    del st.session_state.datasets[table]
                    st.rerun()
    else:
        st.info("No files mounted yet.")

    st.divider()
    st.header("⏳ Session Query History")
    if st.session_state.query_history:
        for idx, hist_query in enumerate(reversed(st.session_state.query_history[-8:])):
            st.code(hist_query, language="sql")
            st.caption("---")
            
    # Credit Statement
    st.divider()
    st.caption("🛠️ **Engine Credit:** Core query performance & multi-engine stability enhancements optimized by **Gemini AI**.")

# ==========================================================
# Main Dashboard UI
# ==========================================================
st.title("📊 Enterprise SQL Workbench")

if st.session_state.datasets:
    st.header("🔍 Interactive Metadata Explorer")
    selected = st.selectbox("Pick Table to Inspect", list(st.session_state.datasets.keys()))
    stats = get_table_stats(selected)
    if stats:
        m1, m2 = st.columns(2)
        m1.metric("Row Profile Count", f"{stats['rows']:,}")
        m2.metric("Total Extracted Columns", stats['columns'])
        search_col = st.text_input("🔍 Filter Columns by Name", "", placeholder="Type column keyword to filter...", key=f"src_{selected}")
        if search_col:
            filtered_schema = stats['schema'][stats['schema']['column_name'].str.lower().str.contains(search_col.lower())]
            st.dataframe(filtered_schema[['column_name', 'column_type']], use_container_width=True, hide_index=True)
        else:
            st.dataframe(stats['schema'][['column_name', 'column_type']], use_container_width=True, hide_index=True)
        with st.expander("👀 View Head Sample (First 50 Rows)"):
            try:
                sample = con.execute(f"SELECT * FROM {selected} LIMIT 50").fetchdf()
                st.dataframe(sample, use_container_width=True)
            except Exception as e:
                st.error(f"Preview Failed: {e}")

st.header("📝 Query Editor")
first_table = list(st.session_state.datasets.keys())[0] if st.session_state.datasets else "dataA"
default_query = f"SELECT * FROM {first_table} LIMIT 100" if st.session_state.datasets else "-- Mount datasets in the sidebar to run custom SQL"

query = st_ace(value=default_query, language="sql", theme="monokai", height=260, font_size=14, wrap=True, show_gutter=True, auto_update=True, key="sql_workbench_editor")

run_col, clear_col, _ = st.columns([1, 1, 4])
execute_query = run_col.button("▶ Run Script", type="primary", use_container_width=True)
clear_query = clear_col.button("🗑 Reset Workbench", use_container_width=True)

if clear_query:
    st.session_state.query_result = None
    st.session_state.query_time = None
    st.session_state.query_row_count = None
    st.rerun()

if execute_query and query.strip():
    if not st.session_state.datasets:
        st.error("No active datasets present to process queries against.")
    else:
        try:
            with st.spinner("⏳ Vectorizing columnar data arrays..."):
                start = time.perf_counter()
                if not st.session_state.query_history or st.session_state.query_history[-1] != query.strip():
                    st.session_state.query_history.append(query.strip())
                count_query = f"SELECT COUNT(*) FROM ({query}) AS master_subquery"
                total_res = con.execute(count_query).fetchone()
                total_rows = total_res[0] if total_res is not None else 0
                safe_query = f"SELECT * FROM ({query}) AS master_subquery LIMIT {result_limit}"
                result_df = con.execute(safe_query).fetchdf()
                end = time.perf_counter()
            st.session_state.query_result = result_df
            st.session_state.query_time = round(end - start, 3)
            st.session_state.query_row_count = total_rows
            st.success(f"🎯 Execution completed in {st.session_state.query_time} seconds.")
        except Exception as e:
            st.error(f"❌ SQL Execution Error:\n{str(e)}")

# ==========================================================
# Results Analytics & Exporters
# ==========================================================
result = st.session_state.query_result
if result is not None:
    st.header("📊 Result Analysis Grid")
    res_m1, res_m2, res_m3 = st.columns(3)
    res_m1.metric("UI Loaded Rows", f"{len(result):,}")
    res_m2.metric("Total Matches across Dataset", f"{st.session_state.query_row_count:,}")
    res_m3.metric("Latency Profiles", f"{st.session_state.query_time}s")
    
    if st.session_state.query_row_count > result_limit:
        st.warning(f"⚠️ Truncated Preview: {st.session_state.query_row_count:,} rows hit, but showing only top {result_limit:,} inside UI frame.")
    st.dataframe(result, use_container_width=True, height=350)
    
    st.subheader("⬇ Safe Exporters (Capped to Preview Limit)")
    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        csv_data = result.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV (Preview)", csv_data, f"query_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv", use_container_width=True)
    with ex2:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                result.to_excel(writer, index=False)
            st.download_button("📥 Download Excel (Preview)", data=buffer.getvalue(), file_name=f"query_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        except Exception:
            st.button("📥 Excel compilation failed", disabled=True, use_container_width=True)
    with ex3:
        json_data = result.to_json(orient='records').encode("utf-8")
        st.download_button("📥 Download JSON (Preview)", json_data, f"query_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "application/json", use_container_width=True)

    st.markdown("---")
    st.subheader("💾 Native Out-Of-Core Export (Recommended for Massive Result Sets)")
    st.caption("Bypasses browser memory barriers entirely. Streams ALL matched query rows directly onto your local storage system via DuckDB engine streams.")
    exp_col1, exp_col2 = st.columns([3, 1])
    export_path_input = exp_col1.text_input("Target Absolute Path for Full Dataset Save", placeholder="C:/Users/Desktop/complete_output.csv", key="native_export_field")
    run_native_export = exp_col2.button("💾 Stream Full Export", use_container_width=True)
    
    if run_native_export and export_path_input:
        clean_exp_path = export_path_input.strip().strip('"').strip("'")
        lower_exp = clean_exp_path.lower()
        try:
            with st.spinner("Streaming matching data blocks directly to disk output..."):
                if lower_exp.endswith(".parquet"):
                    con.execute(f"COPY ({query}) TO '{clean_exp_path}' (FORMAT PARQUET)")
                elif lower_exp.endswith((".xlsx", ".xls")):
                    st.error("DuckDB cannot write natively to formatting layers like .xlsx directly. Please target .csv or .parquet for high-scale exports.")
                    clean_exp_path = None
                else:
                    if not lower_exp.endswith(".csv"):
                        clean_exp_path += ".csv"
                    con.execute(f"COPY ({query}) TO '{clean_exp_path}' (HEADER, DELIMITER ',')")
            if clean_exp_path:
                st.success(f"🚀 Success! Extracted and wrote all {st.session_state.query_row_count:,} matched rows directly to: {clean_exp_path}")
        except Exception as export_error:
            st.error(f"Direct Export Pipeline Failed: {str(export_error)}")
