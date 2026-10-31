import pandas as pd
import streamlit as st
from streamlit_google_auth import Authenticate
from utils.auth_service import authenticate_user
from utils.sheets_service import get_orders_data

st.set_page_config(page_title="Motia Furniture CRM", page_icon="🪑", layout="wide")

# Налаштування об'єкта аутентификації Google з секретів
auth = Authenticate(
    secret_credentials_path=None,
    client_id=st.secrets["google_auth"]["client_id"],
    client_secret=st.secrets["google_auth"]["client_secret"],
    redirect_uri=st.secrets["google_auth"]["redirect_uri"],
    cookie_name="motia_cookie",
    cookie_key="motia_secret_key",
    cookie_expiry_days=30,
)

# Перевірка стану входу
auth.check_authorization()

# Ініціалізація сесії авторизації
if "user_profile" not in st.session_state:
  st.session_state.user_profile = None

st.title("🪑 Система управління замовленнями")

# --- БЛОК АВТОРИЗАЦІЇ ЧЕРЕЗ GOOGLE ---
if not auth.logged_in:
  st.subheader("🔑 Будь ласка, увійдіть за допомогою Google-акаунта")
  # Рендеримо кнопку входу Google
  auth.login_button(button_text="Увійти через Google")

  st.info(
      "Доступ мають лише авторизовані користувачі, чиї поштові адреси зареєстровані"
      " в системі адміністратором."
  )

else:
  # Отримуємо дані користувача, який щойно успішно авторизувався через Google
  user_info = auth.get_user_info()
  google_email = user_info.get("email")

  # Перевіряємо пошту в нашому Master_Config
  if not st.session_state.user_profile:
    profile = authenticate_user(google_email)
    if profile:
      st.session_state.user_profile = profile
      st.rerun()
    else:
      st.error(
          f"Пошту ({google_email}) не знайдено в Master_Config або акаунт"
          " неактивний. Зверніться до адміністратора."
      )
      if st.button("Вийти"):
        auth.logout()
        st.rerun()
      st.stop()

  # --- ОСНОВНИЙ ІНТЕРФЕЙС CRM (ПІСЛЯ УСПІШНОГО ВХОДУ) ---
  profile = st.session_state.user_profile

  # Бокова панель (Сайдбар)
  st.sidebar.image(
      user_info.get("picture"), width=50
  )  # Аватарка з Google
  st.sidebar.write(
      f"👤 **{profile['name']}**\n\n✉️ `{google_email}`\n\nРоль: `{profile['role']}`"
  )

  if st.sidebar.button("Вийти"):
    auth.logout()
    st.session_state.user_profile = None
    st.rerun()

  st.sidebar.markdown("---")
  
  # --- СЕЛЕКТОР БАЗ ДАНИХ (ДЛЯ АДМІНА ТА КОРИСТУВАЧІВ) ---
  db_options = profile["available_databases"]

  if not db_options:
    st.error("У вас немає жодної доступної бази даних у Master_Config.")
  else:
    if len(db_options) > 1:
      selected_db_name = st.sidebar.selectbox(
          "📂 Оберіть базу даних:", list(db_options.keys())
      )
    else:
      selected_db_name = list(db_options.keys())[0]
      st.sidebar.info(f"📂 Активна база:\n\n**{selected_db_name}**")

    selected_sheet_id = db_options[selected_db_name]

    # Меню розділів
    menu = st.sidebar.radio(
        "Навігація",
        ["📋 Актуальні замовлення", "➕ Нове замовлення", "👥 Контакти"],
    )

    st.markdown(f"### Поточний напрямок: **{selected_db_name}**")

    if menu == "📋 Актуальні замовлення":
      # Підтягуємо дані з обраного Google Sheet ID користувача/напрямку
      raw_data = get_orders_data(selected_sheet_id, "Orders")
      if raw_data:
        df = pd.DataFrame(raw_data)
        st.dataframe(df, use_container_width=True)
      else:
        st.info("У цій базі замовлення відсутні або аркуш 'Orders' порожній.")
