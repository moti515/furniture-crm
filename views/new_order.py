import streamlit as st
from utils.drive_service import (
    create_order_folder_structure,
    get_drive_hierarchy,
)
from utils.sheets_service import (
    get_all_contacts_records,
    save_new_order,
    save_new_contact,
)

ALL_ROLES = ["Замовник", "Замірник", "Дизайнер", "Конструктор", "Виробник", "Монтажник", "Інше"]


def render_new_order_view(selected_sheet_id, drive_folder_id):
    st.subheader("➕ Створення нового замовлення")

    if "order_success_msg" in st.session_state and st.session_state.order_success_msg:
        st.success(st.session_state.order_success_msg)
        st.balloons()
        st.session_state.order_success_msg = ""

    # Зчитуємо всі контакти 1 раз за запит сторінки
    all_contacts_records = get_all_contacts_records(selected_sheet_id)

    def filter_contacts_by_role(role_filter=""):
        contacts = []
        for row in all_contacts_records:
            name = str(row.get("ПІБ / Назва", "")).strip()
            roles_str = str(row.get("Роль / Категорія", "")).strip()

            if name:
                if role_filter:
                    roles_list = [r.strip().lower() for r in roles_str.split(",")]
                    if role_filter.lower() in roles_list:
                        contacts.append(name)
                else:
                    contacts.append(name)
        return sorted(list(set(contacts)))

    def contact_multi_selector(label, key_suffix, role_filter=""):
        contacts = filter_contacts_by_role(role_filter=role_filter)
        
        col_sel, col_btn = st.columns([4, 1])
        with col_sel:
            selected = st.multiselect(
                label,
                options=contacts,
                key=f"sel_{key_suffix}"
            )
        with col_btn:
            st.write(" ")
            st.write(" ")
            add_clicked = st.button("➕ Новий", key=f"btn_add_mode_{key_suffix}")

        if add_clicked or st.session_state.get(f"show_add_{key_suffix}", False):
            st.session_state[f"show_add_{key_suffix}"] = True
            st.info(f"📝 **Додавання нового контакту ({label})**")
            with st.expander(f"Форма контакту ({label})", expanded=True):
                new_name = st.text_input("ПІБ / Назва *", key=f"new_name_{key_suffix}")
                col_a, col_b = st.columns(2)
                with col_a:
                    new_phone = st.text_input("Телефон", key=f"new_phone_{key_suffix}")
                    new_email = st.text_input("Email", key=f"new_email_{key_suffix}")
                with col_b:
                    default_roles = [role_filter] if role_filter and role_filter in ALL_ROLES else []
                    new_roles = st.multiselect(
                        "Роль / Категорія *",
                        options=ALL_ROLES,
                        default=default_roles,
                        key=f"new_roles_{key_suffix}"
                    )
                    st.caption("💡 Для додавання інших категорій зверніться до адміністратора.")
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
                                st.session_state[f"show_add_{key_suffix}"] = False
                                st.success(f"✅ Контакт '{new_name}' успішно додано!")
                                st.rerun()
                            else:
                                st.error("❌ Помилка збереження контакту.")
                with col_s2:
                    if st.button("Скасувати", key=f"btn_cancel_{key_suffix}setItem"):
                        st.session_state[f"show_add_{key_suffix}"] = False
                        st.rerun()

        return ", ".join(selected)

    # 2. Сканування ієрархії Google Drive
    with st.spinner("Завантаження ієрархії папок з Google Диску..."):
        try:
            hierarchy, _ = get_drive_hierarchy(drive_folder_id)
        except Exception as e:
            st.error(f"Помилка доступу до Google Диску: {e}")
            hierarchy = {}

    # --- 📌 ОСНОВНА ІНФОРМАЦІЯ ---
    st.markdown("### 📌 Основна інформація")
    col1, col2 = st.columns(2)
    with col1:
        customer = contact_multi_selector("Замовник / Представник *", "customer", "Замовник")
        order_name = st.text_input(
            "Назва замовлення *",
            placeholder="Напр., Кухня фасади МДФ фарбовані",
            key="order_name_val"
        )
    with col2:
        order_content = st.text_area(
            "Суть/Зміст замовлення",
            placeholder="Детальний опис того, що саме необхідно зробити...",
            height=125,
            key="order_content_val"
        )

    st.markdown("---")

    # --- 📍 ЛОКАЦІЯ ТА АДРЕСА ---
    st.markdown("### 📍 Локація та адреса виконання замовлення")
    loc_col1, loc_col2, loc_col3 = st.columns(3)
    with loc_col1:
        countries = list(hierarchy.keys()) + ["Інше"]
        selected_country = st.selectbox("Країна", options=countries, key="sel_country")
    with loc_col2:
        cities = list(hierarchy.get(selected_country, {}).keys()) + ["Інше"] if selected_country != "Інше" else ["Інше"]
        selected_city = st.selectbox("Місто / Ort", options=cities, key="sel_city")
    with loc_col3:
        objects = (
            hierarchy.get(selected_country, {}).get(selected_city, []) + ["Інше"]
            if selected_country != "Інше" and selected_city != "Інше"
            else ["Інше"]
        )
        selected_object = st.selectbox("Назва об'єкта", options=objects, key="sel_object")

    address = st.text_area(
        "Адреса виконання замовлення",
        placeholder=(
            "Вулиця, будинок, квартира...\n💡 Підказка: якщо вище не вказано"
            " точну країну, місто чи об'єкт (обрано 'Інше'), обов'язково вкажіть їх тут"
            " та нагадайте адміністратору про необхідність коригування."
        ),
        key="address_val"
    )

    st.markdown("---")

    # --- 👥 ВІДПОВІДАЛЬНІ ОСОБИ ---
    st.markdown("### 👥 Відповідальні особи")
    col3, col4, col5 = st.columns(3)
    with col3:
        measurer = contact_multi_selector("Замірник", "measurer", "Замірник")
        designer = contact_multi_selector("Дизайнер", "designer", "Дизайнер")
    with col4:
        constructor = contact_multi_selector("Конструктор", "constructor", "Конструктор")
        producer = contact_multi_selector("Виробник", "producer", "Виробник")
    with col5:
        installer = contact_multi_selector("Монтажник", "installer", "Монтажник")
        other_persons = contact_multi_selector("Інші пов'язані особи", "other_persons", "")

    st.markdown("---")

    # --- ⚙️ ТИПИ ЗАМОВЛЕННЯ ТА ЕТАПИ КОНВЕЄРА ---
    st.markdown("### ⚙️ Типи замовлення та етапи конвеєра")
    
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        chk_measuring = st.checkbox("Заміри", key="chk_m")
        chk_design = st.checkbox("Розробка дизайну", key="chk_d")
    with t_col2:
        chk_constructor = st.checkbox("Розробка конструктиву", key="chk_c")
        chk_production = st.checkbox("Виготовлення", key="chk_p")
    with t_col3:
        chk_installation = st.checkbox("Монтаж", key="chk_i")
        chk_delivery_goods = st.checkbox("Поставка готових виробів і фурнітури", key="chk_dg")
    
    chk_service = st.checkbox("Сервіс і Ремонт", key="chk_s")

    active_types = []
    if chk_measuring: active_types.append("Заміри")
    if chk_design: active_types.append("Розробка дизайну")
    if chk_constructor: active_types.append("Розробка конструктиву")
    if chk_production: active_types.append("Виготовлення")
    if chk_installation: active_types.append("Монтаж")
    if chk_delivery_goods: active_types.append("Поставка готових виробів і фурнітури")
    if chk_service: active_types.append("Сервіс і Ремонт")

    order_payload_extras = {}

    if chk_measuring:
        st.markdown("📐 **Етап: Заміри**")
        mc1, mc2 = st.columns(2)
        with mc1: order_payload_extras["Заміри статус"] = st.selectbox("Заміри статус", ["в роботі", "перевіряються", "готово"], key="s_meas")
        with mc2: order_payload_extras["Заміри коментар"] = st.text_input("Заміри коментар", key="c_meas")

    if chk_design:
        st.markdown("🎨 **Етап: Розробка дизайну**")
        dc1, dc2 = st.columns(2)
        with dc1: order_payload_extras["Дизайн статус"] = st.selectbox("Дизайн статус", ["в роботі", "перевіряються", "на погодженні", "готово"], key="s_des")
        with dc2: order_payload_extras["Дизайн коментар"] = st.text_input("Дизайн коментар", key="c_des")

    if chk_constructor:
        st.markdown("🛠 **Етап: Розробка конструктиву**")
        cc1, cc2 = st.columns(2)
        with cc1: order_payload_extras["Конструктив статус"] = st.selectbox("Конструктив статус", ["в роботі", "перевіряються", "готово"], key="s_con")
        with cc2: order_payload_extras["Конструктив коментар"] = st.text_input("Конструктив коментар", key="c_con")

    if chk_production:
        st.markdown("🏭 **Етап: Виготовлення**")
        pc1, pc2 = st.columns(2)
        with pc1: order_payload_extras["Виробництво статус"] = st.selectbox("Виробництво статус", ["в роботі", "перевіряються", "готово"], key="s_prod")
        with pc2: order_payload_extras["Виробництво коментар"] = st.text_input("Виробництво коментар", key="c_prod")

    if chk_installation or chk_service:
        st.markdown("🔧 **Етап: Монтаж**")
        ic1, ic2 = st.columns(2)
        with ic1: order_payload_extras["Монтаж статус"] = st.selectbox("Монтаж статус", ["в роботі", "перевіряються", "готово"], key="s_inst")
        with ic2: order_payload_extras["Монтаж коментар"] = st.text_input("Монтаж коментар", key="c_inst")

    if chk_production or chk_installation or chk_delivery_goods:
        st.markdown("🚚 **Етап: Доставка**")
        doc1, doc2 = st.columns(2)
        with doc1: order_payload_extras["Доставка статус"] = st.selectbox("Доставка статус", ["відвантажено", "розвантаження", "готово"], key="s_del")
        with doc2: order_payload_extras["Доставка коментар"] = st.text_input("Доставка коментар", key="c_del")

    st.markdown("---")

    # --- 💾 ЗБЕРЕЖЕННЯ ---
    if st.button("Зберегти нове замовлення", type="primary", use_container_width=True):
        if not order_name or not customer:
            st.error("❌ Будь ласка, заповніть обов'язкові поля: Замовник та Назва замовлення.")
        else:
            with st.spinner("Створення папок на Google Диску та збереження даних..."):
                try:
                    final_country = selected_country
                    final_city = selected_city
                    final_object = selected_object

                    folder_link = create_order_folder_structure(
                        drive_folder_id,
                        final_country,
                        final_city,
                        final_object,
                        order_name,
                    )

                    order_payload = {
                        "Замовник / Представник": customer,
                        "Країна": final_country,
                        "Місто / Ort": final_city,
                        "Назва об'єкта": final_object,
                        "Адреса": address,
                        "Назва замовлення": order_name,
                        "Суть/Зміст замовлення": order_content,
                        "Тип замовлення": ", ".join(active_types),
                        "Замірник": measurer,
                        "Дизайнер": designer,
                        "Конструктор": constructor,
                        "Виробник": producer,
                        "Монтажник": installer,
                        "Інші пов'язані особи": other_persons,
                        "Папка на Диску": folder_link,
                    }

                    order_payload.update(order_payload_extras)

                    new_id = save_new_order(selected_sheet_id, order_payload)

                    if new_id:
                        st.session_state.order_success_msg = f"✅ Замовлення **{new_id}** успішно створено! [Відкрити папку на Диску]({folder_link})"

                        keys_to_clear = [
                            "order_name_val", "order_content_val", "address_val",
                            "sel_country", "sel_city", "sel_object",
                            "sel_customer", "sel_measurer", "sel_designer",
                            "sel_constructor", "sel_producer", "sel_installer", "sel_other_persons",
                            "chk_m", "chk_d", "chk_c", "chk_p", "chk_i", "chk_dg", "chk_s",
                            "s_meas", "c_meas", "s_des", "c_des", "s_con", "c_con",
                            "s_prod", "c_prod", "s_inst", "c_inst", "s_del", "c_del"
                        ]
                        for k in keys_to_clear:
                            if k in st.session_state:
                                del st.session_state[k]

                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Помилка при збереженні замовлення: {e}")
