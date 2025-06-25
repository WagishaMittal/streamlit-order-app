import streamlit as st
import gspread
import pandas as pd
from gspread_dataframe import get_as_dataframe
from io import BytesIO
import json
from google.oauth2.service_account import Credentials

# Load from Google Sheets
def load_sheet():
    creds_dict = st.secrets["gcp_service_account"]
    st.write("Auth scope set:", scope)
    st.write("Client email loaded:", creds_dict["client_email"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(creds_dict)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key("1PrsSMbPddsn1FnjC4Fao2XJ63f1kG4u8X9aWZwmdK1A")
    ws = sh.get_worksheet(0)
    df = get_as_dataframe(ws).dropna(how='all')
    df["Available Qty"] = pd.to_numeric(df["Available Qty"], errors="coerce").fillna(0).astype(int)
    return df

df = load_sheet()

# --- UI Starts Here ---
st.title("📦 Stock Order System")

# Customer Info
st.sidebar.header("🧍 Customer Info")
customer_name = st.sidebar.text_input("Customer Name")
customer_id = st.sidebar.text_input("Customer ID")

if not customer_name or not customer_id:
    st.warning("Please enter customer name and ID in the sidebar to continue.")
    st.stop()

st.success(f"Welcome, {customer_name} (ID: {customer_id})")

# Search and filter
search = st.text_input("🔍 Search SKU or Item Name")
filtered_df = df.copy()
if search:
    filtered_df = df[df["SkuShortName"].str.contains(search, case=False) |
                     df["SKU"].str.contains(search, case=False)]

# Quantity Input Inline
st.write("### 📝 Enter Quantities Inline")

with st.form("order_form"):
    updated_rows = []
    for i, row in filtered_df.iterrows():
        cols = st.columns([3, 5, 2, 3])  # SKU | Name | Available | Qty
        cols[0].markdown(f"**{row['SKU']}**")
        cols[1].markdown(row['SkuShortName'])
        cols[2].markdown(f"{row['Available Qty']}")
        qty = cols[3].number_input(
            label="Qty",
            min_value=0,
            max_value=int(row["Available Qty"]),
            step=1,
            key=f"qty_{i}"
        )
        updated_rows.append({**row, "Order Quantity": qty})

    submitted = st.form_submit_button("📥 Generate Order Sheet")

if submitted:
    order_df = pd.DataFrame(updated_rows)
    order_summary = order_df[order_df["Order Quantity"] > 0]

    if not order_summary.empty:
        st.success("✅ Order Ready!")

        # Add customer info to output
        order_summary.insert(0, "Customer Name", customer_name)
        order_summary.insert(1, "Customer ID", customer_id)

        st.dataframe(order_summary[["Customer Name", "Customer ID", "SKU", "SkuShortName", "Available Qty", "Order Quantity"]])

        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Order Sheet")
            return output.getvalue()

        excel_data = to_excel(order_summary)

        st.download_button(
            label="⬇️ Download Order Sheet",
            data=excel_data,
            file_name=f"order_{customer_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No quantities selected.")
