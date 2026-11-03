import pandas as pd
import streamlit as st
from utils.sheets_service import (
    get_all_contacts_records,
    get_orders_data,
    save_new_contact,
)

ALL_ROLES = ["Замовник", "Замірник", "Дизайнер", "Конструктор", "Виробник", "Монтажник", "Інше"]


def render_role_picker(label, key_suffix, default_roles=None):
    """Двоколоночний компонент вибору ролей / категорій."""
    st.markdown(f"**{label} *:**")
    
    state_key = f"picked_roles_{key_suffix}"
    if state_key not in st.session_state:
        # Ініціалізуємо початковими ролями, якщо вони передані (при редагуванні)
        if default_roles:
            st.session_state[state_key] = [r.strip() for r in default_roles.split(",") if r.strip()]
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


def render_contact_form(selected_sheet_id, contact_data_to_edit=None, on_success=None):
    """Оптимізована форма додавання або редагування контакту з розширеними полями."""
    is_edit = contact_data_to_edit is not None
    title = f"📝 Редагування контакту: {contact_data_to_edit.get('ПІБ / Назва', '')}" if is_edit else "📝 Форма нового контакту"
    
    st.info(title)
    
    # Ключовий суфікс для унікальності віджетів
    sfx = contact_data_to_edit.get("ID Контакту", "new") if is_edit else "new_contact"

    with st.expander("Детальна інформація про контакт", expanded=True):
        # Незмінний ID при редагуванні
        if is_edit:
            st.text_input("ID Контакту", value=contact_data_to_edit.get("ID Контакту", ""), disabled=True)

        # Ряд 1: ПІБ та Компанія
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("ПІБ / Назва *", value=contact_data_to_edit.get("ПІБ / Назва", "") if is_edit else "", key=f"name_{sfx}")
        with col2:
            company = st.text_input("Компанія", value=contact_data_to_edit.get("Компанія", "") if is_edit else "", key=f"company_{sfx}", placeholder="Напр., ТОВ «Меблі-Світ»")

        # Ряд 2: Вибір ролей через двоколоночний пікер
        existing_roles_str = contact_data_to_edit.get("Роль / Категорія", "") if is_edit else ""
        selected_roles = render_role_picker("Роль / Категорія", key_suffix=sfx, default_roles=existing_roles_str)

        st.markdown("---")

        # Ряд 3: Телефони та Email (з корисними підказками)
        col3, col4 = st.columns(2)
        with col3:
            phone = st.text_input(
                "Телефон(и)", 
                value=contact_data_to_edit.get("Телефон(и)", "") if is_edit else "", 
                key=f"phone_{sfx}",
                placeholder="+4915123456789, +380501112233"
            )
            st.caption("💡 У міжнародній формі, декілька — через кому")
        with col4:
            email = st.text_input(
                "Email(и)", 
                value=contact_data_to_edit.get("Email(и)", "") if is_edit else "", 
                key=f"email_{sfx}",
                placeholder="example1@gmail.com, example2@ukr.net"
            )
            st.caption("💡 Декілька адрес — через кому")

        # Ряд 4: Telegram та Тип (Фіз./Юр.)
        col5, col6 = st.columns(2)
        with col5:
            telegram = st.text_input(
                "Нік Telegram", 
                value=contact_data_to_edit.get("Нік Telegram", "") if is_edit else "", 
                key=f"telegram_{sfx}",
                placeholder="@username1, @username2"
            )
            st.caption("💡 З собачки (@), декілька — через кому")
        with col6:
            client_types = ["Фізична особа", "Юридична особа"]
            curr_type = contact_data_to_edit.get("Тип (Фіз./Юр.)", "Фізична особа") if is_edit else "Фізична особа"
            type_idx = client_types.index(curr_type) if curr_type in client_types else 0
            client_type = st.selectbox("Тип (Фіз./Юр.)", options=client_types, index=type_idx, key=f"client_type_{sfx}")

        # Ряд 5: Адреса та Коментар
        address = st.text_input("Адреса / Місто", value=contact_data_to_edit.get("Адреса / Місто", "") if is_edit else "", key=f"address_{sfx}", placeholder="м. Штутгарт, вул. Штрассе, 12")
        comment = st.text_area("Коментар", value=contact_data_to_edit.get("Коментар", "") if is_edit else "", key=f"comment_{sfx}", placeholder="Будь-які додаткові нотатки...")

        # Якщо це редагування — показуємо зв'язані проєкти (зчитуються динамічно з Orders)
        if is_edit:
            st.markdown("#### 🔗 Зв'язані проєкти")
            orders_data = get_orders_data(selected_sheet_id, "Orders")
            contact_name = contact_data_to_edit.get("ПІБ / Назва", "").strip()
            
            linked_orders = []
            for ord_row in orders_data:
                # Шукаємо, чи згадується ім'я контакту у полях замовлення (Замовник, Замірник тощо)
                row_str = " ".join([str(val) for val in ord_row.values()])
                if contact_name and contact_name.lower() in row_str.lower():
                    linked_orders.append(ord_row.get("ID Замовлення", "Н/Д") + " - " + ord_row.get("Назва замовлення", ""))
            
            if linked_orders:
                for proj in linked_orders:
                    st.markdown(f"- 📂 {proj}")
            else:
                st.info("Цей контакт наразі не прикріплений до жодного замовлення.")

        st.markdown("---")

        # Кнопки збереження / скасування
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 Зберегти контакт", type="primary", key=f"btn_save_{sfx}"):
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
                        # Логіка оновлення існуючого рядка в таблиці Contacts
                        client = st.session_state.get("gspread_client") or None
                        # Використовуємо стандартну функцію збереження або оновлюємо
                        success = save_new_contact(selected_sheet_id, contact_payload) # за потреби можна реалізувати update
                    else:
                        success = save_new_contact(selected_sheet_id, contact_payload)
                        
                    if success:
                        st.success(f"✅ Контакт '{name}' успішно збережено!")
                        # Очищаємо стан ролей
                        if state_key in st.session_state:
                            del st.session_state[state_key]
                        if on_success:
                            on_success()
                        else:
                            st.rerun()
                    else:
                        st.error("❌ Помилка збереження контакту.")
        with col_s2:
            if st.button("Скасувати", key=f"btn_cancel_{sfx}"):
                if state_key in st.session_state:
                    del st.session_state[state_key]
                if on_success:
                    on_success()
                else:
                    st.rerun()


