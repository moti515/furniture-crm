import pandas as pd
import streamlit as st
from utils.auth_service import authenticate_user
from utils.sheets_service import get_orders_data
from views.new_order import render_new_order_view

st.set_page_config(
    page_title="Motia Furniture CRM", page_icon="🪑", layout="wide"
)

st.title("🪑 Система управління замовленнями")

# 1. Перевірка нативної авторизації Streamlit
if not st.user.is_logged_in:
  st.subheader("🔑 Будь ласка, увійдіть за допомогою Google-акаунта")
  st.info("Доступ мають лише користувачі, зареєстровані в Master_Config.")
  st.button("🔑 Увійти через Google", on_click=st.login)
  st.stop()

# 2. Отримуємо підтверджену пошту Google
google_email = st.user.email
user_name = st.user.name or google_email

# 3. Перевіряємо пошту в Master_Config
profile = authenticate_user(google_email)

if not profile:
  st.error(
      f"⛔ Пошту (`{google_email}`) не знайдено в Master_Config або акаунт"
      " неактивний."
  )
  st.info("💡 Зверніться до адміністратора для отримання доступу.")
  st.button("🚪 Вийти з акаунта", on_click=st.logout)
  st.stop()

# --- ОСНОВНИЙ ІНТЕРФЕЙС CRM (ПІСЛЯ ВХОДУ) ---
st.sidebar.write(
    f"👤 **{user_name}**\n\n✉️ `{google_email}`\n\nРоль: `{profile['role']}`"
)
st.sidebar.button("🚪 Вийти з акаунта", on_click=st.logout)

st.sidebar.markdown("---")

# --- СЕЛЕКТОР БАЗ ДАНИХ ---
db_options = profile.get("available_databases", {})

if not db_options:
  st.warning(
      "⚠️ Для вашого акаунта не прописано жодної доступної бази даних у"
      " Master_Config."
  )
  st.info("💡 Зверніться до адміністратора для налаштування доступу.")
else:
  # Якщо баз кілька — виводимо випадаючий список
  if len(db_options) > 1:
    selected_db_name = st.sidebar.selectbox(
        "📂 Оберіть базу даних:", list(db_options.keys())
    )
  else:
    selected_db_name = list(db_options.keys())[0]
    st.sidebar.info(f"📂 Активна база:\n\n**{selected_db_name}**")

  selected_sheet_id = db_options[selected_db_name]

  menu = st.sidebar.radio(
      "Навігація",
      ["📋 Актуальні замовлення", "➕ Нове замовлення", "👥 Контакти"],
  )

  st.markdown(f"### Поточний напрямок: **{selected_db_name}**")

  # --- МЕНЮ ТА РОУТИНГ ---
    if menu == "📋 Актуальні замовлення":
        raw_data = get_orders_data(selected_sheet_id, "Orders")
        if raw_data:
            df = pd.DataFrame(raw_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("У цій базі замовлення відсутні або аркуш 'Orders' порожній.")

    elif menu == "➕ Нове замовлення":
        # Отримуємо drive_folder_id напрямку з об'єкта профілю користувача
        drive_folder_id = profile.get("available_databases", {}).get(
            selected_db_name, ""
        )
        render_new_order_view(selected_sheet_id, drive_folder_id)

    elif menu == "👥 Контакти":
        st.info("Розділ довідника контактів знаходиться в розробці.")
