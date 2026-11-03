import pandas as pd
import streamlit as st
from utils.sheets_service import get_all_contacts_records, save_new_contact

ALL_ROLES = ["Замовник", "Замірник", "Дизайнер", "Конструктор", "Виробник", "Монтажник", "Інше"]


def render_contact_form(selected_sheet_id, default_role="", key_suffix="default", on_success=None):
    """Повноцінна форма додавання нового контакту."""
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


def render_contact_picker(label, key_suffix, role_filter="", selected_sheet_id=None, all_contacts_records=None):
    """Двоколоночний інтерактивний компонент вибору контактів."""
    st.markdown(f"**{label}**")
    
    state_key = f"picked_contacts_{key_suffix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = []
        
    # Формуємо список усіх доступних контактів для цієї ролі з урахуванням ID
    all_contacts = []
    for row in all_contacts_records:
        contact_id = str(row.get("ID Контакту", "")).strip()
        name = str(row.get("ПІБ / Назва", "")).strip()
        roles_str = str(row.get("Роль / Категорія", "")).strip()

        if name:
            display_label = f"{name} ({contact_id})" if contact_id else name
            if role_filter:
                roles_list = [r.strip().lower() for r in roles_str.split(",")]
                if role_filter.lower() in roles_list:
                    all_contacts.append(display_label)
            else:
                all_contacts.append(display_label)
    all_contacts = sorted(list(set(all_contacts)))
    
    # Відсікаємо ті, що вже додані в ліву колонку
    available_contacts = [c for c in all_contacts if c not in st.session_state[state_key]]
    
    col_left, col_right, col_btn = st.columns([3, 3, 1])
    
    with col_left:
        st.markdown("<small><b>Вибрані:</b></small>", unsafe_allow_html=True)
        if not st.session_state[state_key]:
            st.caption("Щойно доданих немає")
        else:
            for idx, item in enumerate(st.session_state[state_key]):
                sub_c1, sub_c2 = st.columns([5, 1])
                with sub_c1:
                    st.text(item)
                with sub_c2:
                    if st.button("❌", key=f"del_{key_suffix}_{idx}_{item}", help="Видалити"):
                        st.session_state[state_key].remove(item)
                        st.rerun()
                        
    with col_right:
        st.markdown("<small><b>Додати з бази:</b></small>", unsafe_allow_html=True)
        options = ["-- Оберіть контакт --"] + available_contacts
        chosen = st.selectbox("Додати", options=options, key=f"sel_box_{key_suffix}", label_visibility="collapsed")
        if chosen and chosen != "-- Оберіть контакт --":
            if chosen not in st.session_state[state_key]:
                st.session_state[state_key].append(chosen)
                st.rerun()
                
    with col_btn:
        st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)
        if st.button("➕ Новий", key=f"btn_add_{key_suffix}"):
            st.session_state[f"show_add_{key_suffix}"] = True
            st.rerun()
            
    # Виклик форми створення нового контакту при натисканні «➕ Новий»
    if st.session_state.get(f"show_add_{key_suffix}", False):
        def close_form():
            st.session_state[f"show_add_{key_suffix}"] = False
            st.rerun()
        render_contact_form(
            selected_sheet_id=selected_sheet_id,
            default_role=role_filter,
            key_suffix=f"inline_{key_suffix}",
            on_success=close_form
        )
        
    return ", ".join(st.session_state[state_key])


def render_contacts_view(selected_sheet_id):
    """Повноцінний розділ управління контактами в меню."""
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