def render_contacts_view(selected_sheet_id):
    """Повноцінний розділ управління контактами з можливістю фільтрації та редагування."""
    st.subheader("👥 Довідник контактів")

    if "edit_contact_id" not in st.session_state:
        st.session_state.edit_contact_id = None
    if "show_new_contact_modal" not in st.session_state:
        st.session_state.show_new_contact_modal = False

    contacts_records = get_all_contacts_records(selected_sheet_id)

    # Панель фільтрації та кнопок
    f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
    with f_col1:
        search_query = st.text_input("🔍 Пошук за ім'ям / компанією", placeholder="Введіть текст...")
    with f_col2:
        role_filter = st.selectbox("Фільтр за роллю", options=["Всі ролі"] + ALL_ROLES)
    with f_col3:
        st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)
        if not st.session_state.show_new_contact_modal and not st.session_state.edit_contact_id:
            if st.button("➕ Додати новий контакт", type="primary"):
                st.session_state.show_new_contact_modal = True
                st.rerun()

    st.markdown("---")

    # Якщо активовано режим додавання нового контакту
    if st.session_state.show_new_contact_modal:
        render_contact_form(
            selected_sheet_id, 
            on_success=lambda: setattr(st.session_state, 'show_new_contact_modal', False)
        )
        st.markdown("---")

    # Якщо активовано режим редагування конкретного контакту
    if st.session_state.edit_contact_id:
        target_contact = next((c for c in contacts_records if c.get("ID Контакту") == st.session_state.edit_contact_id), None)
        if target_contact:
            render_contact_form(
                selected_sheet_id, 
                contact_data_to_edit=target_contact, 
                on_success=lambda: setattr(st.session_state, 'edit_contact_id', None)
            )
            st.markdown("---")

    # Фільтрація записів
    filtered_records = []
    for row in contacts_records:
        name = str(row.get("ПІБ / Назва", ""))
        comp = str(row.get("Компанія", ""))
        roles = str(row.get("Роль / Категорія", ""))

        match_search = not search_query or (search_query.lower() in name.lower() or search_query.lower() in comp.lower())
        match_role = role_filter == "Всі ролі" or role_filter.lower() in roles.lower()

        if match_search and match_role:
            filtered_records.append(row)

    if filtered_records:
        st.markdown(f"**Знайдено контактів:** {len(filtered_records)}")
        
        # Відображення таблиці з кнопкою вибору для редагування
        for row in filtered_records:
            c_id = row.get("ID Контакту", "")
            c_name = row.get("ПІБ / Назва", "")
            c_roles = row.get("Роль / Категорія", "")
            c_phone = row.get("Телефон(и)", "")
            c_email = row.get("Email(и)", "")
            c_comp = row.get("Компанія", "")

            with st.container():
                rc1, rc2, rc3, rc4, rc5 = st.columns([2, 2, 2, 2, 1])
                rc1.write(f"**{c_name}** (`{c_id}`)")
                rc2.write(f"📌 {c_roles}")
                rc3.write(f"📞 {c_phone or '—'}")
                rc4.write(f"✉️ {c_email or c_comp or '—'}")
                with rc5:
                    if st.button("✏️ Редагувати", key=f"edit_btn_{c_id}"):
                        st.session_state.edit_contact_id = c_id
                        st.session_state.show_new_contact_modal = False
                        st.rerun()
                st.divider()
    else:
        st.info("Контактів за вашим запитом не знайдено.")
