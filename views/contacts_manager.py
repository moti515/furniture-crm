import pandas as pd
import streamlit as st
from utils.sheets_service import get_all_contacts_records, save_new_contact

ALL_ROLES = ["Замовник", "Замірник", "Дизайнер", "Конструктор", "Виробник", "Монтажник", "Інше"]


def inject_vertical_multiselect_css():
    """Потужні CSS-стилі для примусового вертикального вишикування тегів у мультивиборі."""
    st.markdown(
        """
        <style>
        /* Загальний контейнер мультивибору */
        .stMultiSelect div[data-baseweb="select"] {
            height: auto !important;
            min-height: 40px !important;
        }
        /* Внутрішній контейнер, що містить вибрані теги */
        .stMultiSelect div[data-baseweb="select"] > div:first-child {
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
            gap: 4px !important;
            height: auto !important;
            padding: 4px !important;
        }
        /* Кожен окремий тег на всю ширину рядка */
        .stMultiSelect div[data-baseweb="select"] span[data-baseweb="tag"] {
            width: 100% !important;
            display: flex !important;
            justify-content: space-between !important;
            box-sizing: border-box !important;
            margin: 2px 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_contact_form(selected_sheet_id, default_role="", key_suffix="default", on_success=None):
    """Повноцінна форма додавання нового контакту з вертикальним мультивибором ролей."""
    inject_vertical_multiselect_css()
    
    st.info("📝 **Форма нового контакту**")
    with st.expander("Заповніть дані контакту", expanded=True):
        new_name = st.text_input("ПІБ / Назва *", key=f"new_name_{key_suffix}")
        col_a, col_b = st.columns(2)
        with col_a:
            new_phone = st.text_input("Телефон", key=f"new_phone_{key_suffix}")
            new_email = st.text_input("Email", key=f"new_email_{key_suffix}")
        with col_b:
            default_roles = [default_role] if default_role and default_role in ALL_ROLES else []
            new_roles = st.multiselect(
                "Роль / Категорія *",
                options=ALL_ROLES,
                default=default_roles,
                key=f"new_roles_{key_suffix}"
            )
            st.caption("💡 Для додавання категорій/ролей - зверніться до адміністратора")
            new_comment = st.text_input("Коментар", key=f"new_com_{key_suffix}")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 Зберегти контакт", key=f"btn_save_contact_{key_suffix}"):
                if not new_name:
                    st.error("❌ Введіть ПІБ або назву контакту.")
                elif not new_roles:
                    st.error("❌ Оберіть принаймні одну роль / категорію.")
                else:
                    contact_data = {
                        "ПІБ / Назва": new_name,
                        "Роль / Категорія": ", ".join(new_roles),
                        "Телефон(и)": new_phone,
                        "Email(и)": new_email,
                        "Коментар": new_comment,
                    }
                    success = save_new_contact(selected_sheet_id, contact_data)
                    if success:
                        st.success(f"✅ Контакт '{new_name}' успішно додано!")
                        if on_success:
                            on_success()
                        else:
                            st.rerun()
                    else:
                        st.error("❌ Помилка збереження контакту.")
        with col_s2:
            if st.button("Скасувати", key=f"btn_cancel_{key_suffix}"):
                if on_success:
                    on_success()
                else:
                    st.rerun()


def render_contacts_view(selected_sheet_id):
    """Повноцінний розділ управління контактами в меню."""
    inject_vertical_multiselect_css()
    st.subheader("👥 Довідник контактів")

    if "show_new_contact_modal" not in st.session_state:
        st.session_state.show_new_contact_modal = False

    if not st.session_state.show_new_contact_modal:
        if st.button("➕ Додати новий контакт", type="primary"):
            st.session_state.show_new_contact_modal = True
            st.rerun()
    else:
        render_contact_form(
            selected_sheet_id,
            default_role="Замовник",
            key_suffix="contacts_page",
            on_success=lambda: setattr(st.session_state, 'show_new_contact_modal', False)
        )
        st.markdown("---")

    contacts_records = get_all_contacts_records(selected_sheet_id)
    if contacts_records:
        df_contacts = pd.DataFrame(contacts_records)
        st.dataframe(df_contacts, width="stretch")
    else:
        st.info("У цій базі даних ще немає збережених контактів.")
