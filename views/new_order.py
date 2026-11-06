import streamlit as st
from utils.drive_service import (
    create_order_folder_structure,
    get_drive_hierarchy,
)
from utils.sheets_service import (
    get_all_contacts_records,
    save_new_order,
)
from views.contacts_manager import render_contact_picker


def render_new_order_view(selected_sheet_id, drive_folder_id):
    st.subheader("➕ Створення нового замовлення")

    if "order_success_msg" in st.session_state and st.session_state.order_success_msg:
        st.success(st.session_state.order_success_msg)
        st.balloons()
        st.session_state.order_success_msg = ""

    all_contacts_records = get_all_contacts_records(selected_sheet_id)

    with st.spinner("Завантаження ієрархії папок з Google Диску..."):
        try:
            hierarchy, _ = get_drive_hierarchy(drive_folder_id)
        except Exception as e:
            st.error(f"Помилка доступу до Google Диску: {e}")
            hierarchy = {}

    st.markdown("### 📌 Основна інформація")
    
    label_style = "font-size: 1.05rem; font-weight: 700; margin-bottom: 0.3rem; display: block;"

    # Розтягуємо основну інформацію на всю ширину екрана (без стовпців)
    with st.container(border=True):
        customer = render_contact_picker(
            "Замовник / Представник *", "customer", "Замовник", 
            selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records
        )
    
    st.markdown(f'<span style="{label_style}">Назва замовлення *</span>', unsafe_allow_html=True)
    order_name = st.text_input(
        "Назва замовлення *",
        placeholder="Напр., Кухня фасади МДФ фарбовані",
        key="order_name_val",
        label_visibility="collapsed"
    )
    
    st.markdown(f'<span style="{label_style}">Суть/Зміст замовлення</span>', unsafe_allow_html=True)
    order_content = st.text_area(
        "Суть/Зміст замовлення",
        placeholder="Детальний опис того, що саме необхідно зробити...",
        height=125,
        key="order_content_val",
        label_visibility="collapsed"
    )

    st.markdown("---")

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

    st.markdown("### 👥 Відповідальні особи")
    col3, col4, col5 = st.columns(3)
    with col3:
        with st.container(border=True):
            measurer = render_contact_picker("Замірник", "measurer", "Замірник", selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records)
        with st.container(border=True):
            designer = render_contact_picker("Дизайнер", "designer", "Дизайнер", selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records)
    with col4:
        with st.container(border=True):
            constructor = render_contact_picker("Конструктор", "constructor", "Конструктор", selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records)
        with st.container(border=True):
            producer = render_contact_picker("Виробник", "producer", "Виробник", selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records)
    with col5:
        with st.container(border=True):
            installer = render_contact_picker("Монтажник", "installer", "Монтажник", selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records)
        with st.container(border=True):
            other_persons = render_contact_picker("Інші пов'язані особи", "other_persons", "", selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records)

    st.markdown("---")

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

    if st.button("Зберегти нове замовлення", type="primary", use_container_width=True):
        if not order_name or not customer:
            st.error("❌ Будь ласка, заповніть обов'язкові поля: Замовник та Назва замовлення.")
        else:
            with st.spinner("Створення папок на Google Диску та збереження даних..."):
                try:
                    folder_link = create_order_folder_structure(
                        drive_folder_id,
                        selected_country,
                        selected_city,
                        selected_object,
                        order_name,
                    )

                    order_payload = {
                        "Замовник / Представник": customer,
                        "Країна": selected_country,
                        "Місто / Ort": selected_city,
                        "Назва об'єкта": selected_object,
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
                            "chk_m", "chk_d", "chk_c", "chk_p", "chk_i", "chk_dg", "chk_s",
                            "s_meas", "c_meas", "s_des", "c_des", "s_con", "c_con",
                            "s_prod", "c_prod", "s_inst", "c_inst", "s_del", "c_del"
                        ]
                        for k in keys_to_clear:
                            if k in st.session_state:
                                del st.session_state[k]
                                
                        # Очищаємо обрані контакти в state
                        for suffix in ["customer", "measurer", "designer", "constructor", "producer", "installer", "other_persons"]:
                            st_key = f"picked_contacts_{suffix}"
                            if st_key in st.session_state:
                                st.session_state[st_key] = []

                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Помилка при збереженні замовлення: {e}")
