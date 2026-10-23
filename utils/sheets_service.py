import gspread
import streamlit as st


@st.cache_resource
def get_gspread_client():
  """Ініціалізація клієнта Google Sheets через секрети Streamlit"""
  creds_dict = dict(st.secrets["gcp_service_account"])
  client = gspread.service_account_from_dict(creds_dict)
  return client


def get_orders_data(spreadsheet_name: str, sheet_name: str = "Orders"):
  """Отримує всі замовлення з таблиці у вигляді списку словників"""
  client = get_gspread_client()
  try:
    sh = client.open(spreadsheet_name)
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return data
  except Exception as e:
    st.error(f"Помилка підключення до таблиці: {e}")
    return []


def add_order_to_sheet(
    spreadsheet_name: str, order_data: list, sheet_name: str = "Orders"
):
  """Додає новий рядок із замовленням"""
  client = get_gspread_client()
  sh = client.open(spreadsheet_name)
  worksheet = sh.worksheet(sheet_name)
  worksheet.append_row(order_data)
