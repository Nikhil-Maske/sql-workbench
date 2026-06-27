# 📊 Enterprise SQL Workbench

An enterprise-grade local SQL analytical workbench designed to instantly query massive Excel, CSV, and Parquet datasets using ultra-fast, in-memory processing. Powered by DuckDB and Streamlit.

---

## ⚡ Core Features
* **Zero Database Setup:** No local server installation or configurations required.
* **Blazing Fast Analytics:** Utilizes **DuckDB's** vectorized, columnar data processing framework to query millions of rows in fractions of a second.
* **Multi-Engine Excel Parser:** Integrates high-performance `calamine` engines to unpack complex, large-scale sheets smoothly.
* **Direct-to-Disk Out-Of-Core Export:** Stream massive query results straight to a local file path, bypassing browser memory limitations entirely.

---

## 🏃‍♂️ How to Setup & Run (One-Click Launch)

You do not need to install Python or look at any code to run this application. Follow these simple steps:

1. **Download the Launcher:** Click on the **`Launch_SQL_Workbench.bat`** file in the list above, then click the **Download raw file** button (or click the direct link below).
2. **Move to Desktop:** Place the downloaded file onto your Desktop for easy access.
3. **Double-Click to Launch:** Run the `.bat` file. 

> 💡 **Note on Windows Security:** Since this script automates setting up a virtual sandbox environment and downloads your newest dashboard updates directly from GitHub, Windows SmartScreen may show a *"Windows protected your PC"* popup. Simply click **"More info"** and then select **"Run anyway"**. 

---

## 🛠️ Technology Stack
* **UI Interface Frame:** Streamlit (Dynamic Dataframes, Session Caching, and Ace Code Editor Integration)
* **SQL Processing Matrix:** DuckDB In-Memory Analytical Vectorization
* **Data Core Components:** Pandas, OpenPyXL, and Python-Calamine
