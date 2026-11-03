import pandas as pd
import streamlit as st
from utils.sheets_service import (
    get_all_contacts_records,
    get_orders_data,
    save_new_contact,
)

ALL_ROLES = ["Замовник", "Замірник", "Дизайнер", "Конструктор", "Виробник", "Монтажник", "Інше"]


def render_role_picker(label, key_suffix, default_roles=None):
    """Двоколоночний компонент вибору ролей / категорій всередині форми контакту."""
    st.markdown(f"**{label} *:**")
    
    state_key = f"picked_roles_{key_suffix}"
    if state_key not in st.session_state:
        if default_roles:
            st.session_state[state_key] = [r.strip() for r in str(default_roles).split(",") if r.strip()]
        else:
            st.session_state[state_key] = []
            
    available_roles = [r for r in ALL_ROLES if r not in st.session_state[state_key]]
    
    col_left, col_right = st.columns([3, 3])
    
    with col_left:
        st.markdown("<small><b>Вибрані ролі:</b></small>", unsafe_allow_html=True)
        if not st.session_state[state_key]:
            st.caption("Жодної ролі не обрано")
        else:
            for idx, role in enumerate(st.session_state[state_key]):
                sub_c1, sub_c2 = st.columns([5, 1])
                with sub_c1:
                    st.text(role)
                with sub_c2:
                    if st.button("❌", key=f"del_role_{key_suffix}_{idx}_{role}", help="Видалити"):
                        st.session_state[state_key].remove(role)
                        st.rerun()
                        
    with col_right:
        st.markdown("<small><b>Додати роль:</b></small>", unsafe_allow_html=True)
        options = ["-- Оберіть роль --"] + available_roles
        chosen = st.selectbox("Обрати роль", options=options, key=f"sel_box_role_{key_suffix}", label_visibility="collapsed")
        if chosen and chosen != "-- Оберіть роль --":
            if chosen not in st.session_state[state_key]:
                st.session_state[state_key].append(chosen)
                st.rerun()
                
    st.caption("💡 Для додавання нових категорій/ролей — зверніться до адміністратора.")
    return st.session_state[state_key]


def render_contact_picker(label, key_suffix, role_filter="", selected_sheet_id=None, all_contacts_records=None):
    """Двоколоночний інтерактивний компонент вибору контактів для форми замовлення."""
    st.markdown(f"**{label}**")
    
    state_key = f"picked_contacts_{key_suffix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = []
        
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


