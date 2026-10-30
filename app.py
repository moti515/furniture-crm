import pandas as pd
import streamlit as st
from utils.auth_service import authenticate_user
from utils.sheets_service import get_orders_data

st.set_page_config(page_title="Motia Furniture CRM", page_icon="🪑", layout="wide")

MASTER_SPREADSHEET_NAME = "Master_CRM_DB"

# Ініціалізація сесії авторизації
if "user_profile" not in st.session_state:
  st.session_state.user_profile = None

st.title("🪑 Система управління замовленнями (Motia CRM)")

# --- БЛОК АВТОРИЗАЦІЇ ---
if not st.session_state.user_profile:
  st.subheader("🔑 Вхід у систему")
  email_input = st.text_input("Введіть ваш Email для входу:")

  if st.button("Увійти"):
    if email_input:
      profile = authenticate_user(email_input, MASTER_SPREADSHEET_NAME)
      if profile:
        st.session_state.user_profile = profile
        st.success(f"Ласкаво просимо, {profile['name']}!")
        st.rerun()
      else:
        st.error(
            "Email не знайдено або акаунт деактивовано. Зверніться до"
            " адміністратора."
        )
    else:
      st.warning("Будь ласка, введіть Email.")

# --- ОСНОВНИЙ ІНТЕРФЕЙС CRM (ПІСЛЯ ВХОДУ) ---
else:
  profile = st.session_state.user_profile

  # Бокова панель (Сайдбар)
  st.sidebar.write(f"👤 **{profile['name']}** ({profile['role']})")

  if st.sidebar.button("Вийти"):
    st.session_state.user_profile = None
    st.rerun()

  st.sidebar.markdown("---")

  # --- СЕЛЕКТОР БАЗ ДАНИХ (ДЛЯ АДМІНА ТА КОРИСТУВАЧІВ) ---
  db_options = profile["available_databases"]

  if len(db_options) > 1:
    selected_db_name = st.sidebar.selectbox(
        "📂 Оберіть базу даних:", list(db_options.keys())
    )
  else:
    selected_db_name = list(db_options.keys())[0]
    st.sidebar.info(f"📂 Активна база: **{selected_db_name}**")

  selected_sheet_id = db_options[selected_db_name]

  # Меню розділів
  menu = st.sidebar.radio(
      "Навігація", ["📋 Актуальні замовлення", "➕ Нове замовлення", "👥 Контакти"]
  )

  st.markdown(f"### Поточний напрямок: **{selected_db_name}**")

  if menu == "📋 Актуальні замовлення":
    # Підтягуємо дані з обраного Google Sheet ID
    raw_data = get_orders_data(selected_sheet_id, "Orders")
    if raw_data:
      df = pd.DataFrame(raw_data)
      st.dataframe(df, use_container_width=True)
    else:
      st.info("У цій базі замовлення відсутні або аркуш 'Orders' порожній.")
