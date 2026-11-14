import pandas as pd
import streamlit as st
from utils.drive_service import (
    create_order_folder_structure,
    get_drive_hierarchy,
)
from utils.sheets_service import (
    get_all_contacts_records,
    get_orders_data,
    save_new_order,
)
from views.contacts_manager import (
    render_contact_form,
    render_contact_picker,
)

# Основні поля для текстового пошуку
SEARCH_FIELDS = [
    "ID Замовлення",
    "Назва замовлення",
    "Суть/Зміст замовлення",
    "Замовник / Представник",
    "Країна",
    "Місто / Ort",
    "Назва об'єкта",
    "Адреса",
    "Тип замовлення",
    "Замірник",
    "Дизайнер",
    "Конструктор",
    "Виробник",
    "Монтажник",
    "Інші пов'язані особи",
]

# Поля, які вже виводяться в основних секціях форми редагування
STANDARD_FORM_FIELDS = {
    "ID Замовлення",
    "Замовник / Представник",
    "Країна",
    "Місто / Ort",
    "Назва об'єкта",
    "Адреса",
    "Назва замовлення",
    "Суть/Зміст замовлення",
    "Тип замовлення",
    "Замірник",
    "Дизайнер",
    "Конструктор",
    "Виробник",
    "Монтажник",
    "Інші пов'язані особи",
    "Папка на Диску",
    "Заміри статус",
    "Заміри коментар",
    "Дизайн статус",
    "Дизайн коментар",
    "Конструктив статус",
    "Конструктив коментар",
    "Виробництво статус",
    "Виробництво коментар",
    "Монтаж статус",
    "Монтаж коментар",
    "Доставка статус",
    "Доставка коментар",
}


def _is_archived_order(row: dict) -> bool:
    """Визначає, чи є замовлення архівним за можливими колонками статусу/архіву."""
    for col_name in ("Архів", "В архіві", "Архівне", "Статус", "Стан"):
        val = str(row.get(col_name, "")).strip().lower()
        if not val:
            continue
        if col_name in ("Архів", "В архіві", "Архівне"):
            if val in ("так", "true", "1", "yes", "архів", "в архіві"):
                return True
        else:
            if "архів" in val or "archive" in val:
                return True
    return False


def _parse_contact_list(value: str) -> list[str]:
    """Розбиває рядок пов'язаних осіб (через кому) на список чистих значень."""
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _extract_contact_name_and_id(contact_label: str) -> tuple[str, str]:
    """Витягує ім'я та ID контакту з рядка вигляду 'Ім'я (ID-123)' або просто 'Ім'я'."""
    label = contact_label.strip()
    if label.endswith(")") and "(" in label:
        name_part, id_part = label.rsplit("(", 1)
        return name_part.strip(), id_part[:-1].strip()
    return label, ""


def _find_contact_record(contact_label: str, all_contacts_records: list[dict]) -> dict:
    """Шукає запис контакту в базі контактів за ID або ПІБ."""
    name_part, id_part = _extract_contact_name_and_id(contact_label)
    for rec in all_contacts_records or []:
        rec_id = str(rec.get("ID Контакту", "")).strip()
        rec_name = str(rec.get("ПІБ / Назва", "")).strip()
        if id_part and rec_id == id_part:
            return rec
        if name_part and rec_name.lower() == name_part.lower():
            return rec
    # Якщо контакту немає в довіднику — повертаємо мінімальний шаблон для перегляду/створення
    return {
        "ID Контакту": id_part,
        "ПІБ / Назва": name_part or contact_label,
    }


def _sync_picked_contacts_from_order(order_row: dict, force: bool = False):
    """Заповнює session_state для render_contact_picker значеннями з поточного замовлення."""
    mapping = {
        "customer": "Замовник / Представник",
        "measurer": "Замірник",
        "designer": "Дизайнер",
        "constructor": "Конструктор",
        "producer": "Виробник",
        "installer": "Монтажник",
        "other_persons": "Інші пов'язані особи",
    }
    for suffix, col_name in mapping.items():
        st_key = f"picked_contacts_{suffix}"
        if force or st_key not in st.session_state:
            st.session_state[st_key] = _parse_contact_list(order_row.get(col_name, ""))


