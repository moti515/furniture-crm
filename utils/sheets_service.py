import gspread
import streamlit as st


@st.cache_resource
def get_gspread_client():
  """Ініціалізація клієнта Google Sheets через секрети Streamlit"""
  creds_dict = dict(st.secrets["gcp_service_account"])
  client = gspread.service_account_from_dict(creds_dict)
  return client


def get_orders_data(spreadsheet_id: str, sheet_name: str = "Orders"):
  """Отримує всі рядки з таблиці за її ID у вигляді списку словників"""
  client = get_gspread_client()
  try:
    # Використовуємо відкриття за ID, що надійніше, ніж за назвою
    sh = client.open_by_key(spreadsheet_id)
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return data
  except Exception as e:
    st.error(f"Помилка підключення до таблиці (ID: {spreadsheet_id}): {e}")
    return []
