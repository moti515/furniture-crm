import pandas as pd
import streamlit as st
from utils.sheets_service import add_order_to_sheet, get_orders_data

st.set_page_config(
    page_title="Furniture CRM", page_icon="🪑", layout="wide"
)

st.title("🪑 Система управління замовленнями (Меблі)")

# Назва вашої таблиці на Google Диску
SPREADSHEET_NAME = "Master_CRM_DB"

# Бічна панель навігації
menu = st.sidebar.selectbox(
    "Меню", ["Актуальні замовлення", "Створити замовлення", "Контакти"]
)

if menu == "Актуальні замовлення":
  st.header("📋 Список замовлень")

  # Завантаження даних з Google Таблиці
  raw_data = get_orders_data(SPREADSHEET_NAME, "Orders")

  if raw_data:
    df = pd.DataFrame(raw_data)
    st.dataframe(df, use_container_width=True)
  else:
    st.info(
        "База замовлень порожня або аркуш 'Orders' не містить даних (або ще не"
        " створений)."
    )

elif menu == "Створити замовлення":
  st.header("➕ Нове замовлення")

  with st.form("order_form"):
    client_name = st.text_input("Ім'я замовника")
    service_type = st.selectbox(
        "Тип послуги",
        ["Замір", "3D Проєкт", "Виготовлення", "Поставка", "Монтаж"],
    )
    phone = st.text_input("Телефон")
    notes = st.text_area("Примітки / Деталі")

    submitted = st.form_submit_button("Зберегти замовлення")

    if submitted:
      if client_name and phone:
        # Формуємо рядок для запису в таблицю
        new_row = [
            "ORD-001",
            client_name,
            service_type,
            phone,
            notes,
            "Новий",
            "",
        ]
        add_order_to_sheet(SPREADSHEET_NAME, new_row, "Orders")
        st.success(f"Замовлення для {client_name} успішно створено!")
      else:
        st.warning("Будь ласка, заповніть обов'язкові поля (Ім'я та Телефон).")