def _render_linked_persons_bar(order_row: dict, all_contacts_records: list[dict], selected_sheet_id: str):
    """Рендерить активні кнопки пов'язаних осіб для переходу до картки/форми контакту."""
    st.markdown("#### 🔗 Пов'язані особи (натисніть для відкриття картки контакту)")
    st.caption("💡 Натисніть на особу, щоб відкрити форму редагування контакту.")

    role_fields = [
        ("Замовник", "Замовник / Представник"),
        ("Замірник", "Замірник"),
        ("Дизайнер", "Дизайнер"),
        ("Конструктор", "Конструктор"),
        ("Виробник", "Виробник"),
        ("Монтажник", "Монтажник"),
        ("Інші", "Інші пов'язані особи"),
    ]

    linked_entries = []
    for short_role, col_name in role_fields:
        for person_label in _parse_contact_list(order_row.get(col_name, "")):
            linked_entries.append((short_role, person_label))

    if not linked_entries:
        st.info("До цього замовлення ще не прикріплено пов'язаних осіб.")
        return

    cols = st.columns(min(len(linked_entries), 3))
    for idx, (short_role, person_label) in enumerate(linked_entries):
        with cols[idx % len(cols)]:
            btn_key = f"open_linked_contact_{idx}_{person_label}"
            if st.button(f"👤 {short_role}: {person_label}", key=btn_key, width="stretch"):
                st.session_state.active_linked_contact_label = person_label
                st.rerun()

    # Якщо користувач натиснув на пов'язану особу — відкриваємо форму редагування контакту
    active_label = st.session_state.get("active_linked_contact_label")
    if active_label:
        st.markdown("---")
        with st.container(border=True):
            top_c1, top_c2 = st.columns([5, 1])
            with top_c1:
                st.markdown(f"### 📇 Картка пов'язаної особи: **{active_label}**")
            with top_c2:
                if st.button("⬅️ Назад до замовлення", key="close_linked_contact_btn", width="stretch"):
                    st.session_state.active_linked_contact_label = None
                    st.rerun()

            contact_rec = _find_contact_record(active_label, all_contacts_records)
            has_real_id = bool(str(contact_rec.get("ID Контакту", "")).strip())

            def _on_contact_done():
                st.session_state.active_linked_contact_label = None
                st.rerun()

            render_contact_form(
                selected_sheet_id=selected_sheet_id,
                contact_data_to_edit=contact_rec if has_real_id else None,
                default_role="" if has_real_id else "",
                key_suffix=f"linked_order_{active_label}",
                on_success=_on_contact_done,
            )