def render_contact_form(selected_sheet_id, default_role="", contact_data_to_edit=None, key_suffix="new_contact", on_success=None):
    """Оптимізована форма додавання або редагування контакту з розширеними полями."""
    is_edit = contact_data_to_edit is not None
    title = f"📝 Редагування контакту: {contact_data_to_edit.get('ПІБ / Назва', '')}" if is_edit else "📝 Форма нового контакту"
    btn_label = "🔄 Оновити контакт" if is_edit else "💾 Зберегти нові дані"

    st.info(title)
    sfx = str(contact_data_to_edit.get("ID Контакту", "edit")) if is_edit else key_suffix

    with st.expander("Детальна інформація про контакт", expanded=True):
        contact_id = contact_data_to_edit.get("ID Контакту", "") if is_edit else ""
        if is_edit:
            st.text_input("ID Контакту", value=contact_id, disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("ПІБ / Назва *", value=contact_data_to_edit.get("ПІБ / Назва", "") if is_edit else "", key=f"name_{sfx}")
        with col2:
            company = st.text_input("Компанія", value=contact_data_to_edit.get("Компанія", "") if is_edit else "", key=f"company_{sfx}", placeholder="Напр., ТОВ «Меблі-Світ»")

        existing_roles_str = contact_data_to_edit.get("Роль / Категорія", default_role) if is_edit else default_role
        selected_roles = render_role_picker("Роль / Категорія", key_suffix=sfx, default_roles=existing_roles_str)

        st.markdown("---")

        col3, col4 = st.columns(2)
        with col3:
            phone = st.text_input(
                "Телефон(и)", 
                value=contact_data_to_edit.get("Телефон(и)", "") if is_edit else "", 
                key=f"phone_{sfx}",
                placeholder="+4915123456789, +380501112233"
            )
            st.caption("💡 У міжнародній формі, через кому")
        with col4:
            email = st.text_input(
                "Email(и)", 
                value=contact_data_to_edit.get("Email(и)", "") if is_edit else "", 
                key=f"email_{sfx}",
                placeholder="example1@gmail.com, example2@ukr.net"
            )
            st.caption("💡 Декілька адрес — через кому")

        col5, col6 = st.columns(2)
        with col5:
            telegram = st.text_input(
                "Нік Telegram", 
                value=contact_data_to_edit.get("Нік Telegram", "") if is_edit else "", 
                key=f"telegram_{sfx}",
                placeholder="@username1, @username2"
            )
            st.caption("💡 З собачки (@), через кому")
        with col6:
            client_types = ["Фізична особа", "Юридична особа"]
            curr_type = contact_data_to_edit.get("Тип (Фіз./Юр.)", "Фізична особа") if is_edit else "Фізична особа"
            type_idx = client_types.index(curr_type) if curr_type in client_types else 0
            client_type = st.selectbox("Тип (Фіз./Юр.)", options=client_types, index=type_idx, key=f"client_type_{sfx}")

        address = st.text_input("Адреса / Місто", value=contact_data_to_edit.get("Адреса / Місто", "") if is_edit else "", key=f"address_{sfx}", placeholder="м. Штутгарт, вул. Штрассе, 12")
        comment = st.text_area("Коментар", value=contact_data_to_edit.get("Коментар", "") if is_edit else "", key=f"comment_{sfx}", placeholder="Будь-які додаткові нотатки...")

        if is_edit:
            st.markdown("#### 🔗 Зв'язані проєкти")
            orders_data = get_orders_data(selected_sheet_id, "Orders")
            contact_name = contact_data_to_edit.get("ПІБ / Назва", "").strip()
            
            linked_orders = []
            for ord_row in orders_data:
                row_str = " ".join([str(val) for val in ord_row.values()])
                if contact_name and contact_name.lower() in row_str.lower():
                    linked_orders.append(ord_row.get("ID Замовлення", "Н/Д") + " - " + ord_row.get("Назва замовлення", ""))
            
            if linked_orders:
                for proj in linked_orders:
                    st.markdown(f"- 📂 {proj}")
            else:
                st.info("Цей контакт наразі не прикріплений до жодного замовлення.")

        st.markdown("---")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button(btn_label, type="primary", key=f"btn_save_{sfx}"):
                if not name:
                    st.error("❌ Введіть ПІБ або назву контакту.")
                elif not selected_roles:
                    st.error("❌ Оберіть принаймні одну роль / категорію.")
                else:
                    contact_payload = {
                        "ПІБ / Назва": name,
                        "Роль / Категорія": ", ".join(selected_roles),
                        "Телефон(и)": phone,
                        "Email(и)": email,
                        "Нік Telegram": telegram,
                        "Компанія": company,
                        "Тип (Фіз./Юр.)": client_type,
                        "Адреса / Місто": address,
                        "Коментар": comment,
                    }
                    
                    if is_edit:
                        contact_payload["ID Контакту"] = contact_id
                        
                    success = save_new_contact(selected_sheet_id, contact_payload)
                        
                    if success:
                        st.success(f"✅ Контакт '{name}' успішно збережено!")
                        role_state_key = f"picked_roles_{sfx}"
                        if role_state_key in st.session_state:
                            del st.session_state[role_state_key]

                        st.session_state.edit_contact_id = None
                        st.session_state.show_new_contact_modal = False

                        if on_success:
                            on_success()
                        else:
                            st.rerun()
                    else:
                        st.error("❌ Помилка збереження контакту.")
        with col_s2:
            if st.button("Скасувати", key=f"btn_cancel_{sfx}"):
                role_state_key = f"picked_roles_{sfx}"
                if role_state_key in st.session_state:
                    del st.session_state[role_state_key]

                st.session_state.edit_contact_id = None
                st.session_state.show_new_contact_modal = False

                if on_success:
                    on_success()
                else:
                    st.rerun()


def render_contacts_view(selected_sheet_id):
    """Повноцінний розділ управління контактами з ультракомпактним табличним вирівнюванням."""
    st.markdown(
        """
        <style>
        div.stButton > button {
            margin-top: 28px !important;
        }
        .contact-row {
            display: flex;
            align-items: center;
            border-bottom: 1px solid rgba(150, 150, 150, 0.2);
            padding: 6px 0px;
            margin: 0px;
        }
        [data-testid="stHorizontalBlock"] {
            align-items: center !important;
            vertical-align: middle !important;
        }
        div[data-testid="column"] button {
            margin: 0px !important;
            padding: 2px 8px !important;
            min-height: 28px !important;
            font-size: 13px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("👥 Довідник контактів")

    if "edit_contact_id" not in st.session_state:
        st.session_state.edit_contact_id = None
    if "show_new_contact_modal" not in st.session_state:
        st.session_state.show_new_contact_modal = False

    contacts_records = get_all_contacts_records(selected_sheet_id)

    f_col1, f_col2, f_col3 = st.columns([2, 2, 1.5])
    with f_col1:
        search_query = st.text_input("🔍 Пошук за ім'ям / компанією", placeholder="Введіть текст...")
    with f_col2:
        role_filter = st.selectbox("Фільтр за роллю", options=["Всі ролі"] + ALL_ROLES)
    with f_col3:
        if not st.session_state.show_new_contact_modal and not st.session_state.edit_contact_id:
            if st.button("➕ Додати новий контакт", type="primary", use_container_width=True):
                st.session_state.show_new_contact_modal = True
                st.rerun()

    st.markdown("---")

    if st.session_state.show_new_contact_modal:
        render_contact_form(
            selected_sheet_id, 
            key_suffix="new_modal",
            on_success=lambda: setattr(st.session_state, 'show_new_contact_modal', False)
        )
        st.markdown("---")

    if st.session_state.edit_contact_id:
        target_contact = next((c for c in contacts_records if str(c.get("ID Контакту")) == str(st.session_state.edit_contact_id)), None)
        if target_contact:
            def _close_edit():
                st.session_state.edit_contact_id = None
                st.rerun()

            render_contact_form(
                selected_sheet_id, 
                contact_data_to_edit=target_contact, 
                on_success=_close_edit
            )
            st.markdown("---")

    filtered_records = []
    for row in contacts_records:
        name = str(row.get("ПІБ / Назва", ""))
        comp = str(row.get("Компанія", ""))
        roles = str(row.get("Роль / Категорія", ""))
        addr = str(row.get("Адреса / Місто", ""))
        comm = str(row.get("Коментар", ""))

        q = search_query.lower()
        match_search = not search_query or (
            q in name.lower() or 
            q in comp.lower() or 
            q in addr.lower() or 
            q in comm.lower()
        )
        match_role = role_filter == "Всі ролі" or role_filter.lower() in roles.lower()

        if match_search and match_role:
            filtered_records.append(row)

    if filtered_records:
        st.markdown(f"**Знайдено контактів:** {len(filtered_records)}")
        
        for idx, row in enumerate(filtered_records):
            c_id = row.get("ID Контакту", "")
            c_name = row.get("ПІБ / Назва", "")
            c_roles = row.get("Роль / Категорія", "")
            c_phone = row.get("Телефон(и)", "")
            c_comp = row.get("Компанія", "")

            rc1, rc2, rc3, rc4, rc5 = st.columns([3, 3, 3, 3, 1.5])
            
            with rc1:
                st.markdown(f"<span style='font-weight: 600;'>{c_name}</span>", unsafe_allow_html=True)
            with rc2:
                st.markdown(f"<span style='color: #555; font-size: 14px;'>{c_roles or '—'}</span>", unsafe_allow_html=True)
            with rc3:
                st.markdown(f"<span style='color: #555; font-size: 14px;'>{c_phone or '—'}</span>", unsafe_allow_html=True)
            with rc4:
                st.markdown(f"<span style='color: #555; font-size: 14px;'>{c_comp or '—'}</span>", unsafe_allow_html=True)
            with rc5:
                if st.button("✏️ Редагувати", key=f"edit_btn_{c_id}_{idx}", use_container_width=True):
                    st.session_state.edit_contact_id = c_id
                    st.session_state.show_new_contact_modal = False
                    st.rerun()
            
            st.markdown("<div style='margin: 2px 0px; border-bottom: 1px solid #eaeaea;'></div>", unsafe_allow_html=True)
    else:
        st.info("Контактів за вашим запитом не знайдено.")
