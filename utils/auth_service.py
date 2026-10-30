import pandas as pd
import streamlit as st
from utils.sheets_service import get_orders_data


def get_master_config() -> pd.DataFrame:
  """Зчитує конфігураційний аркуш Master_Config із головної таблиці"""
  master_id = st.secrets["MASTER_SHEET_ID"]
  raw_config = get_orders_data(master_id, "Master_Config")
  if raw_config:
    return pd.DataFrame(raw_config)
  return pd.DataFrame()


def authenticate_user(email: str) -> dict | None:
  """Шукає користувача за email у Master_Config та формує доступні йому бази."""
  df_config = get_master_config()

  if df_config.empty:
    st.error("Неможливо завантажити Master_Config або аркуш порожній.")
    return None

  # Нормалізація email для коректної перевірки
  df_config["Email користувача"] = (
      df_config["Email користувача"].astype(str).str.strip().str.lower()
  )
  clean_email = email.strip().lower()

  user_rows = df_config[df_config["Email користувача"] == clean_email]

  if user_rows.empty:
    return None

  first_row = user_rows.iloc[0].to_dict()
  role = str(first_row.get("Роль", "user")).strip().lower()

  # Формування доступних баз залежно від ролі
  if role == "admin":
    # Адмін бачить усі напрямки/бази, зареєстровані в Master_Config
    available_databases = (
        df_config[["Ім'я / Напрямок", "ID бази даних"]]
        .dropna(subset=["ID бази даних"])
        .set_index("Ім'я / Напрямок")["ID бази даних"]
        .to_dict()
    )
  else:
    # Звичайний користувач бачить тільки свої напрямки (якщо їх кілька в таблиці)
    available_databases = (
        user_rows[["Ім'я / Напрямок", "ID бази даних"]]
        .dropna(subset=["ID бази даних"])
        .set_index("Ім'я / Напрямок")["ID бази даних"]
        .to_dict()
    )

  return {
      "user_id": first_row.get("User_ID"),
      "email": clean_email,
      "name": first_row.get("Ім'я / Напрямок"),
      "role": role,
      "available_databases": available_databases,
  }
