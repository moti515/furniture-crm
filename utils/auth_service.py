import pandas as pd
import streamlit as st
from utils.sheets_service import get_orders_data


@st.cache_data(ttl=300)
def get_master_config() -> pd.DataFrame:
  """Зчитує конфігураційний аркуш Master_Config із кешуванням на 5 хвилин"""
  master_id = st.secrets.get("MASTER_SHEET_ID")
  if not master_id:
    st.error("Помилка: У секретах не вказано MASTER_SHEET_ID!")
    return pd.DataFrame()

  raw_config = get_orders_data(master_id, "Master_Config")
  if raw_config:
    return pd.DataFrame(raw_config)
  return pd.DataFrame()


def authenticate_user(email: str) -> dict | None:
  """Шукає користувача в Master_Config та повертає профіль із доступними базами та їх папка на Диску."""
  df_config = get_master_config()

  if df_config.empty:
    st.error("Неможливо завантажити Master_Config або аркуш порожній.")
    return None

  # Нормалізація колонок
  df_config["Email користувача"] = (
      df_config["Email користувача"].astype(str).str.strip().str.lower()
  )
  clean_email = email.strip().lower()

  # Залишаємо тільки рядки, де реалізовано валідний ID бази даних
  df_config = df_config.dropna(subset=["ID бази даних"])
  df_config = df_config[df_config["ID бази даних"].astype(str).str.strip() != ""]

  user_rows = df_config[df_config["Email користувача"] == clean_email]

  if user_rows.empty:
    return None

  first_row = user_rows.iloc[0].to_dict()
  role = str(first_row.get("Роль", "user")).strip().lower()

  # Формуємо словник доступних баз: { "Назва напрямку": { "sheet_id": "...", "drive_folder_id": "..." } }
  target_df = df_config if role == "admin" else user_rows

  available_databases = {}
  for _, row in target_df.iterrows():
    db_name = str(row.get("Ім'я / Напрямок", "Без назви")).strip()
    sheet_id = str(row.get("ID бази даних", "")).strip()
    drive_folder_id = str(row.get("ID папки Google Drive", "")).strip()

    if sheet_id:
      available_databases[db_name] = {
          "sheet_id": sheet_id,
          "drive_folder_id": drive_folder_id,
      }

  return {
      "user_id": first_row.get("User_ID"),
      "email": clean_email,
      "name": first_row.get("Ім'я / Напрямок"),
      "role": role,
      "available_databases": available_databases,
  }
