import os
import google.auth.transport.requests
import google.oauth2.id_token
from google_auth_oauthlib.flow import Flow
import pandas as pd
import streamlit as st
from utils.auth_service import authenticate_user
from utils.sheets_service import get_orders_data

st.set_page_config(page_title="Motia Furniture CRM", page_icon="🪑", layout="wide")

CLIENT_ID = st.secrets["google_auth"]["client_id"]
CLIENT_SECRET = st.secrets["google_auth"]["client_secret"]
REDIRECT_URI = st.secrets["google_auth"]["redirect_uri"]

# Конфігурація OAuth потоку
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    },
    scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ],
)
flow.redirect_uri = REDIRECT_URI

# Ініціалізація сесії
if "user_profile" not in st.session_state:
  st.session_state.user_profile = None
if "google_email" not in st.session_state:
  st.session_state.google_email = None

st.title("🪑 Система управління замовленнями")

# Отримуємо код авторизації з параметрів URL (після редиректу від Google)
query_params = st.query_params
auth_code = query_params.get("code")

# Логіка обробки входу через Google
if not st.session_state.google_email:
  if auth_code:
    try:
      flow.fetch_token(code=auth_code)
      credentials = flow.credentials
      id_info = google.oauth2.id_token.verify_oauth2_token(
          credentials.id_token,
          google.auth.transport.requests.Request(),
          audience=CLIENT_ID,
      )
      st.session_state.google_email = id_info.get("email")
      # Очищаємо URL від параметра ?code=...
      st.query_params.clear()
      st.rerun()
    except Exception as e:
      st.error(f"Помилка авторизації Google: {e}")

# Якщо користувач ще не увійшов — показуємо кнопку входу
if not st.session_state.google_email:
  st.subheader("🔑 Будь ласка, увійдіть за допомогою Google-акаунта")

  auth_url, _ = flow.authorization_url(
      access_type="offline", include_granted_scopes="true"
  )

  st.markdown(
      f'<p><a href="{auth_url}" target="_self"><button'
      ' style="background-color:#4285F4; color:white; padding:10px 20px;'
      ' border:none; border-radius:4px; font-size:16px; cursor:pointer;">🔑'
      " Увійти через Google</button></a></p>",
      unsafe_allow_html=True,
  )

  st.info(
      "Доступ мають лише авторизовані користувачі, чиї поштові адреси зареєстровані"
      " в системі адміністратором."
  )

else:
  google_email = st.session_state.google_email

  # Перевіряємо пошту в нашому Master_Config
  if not st.session_state.user_profile:
    profile = authenticate_user(google_email)
    if profile:
      st.session_state.user_profile = profile
      st.rerun()
    else:
      st.error(
          f"Пошту (`{google_email}`) не знайдено в Master_Config або акаунт"
          " неактивний. Зверніться до адміністратора."
      )
      if st.button("Вийти / Змінити акаунт"):
        st.session_state.google_email = None
        st.session_state.user_profile = None
        st.rerun()
      st.stop()

  # --- ОСНОВНИЙ ІНТЕРФЕЙС CRM (ПІСЛЯ УСПІШНОГО ВХОДУ) ---
  profile = st.session_state.user_profile

  st.sidebar.write(
      f"👤 **{profile['name']}**\n\n✉️ `{google_email}`\n\nРоль:"
      f" `{profile['role']}`"
  )

  if st.sidebar.button("Вийти"):
    st.session_state.google_email = None
    st.session_state.user_profile = None
    st.rerun()

  st.sidebar.markdown("---")

  # --- СЕЛЕКТОР БАЗ ДАНИХ ---
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

    menu = st.sidebar.radio(
        "Навігація",
        ["📋 Актуальні замовлення", "➕ Нове замовлення", "👥 Контакти"],
    )

    st.markdown(f"### Поточний напрямок: **{selected_db_name}**")

    if menu == "📋 Актуальні замовлення":
      raw_data = get_orders_data(selected_sheet_id, "Orders")
      if raw_data:
        df = pd.DataFrame(raw_data)
        st.dataframe(df, use_container_width=True)
      else:
        st.info("У цій базі замовлення відсутні або аркуш 'Orders' порожній.")