def _render_order_edit_form(
    order_row: dict,
    selected_sheet_id: str,
    drive_folder_id: str,
    all_contacts_records: list[dict],
    hierarchy: dict,
):
    """Форма редагування замовлення — аналогічна new_order.py, але з усіма полями таблиці."""
    order_id = str(order_row.get("ID Замовлення", "")).strip()
    order_title = str(order_row.get("Назва замовлення", "")).strip()

    st.markdown("---")
    header_c1, header_c2 = st.columns([5, 1])
    with header_c1:
        st.subheader(f"✏️ Редагування замовлення: {order_title or order_id}")
    with header_c2:
        if st.button("✖️ Закрити форму", key="btn_close_order_edit", width="stretch"):
            st.session_state.edit_order_id = None
            st.session_state.active_linked_contact_label = None
            st.session_state.orders_table_nonce = st.session_state.get("orders_table_nonce", 0) + 1
            st.rerun()

    # Посилання на папку Google Диску — активне та відкривається в новій вкладці
    folder_url = str(order_row.get("Папка на Диску", "")).strip()
    if folder_url:
        st.link_button("📂 Відкрити папку замовлення на Google Диску", folder_url)
    else:
        st.caption("📂 Посилання на папку Google Диску відсутнє.")

    # Активні пов'язані особи (клік відкриває форму редагування контакту)
    _render_linked_persons_bar(order_row, all_contacts_records, selected_sheet_id)

    st.markdown("---")
    st.markdown("### 📌 Основна інформація")

    label_style = "font-size: 1.05rem; font-weight: 700; margin-bottom: 0.3rem; display: block;"

    if order_id:
        st.text_input("ID Замовлення", value=order_id, disabled=True, key=f"edit_oid_{order_id}")

    with st.container(border=True):
        customer = render_contact_picker(
            "Замовник / Представник *",
            f"edit_customer_{order_id}",
            "Замовник",
            selected_sheet_id=selected_sheet_id,
            all_contacts_records=all_contacts_records,
        )

    st.markdown(f'<span style="{label_style}">Назва замовлення *</span>', unsafe_allow_html=True)
    order_name = st.text_input(
        "Назва замовлення *",
        value=str(order_row.get("Назва замовлення", "")),
        key=f"edit_order_name_{order_id}",
        label_visibility="collapsed",
    )

    st.markdown(f'<span style="{label_style}">Суть/Зміст замовлення</span>', unsafe_allow_html=True)
    order_content = st.text_area(
        "Суть/Зміст замовлення",
        value=str(order_row.get("Суть/Зміст замовлення", "")),
        height=125,
        key=f"edit_order_content_{order_id}",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 📍 Локація та адреса виконання замовлення")

    loc_col1, loc_col2, loc_col3 = st.columns(3)
    curr_country = str(order_row.get("Країна", "")).strip()
    curr_city = str(order_row.get("Місто / Ort", "")).strip()
    curr_object = str(order_row.get("Назва об'єкта", "")).strip()

    with loc_col1:
        countries = list(hierarchy.keys()) + ["Інше"]
        if curr_country and curr_country not in countries:
            countries = [curr_country] + countries
        c_idx = countries.index(curr_country) if curr_country in countries else 0
        selected_country = st.selectbox("Країна", options=countries, index=c_idx, key=f"edit_sel_country_{order_id}")

    with loc_col2:
        cities = (
            list(hierarchy.get(selected_country, {}).keys()) + ["Інше"]
            if selected_country != "Інше"
            else ["Інше"]
        )
        if curr_city and curr_city not in cities:
            cities = [curr_city] + cities
        city_idx = cities.index(curr_city) if curr_city in cities else 0
        selected_city = st.selectbox("Місто / Ort", options=cities, index=city_idx, key=f"edit_sel_city_{order_id}")

    with loc_col3:
        objects = (
            hierarchy.get(selected_country, {}).get(selected_city, []) + ["Інше"]
            if selected_country != "Інше" and selected_city != "Інше"
            else ["Інше"]
        )
        if curr_object and curr_object not in objects:
            objects = [curr_object] + objects
        obj_idx = objects.index(curr_object) if curr_object in objects else 0
        selected_object = st.selectbox("Назва об'єкта", options=objects, index=obj_idx, key=f"edit_sel_object_{order_id}")

    address = st.text_area(
        "Адреса виконання замовлення",
        value=str(order_row.get("Адреса", "")),
        key=f"edit_address_{order_id}",
    )

    st.markdown("---")
    st.markdown("### 👥 Відповідальні особи")

    col3, col4, col5 = st.columns(3)
    with col3:
        with st.container(border=True):
            measurer = render_contact_picker(
                "Замірник",
                f"edit_measurer_{order_id}",
                "Замірник",
                selected_sheet_id=selected_sheet_id,
                all_contacts_records=all_contacts_records,
            )
        with st.container(border=True):
            designer = render_contact_picker(
                "Дизайнер",
                f"edit_designer_{order_id}",
                "Дизайнер",
                selected_sheet_id=selected_sheet_id,
                all_contacts_records=all_contacts_records,
            )
    with col4:
        with st.container(border=True):
            constructor = render_contact_picker(
                "Конструктор",
                f"edit_constructor_{order_id}",
                "Конструктор",
                selected_sheet_id=selected_sheet_id,
                all_contacts_records=all_contacts_records,
            )
        with st.container(border=True):
            producer = render_contact_picker(
                "Виробник",
                f"edit_producer_{order_id}",
                "Виробник",
                selected_sheet_id=selected_sheet_id,
                all_contacts_records=all_contacts_records,
            )
    with col5:
        with st.container(border=True):
            installer = render_contact_picker(
                "Монтажник",
                f"edit_installer_{order_id}",
                "Монтажник",
                selected_sheet_id=selected_sheet_id,
                all_contacts_records=all_contacts_records,
            )
        with st.container(border=True):
            other_persons = render_contact_picker(
                "Інші пов'язані особи",
                f"edit_other_persons_{order_id}",
                "",
                selected_sheet_id=selected_sheet_id,
                all_contacts_records=all_contacts_records,
            )

    st.markdown("---")
    st.markdown("### ⚙️ Типи замовлення та етапи конвеєра")

    existing_types = _parse_contact_list(order_row.get("Тип замовлення", ""))

    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        chk_measuring = st.checkbox("Заміри", value="Заміри" in existing_types, key=f"edit_chk_m_{order_id}")
        chk_design = st.checkbox("Розробка дизайну", value="Розробка дизайну" in existing_types, key=f"edit_chk_d_{order_id}")
    with t_col2:
        chk_constructor = st.checkbox("Розробка конструктиву", value="Розробка конструктиву" in existing_types, key=f"edit_chk_c_{order_id}")
        chk_production = st.checkbox("Виготовлення", value="Виготовлення" in existing_types, key=f"edit_chk_p_{order_id}")
    with t_col3:
        chk_installation = st.checkbox("Монтаж", value="Монтаж" in existing_types, key=f"edit_chk_i_{order_id}")
        chk_delivery_goods = st.checkbox(
            "Поставка готових виробів і фурнітури",
            value="Поставка готових виробів і фурнітури" in existing_types,
            key=f"edit_chk_dg_{order_id}",
        )

    chk_service = st.checkbox("Сервіс і Ремонт", value="Сервіс і Ремонт" in existing_types, key=f"edit_chk_s_{order_id}")

    active_types = []
    if chk_measuring:
        active_types.append("Заміри")
    if chk_design:
        active_types.append("Розробка дизайну")
    if chk_constructor:
        active_types.append("Розробка конструктиву")
    if chk_production:
        active_types.append("Виготовлення")
    if chk_installation:
        active_types.append("Монтаж")
    if chk_delivery_goods:
        active_types.append("Поставка готових виробів і фурнітури")
    if chk_service:
        active_types.append("Сервіс і Ремонт")

    order_payload_extras = {}

    if chk_measuring:
        st.markdown("📐 **Етап: Заміри**")
        mc1, mc2 = st.columns(2)
        opts_m = ["в роботі", "перевіряються", "готово"]
        curr_sm = str(order_row.get("Заміри статус", "в роботі"))
        with mc1:
            order_payload_extras["Заміри статус"] = st.selectbox(
                "Заміри статус",
                opts_m,
                index=opts_m.index(curr_sm) if curr_sm in opts_m else 0,
                key=f"edit_s_meas_{order_id}",
            )
        with mc2:
            order_payload_extras["Заміри коментар"] = st.text_input(
                "Заміри коментар",
                value=str(order_row.get("Заміри коментар", "")),
                key=f"edit_c_meas_{order_id}",
            )

    if chk_design:
        st.markdown("🎨 **Етап: Розробка дизайну**")
        dc1, dc2 = st.columns(2)
        opts_d = ["в роботі", "перевіряються", "на погодженні", "готово"]
        curr_sd = str(order_row.get("Дизайн статус", "в роботі"))
        with dc1:
            order_payload_extras["Дизайн статус"] = st.selectbox(
                "Дизайн статус",
                opts_d,
                index=opts_d.index(curr_sd) if curr_sd in opts_d else 0,
                key=f"edit_s_des_{order_id}",
            )
        with dc2:
            order_payload_extras["Дизайн коментар"] = st.text_input(
                "Дизайн коментар",
                value=str(order_row.get("Дизайн коментар", "")),
                key=f"edit_c_des_{order_id}",
            )

    if chk_constructor:
        st.markdown("🛠 **Етап: Розробка конструктиву**")
        cc1, cc2 = st.columns(2)
        opts_c = ["в роботі", "перевіряються", "готово"]
        curr_sc = str(order_row.get("Конструктив статус", "в роботі"))
        with cc1:
            order_payload_extras["Конструктив статус"] = st.selectbox(
                "Конструктив статус",
                opts_c,
                index=opts_c.index(curr_sc) if curr_sc in opts_c else 0,
                key=f"edit_s_con_{order_id}",
            )
        with cc2:
            order_payload_extras["Конструктив коментар"] = st.text_input(
                "Конструктив коментар",
                value=str(order_row.get("Конструктив коментар", "")),
                key=f"edit_c_con_{order_id}",
            )

    if chk_production:
        st.markdown("🏭 **Етап: Виготовлення**")
        pc1, pc2 = st.columns(2)
        opts_p = ["в роботі", "перевіряються", "готово"]
        curr_sp = str(order_row.get("Виробництво статус", "в роботі"))
        with pc1:
            order_payload_extras["Виробництво статус"] = st.selectbox(
                "Виробництво статус",
                opts_p,
                index=opts_p.index(curr_sp) if curr_sp in opts_p else 0,
                key=f"edit_s_prod_{order_id}",
            )
        with pc2:
            order_payload_extras["Виробництво коментар"] = st.text_input(
                "Виробництво коментар",
                value=str(order_row.get("Виробництво коментар", "")),
                key=f"edit_c_prod_{order_id}",
            )

    if chk_installation or chk_service:
        st.markdown("🔧 **Етап: Монтаж**")
        ic1, ic2 = st.columns(2)
        opts_i = ["в роботі", "перевіряються", "готово"]
        curr_si = str(order_row.get("Монтаж статус", "в роботі"))
        with ic1:
            order_payload_extras["Монтаж статус"] = st.selectbox(
                "Монтаж статус",
                opts_i,
                index=opts_i.index(curr_si) if curr_si in opts_i else 0,
                key=f"edit_s_inst_{order_id}",
            )
        with ic2:
            order_payload_extras["Монтаж коментар"] = st.text_input(
                "Монтаж коментар",
                value=str(order_row.get("Монтаж коментар", "")),
                key=f"edit_c_inst_{order_id}",
            )

    if chk_production or chk_installation or chk_delivery_goods:
        st.markdown("🚚 **Етап: Доставка**")
        doc1, doc2 = st.columns(2)
        opts_del = ["відвантажено", "розвантаження", "готово"]
        curr_sdel = str(order_row.get("Доставка статус", "відвантажено"))
        with doc1:
            order_payload_extras["Доставка статус"] = st.selectbox(
                "Доставка статус",
                opts_del,
                index=opts_del.index(curr_sdel) if curr_sdel in opts_del else 0,
                key=f"edit_s_del_{order_id}",
            )
        with doc2:
            order_payload_extras["Доставка коментар"] = st.text_input(
                "Доставка коментар",
                value=str(order_row.get("Доставка коментар", "")),
                key=f"edit_c_del_{order_id}",
            )

    # Усі інші колонки з таблиці Orders, які не входять до стандартних секцій
    extra_table_fields = [k for k in order_row.keys() if k not in STANDARD_FORM_FIELDS]
    if extra_table_fields:
        st.markdown("---")
        st.markdown("### 📋 Додаткові поля таблиці")
        extra_cols = st.columns(2)
        for idx, field_name in enumerate(extra_table_fields):
            with extra_cols[idx % 2]:
                order_payload_extras[field_name] = st.text_input(
                    field_name,
                    value=str(order_row.get(field_name, "")),
                    key=f"edit_extra_{order_id}_{field_name}",
                )

    st.markdown("---")

    btn_c1, btn_c2 = st.columns(2)
    with btn_c1:
        if st.button("💾 Зберегти зміни замовлення", type="primary", key=f"btn_save_order_{order_id}", width="stretch"):
            if not order_name or not customer:
                st.error("❌ Будь ласка, заповніть обов'язкові поля: Замовник та Назва замовлення.")
            else:
                with st.spinner("Оновлення даних замовлення..."):
                    try:
                        updated_folder_link = folder_url
                        if not updated_folder_link and drive_folder_id:
                            updated_folder_link = create_order_folder_structure(
                                drive_folder_id,
                                selected_country,
                                selected_city,
                                selected_object,
                                order_name,
                            )

                        order_payload = {
                            "ID Замовлення": order_id,
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
                            "Папка на Диску": updated_folder_link,
                        }
                        order_payload.update(order_payload_extras)

                        save_new_order(selected_sheet_id, order_payload)
                        st.session_state.edit_order_id = None
                        st.session_state.active_linked_contact_label = None
                        st.session_state.orders_table_nonce = st.session_state.get("orders_table_nonce", 0) + 1
                        st.success(f"✅ Замовлення **{order_id}** успішно оновлено!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Помилка при збереженні замовлення: {e}")

    with btn_c2:
        if st.button("Скасувати", key=f"btn_cancel_order_{order_id}", width="stretch"):
            st.session_state.edit_order_id = None
            st.session_state.active_linked_contact_label = None
            st.session_state.orders_table_nonce = st.session_state.get("orders_table_nonce", 0) + 1
            st.rerun()


def render_manager_orders_view(selected_sheet_id: str, drive_folder_id: str):
    """Інтерфейс управління замовленнями для менеджерів (аналогічно contacts_manager.py)."""
    st.subheader("📋 Актуальні замовлення")

    if "edit_order_id" not in st.session_state:
        st.session_state.edit_order_id = None
    if "orders_table_nonce" not in st.session_state:
        st.session_state.orders_table_nonce = 0

    raw_orders = get_orders_data(selected_sheet_id, "Orders") or []
    all_contacts_records = get_all_contacts_records(selected_sheet_id) or []

    try:
        hierarchy, _ = get_drive_hierarchy(drive_folder_id)
    except Exception:
        hierarchy = {}

    if not raw_orders:
        st.info("У цій базі замовлення відсутні або аркуш 'Orders' порожній.")
        return

    # --- ВЕРХНІЙ БЛОК ФІЛЬТРІВ ---
    top_f1, top_f2, top_f3 = st.columns([1.5, 2, 2])
    with top_f1:
        archive_mode = st.selectbox(
            "Відображати архів?",
            options=["Ні (лише активні)", "Так (всі замовлення)", "Лише архів"],
            index=0,
            key="mgr_archive_selector",
        )
    with top_f2:
        search_query = st.text_input(
            "🔍 Пошук по основних полях",
            placeholder="ID, назва, замовник, адреса, виконавці...",
            key="mgr_search_query",
        )
    with top_f3:
        all_customers = sorted(
            {
                str(r.get("Замовник / Представник", "")).strip()
                for r in raw_orders
                if str(r.get("Замовник / Представник", "")).strip()
            }
        )
        selected_customer = st.selectbox(
            "Фільтр за замовником",
            options=["Всі замовники"] + all_customers,
            index=0,
            key="mgr_customer_filter",
        )

    # --- КАСКАДНИЙ ФІЛЬТР КРАЇНА -> МІСТО -> ОБ'ЄКТ ---
    # Спочатку фільтруємо за архівом та замовником, щоб каскад показував релевантні значення
    pre_filtered = []
    for row in raw_orders:
        is_arch = _is_archived_order(row)
        if archive_mode == "Ні (лише активні)" and is_arch:
            continue
        if archive_mode == "Лише архів" and not is_arch:
            continue

        if selected_customer != "Всі замовники":
            if str(row.get("Замовник / Представник", "")).strip() != selected_customer:
                continue

        pre_filtered.append(row)

    c_col, m_col, o_col = st.columns(3)

    with c_col:
        avail_countries = sorted(
            {str(r.get("Країна", "")).strip() for r in pre_filtered if str(r.get("Країна", "")).strip()}
        )
        prev_country = st.session_state.get("mgr_country_filter", "Всі країни")
        country_opts = ["Всі країни"] + avail_countries
        c_index = country_opts.index(prev_country) if prev_country in country_opts else 0
        sel_country = st.selectbox("🌍 Країна", options=country_opts, index=c_index, key="mgr_country_filter")

    after_country = [
        r for r in pre_filtered
        if sel_country == "Всі країни" or str(r.get("Країна", "")).strip() == sel_country
    ]

    with m_col:
        avail_cities = sorted(
            {str(r.get("Місто / Ort", "")).strip() for r in after_country if str(r.get("Місто / Ort", "")).strip()}
        )
        prev_city = st.session_state.get("mgr_city_filter", "Всі міста")
        city_opts = ["Всі міста"] + avail_cities
        m_index = city_opts.index(prev_city) if prev_city in city_opts else 0
        sel_city = st.selectbox("🏙 Місто / Ort", options=city_opts, index=m_index, key="mgr_city_filter")

    after_city = [
        r for r in after_country
        if sel_city == "Всі міста" or str(r.get("Місто / Ort", "")).strip() == sel_city
    ]

    with o_col:
        avail_objects = sorted(
            {str(r.get("Назва об'єкта", "")).strip() for r in after_city if str(r.get("Назва об'єкта", "")).strip()}
        )
        prev_obj = st.session_state.get("mgr_object_filter", "Всі об'єкти")
        obj_opts = ["Всі об'єкти"] + avail_objects
        o_index = obj_opts.index(prev_obj) if prev_obj in obj_opts else 0
        sel_object = st.selectbox("🏢 Назва об'єкта", options=obj_opts, index=o_index, key="mgr_object_filter")

    # Фінальна фільтрація таблиці
    filtered_orders = []
    q_lower = search_query.strip().lower()
    for row in after_city:
        if sel_object != "Всі об'єкти" and str(row.get("Назва об'єкта", "")).strip() != sel_object:
            continue

        if q_lower:
            haystack = " ".join(str(row.get(f, "")) for f in SEARCH_FIELDS).lower()
            if q_lower not in haystack:
                continue

        filtered_orders.append(row)

    st.markdown("---")

    if filtered_orders:
        df = pd.DataFrame(filtered_orders).astype(str)

        st.caption(
            "💡 **Порада:** Відмітьте галочкою будь-який рядок у таблиці нижче, щоб відкрити замовлення в режимі редагування."
        )

        table_key = f"manager_orders_table_{st.session_state.orders_table_nonce}"

        column_cfg = {}
        if "Папка на Диску" in df.columns:
            column_cfg["Папка на Диску"] = st.column_config.LinkColumn(
                "Папка на Диску",
                display_text="Відкрити папку",
            )

        event = st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config=column_cfg,
            key=table_key,
        )

        selected_rows = event.selection.get("rows", [])
        if selected_rows:
            selected_idx = selected_rows[0]
            selected_order = filtered_orders[selected_idx]
            selected_order_id = str(selected_order.get("ID Замовлення", "")).strip()

            if st.session_state.edit_order_id != selected_order_id:
                st.session_state.edit_order_id = selected_order_id
                st.session_state.active_linked_contact_label = None
                _sync_picked_contacts_from_order(selected_order, force=True)
                st.rerun()
    else:
        st.info("Замовлень за заданими умовами фільтрації не знайдено.")

    # --- ФОРМА РЕДАГУВАННЯ ОБРАНОГО ЗАМОВЛЕННЯ ---
    if st.session_state.edit_order_id:
        target_order = next(
            (r for r in raw_orders if str(r.get("ID Замовлення", "")).strip() == st.session_state.edit_order_id),
            None,
        )
        if target_order:
            _sync_picked_contacts_from_order(target_order, force=False)
            _render_order_edit_form(
                order_row=target_order,
                selected_sheet_id=selected_sheet_id,
                drive_folder_id=drive_folder_id,
                all_contacts_records=all_contacts_records,
                hierarchy=hierarchy,
            )
