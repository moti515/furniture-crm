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
  """Шукає користувача за email у Master_Config та формує список доступних йому баз.

  Якщо ID бази даних порожній або відсутній, рядок ігнорується.
  """
  df_config = get_master_config()

  if df_config.empty:
    st.error("Неможливо завантажити Master_Config або аркуш порожній.")
    return None

  # Нормалізація колонок та email для коректної перевірки
  df_config["Email користувача"] = (
      df_config["Email користувача"].astype(str).str.strip().str.lower()
  )
  clean_email = email.strip().lower()

  # Фільтруємо тільки ті рядки, де реально прописаний ID бази даних (не NaN і не пустий рядок)
  df_config = df_config.dropna(subset=["ID бази даних"])
  df_config = df_config[df_config["ID бази даних"].astype(str).str.strip() != ""]

  user_rows = df_config[df_config["Email користувача"] == clean_email]

  if user_rows.empty:
    return None

  # Визначаємо роль за першим знайденим рядком користувача
  first_row = user_rows.iloc[0].to_dict()
  role = str(first_row.get("Роль", "user")).strip().lower()

  # Формування доступних баз даних (тільки з валідними ID)
  if role == "admin":
    # Адмін має доступ до ВСІХ валідних баз, зареєстрованих у Master_Config
    available_databases = (
        df_config[["Ім'я / Напрямок", "ID бази даних"]]
        .drop_duplicates(subset=["Ім'я / Напрямок"])
        .set_index("Ім'я / Напрямок")["ID бази даних"]
        .to_dict()
    )
  else:
    # Звичайний користувач отримує тільки ті свої бази, де заповнений ID
    available_databases = (
        user_rows[["Ім'я / Напрямок", "ID бази даних"]]
        .drop_duplicates(subset=["Ім'я / Напрямок"])
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
