import streamlit as st
from utils.auth_service import authenticate_user
from views.contacts_manager import render_contacts_view
from views.manager_orders import render_manager_orders_view
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
        f"⛔ Пошту (`{google_email}`) не знайдено в Master_Config або акаунт неактивний."
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
        "⚠️ Для вашого акаунта не прописано жодної доступної бази даних у Master_Config."
    )
    st.info("💡 Зверніться до адміністратора для налаштування доступу.")
else:
    if len(db_options) > 1:
        selected_db_name = st.sidebar.selectbox(
            "📂 Оберіть базу даних:", list(db_options.keys())
        )
    else:
        selected_db_name = list(db_options.keys())[0]
        st.sidebar.info(f"📂 Активна база:\n\n**{selected_db_name}**")

    selected_db_info = db_options[selected_db_name]
    selected_sheet_id = selected_db_info.get("sheet_id", "")
    drive_folder_id = selected_db_info.get("drive_folder_id", "")

    # Якщо перейшли за посиланням з ?edit_order=ORD-...
    qp_order_id = str(st.query_params.get("edit_order", "")).strip()
    if qp_order_id and st.session_state.get("edit_order_id") != qp_order_id:
        st.session_state.edit_order_id = qp_order_id
        st.session_state.nav_menu = "📋 Актуальні замовлення"

    menu_options = ["📋 Актуальні замовлення", "➕ Нове замовлення", "👥 Контакти"]
    default_idx = 0
    if st.session_state.get("nav_menu") in menu_options:
        default_idx = menu_options.index(st.session_state["nav_menu"])

    menu = st.sidebar.radio(
        "Навігація",
        menu_options,
        index=default_idx,
        key="sidebar_nav_radio",
    )
    st.session_state.nav_menu = menu

    st.markdown(f"### Поточний напрямок: **{selected_db_name}**")

    # --- МЕНЮ ТА РОУТИНГ ---
    if menu == "📋 Актуальні замовлення":
        render_manager_orders_view(selected_sheet_id, drive_folder_id)

    elif menu == "➕ Нове замовлення":
        render_new_order_view(selected_sheet_id, drive_folder_id)

    elif menu == "👥 Контакти":
        render_contacts_view(selected_sheet_id)
