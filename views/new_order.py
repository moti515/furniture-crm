from datetime import datetime
import streamlit as st
from utils.drive_service import (
    create_order_folder_structure,
    get_drive_hierarchy,
    sync_order_drive_folder,
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

STANDARD_FORM_FIELDS = {
    "ID Замовлення",
    "Архів",
    "Час створення",
    "Час останнього редагування",
    "Замовник / Представник",
    "Країна",
    "Місто / Ort",
    "Адреса",
    "Назва об'єкта",
    "Назва замовлення",
    "Суть/Зміст замовлення",
    "Пов'язані замовлення",
    "Поточний статус",
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
    "КП / специфікація статус",
    "КП коментар",
    "Виробництво статус",
    "Виробництво коментар",
    "Доставка статус",
    "Доставка коментар",
    "Монтаж статус",
    "Монтаж коментар",
    "Звіт / відгук статус",
    "Звіт / відгук коментар",
}

PICKER_MAPPING = {
    "customer": "Замовник / Представник",
    "measurer": "Замірник",
    "designer": "Дизайнер",
    "constructor": "Конструктор",
    "producer": "Виробник",
    "installer": "Монтажник",
    "other_persons": "Інші пов'язані особи",
}


def _parse_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _is_archived_value(val) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val or "").strip().lower()
    return s in ("так", "true", "1", "yes", "архів", "в архіві")


def _extract_contact_name_and_id(contact_label: str) -> tuple[str, str]:
    label = contact_label.strip()
    if label.endswith(")") and "(" in label:
        name_part, id_part = label.rsplit("(", 1)
        return name_part.strip(), id_part[:-1].strip()
    return label, ""


def _find_contact_record(contact_label: str, all_contacts_records: list[dict]) -> dict:
    name_part, id_part = _extract_contact_name_and_id(contact_label)
    for rec in all_contacts_records or []:
        rec_id = str(rec.get("ID Контакту", "")).strip()
        rec_name = str(rec.get("ПІБ / Назва", "")).strip()
        if id_part and rec_id == id_part:
            return rec
        if name_part and rec_name.lower() == name_part.lower():
            return rec
    return {"ID Контакту": id_part, "ПІБ / Назва": name_part or contact_label}


def sync_order_pickers_state(order_row: dict | None, key_suffix: str, force: bool = False):
    """Синхронізує picked_contacts_* та пов'язані замовлення у session_state."""
    for suffix, col_name in PICKER_MAPPING.items():
        st_key = f"picked_contacts_{key_suffix}_{suffix}"
        if order_row is None:
            if force or st_key not in st.session_state:
                st.session_state[st_key] = []
        else:
            if force or st_key not in st.session_state:
                st.session_state[st_key] = _parse_list(order_row.get(col_name, ""))

    rel_key = f"related_orders_{key_suffix}"
    if order_row is None:
        if force or rel_key not in st.session_state:
            st.session_state[rel_key] = []
    else:
        if force or rel_key not in st.session_state:
            st.session_state[rel_key] = _parse_list(order_row.get("Пов'язані замовлення", ""))


def _open_related_order_in_edit(target_oid: str):
    st.session_state.edit_order_id = target_oid
    st.session_state.nav_menu = "📋 Актуальні замовлення"
    st.query_params["edit_order"] = target_oid
    st.rerun()


def _render_related_orders_section(
    selected_sheet_id: str,
    sfx: str,
    current_order_id: str = "",
    all_orders_records: list[dict] | None = None,
) -> list[str]:
    """Блок відображення та вибору пов'язаних замовлень з міні-менеджером."""
    st.markdown("#### 🔗 Пов'язані замовлення")
    rel_state_key = f"related_orders_{sfx}"
    if rel_state_key not in st.session_state:
        st.session_state[rel_state_key] = []

    selected_rel: list[str] = list(st.session_state[rel_state_key])

    if selected_rel:
        st.caption("Натисніть на пов'язане замовлення, щоб відкрити його в режимі редагування:")
        rel_cols = st.columns(min(len(selected_rel), 3))
        for idx, item_label in enumerate(selected_rel):
            oid_part = item_label.split("—")[0].strip() if "—" in item_label else item_label.strip()
            with rel_cols[idx % len(rel_cols)]:
                btn_c1, btn_c2 = st.columns([4, 1])
                with btn_c1:
                    if st.button(
                        f"📄 {item_label}",
                        key=f"open_rel_order_{sfx}_{idx}_{oid_part}",
                        width="stretch",
                    ):
                        _open_related_order_in_edit(oid_part)
                with btn_c2:
                    if st.button(
                        "✖",
                        key=f"rm_rel_order_{sfx}_{idx}_{oid_part}",
                        help="Прибрати зі зв'язаних",
                    ):
                        updated_list = [x for x in st.session_state[rel_state_key] if x != item_label]
                        st.session_state[rel_state_key] = updated_list
                        st.rerun()
    else:
        st.caption("Пов'язані замовлення ще не обрано.")

    toggle_key = f"chk_add_related_orders_{sfx}"
    add_rel_enabled = st.checkbox(
        "Додати пов'язані замовлення",
        value=st.session_state.get(toggle_key, False),
        key=toggle_key,
    )

    if add_rel_enabled:
        if all_orders_records is None:
            all_orders_records = get_orders_data(selected_sheet_id, "Orders") or []

        candidates = [
            r for r in all_orders_records
            if str(r.get("ID Замовлення", "")).strip()
            and str(r.get("ID Замовлення", "")).strip() != current_order_id
        ]

        with st.container(border=True):
            st.markdown("**🔎 Підбір пов'язаних замовлень**")
            f_c1, f_c2, f_c3 = st.columns([1.5, 2, 2])
            with f_c1:
                rel_arch_mode = st.selectbox(
                    "Архів",
                    options=["Приховати архів", "Показати архів", "Лише архів"],
                    index=0,
                    key=f"rel_arch_{sfx}",
                )
            with f_c2:
                rel_search = st.text_input(
                    "Пошук (ID, назва, об'єкт)",
                    key=f"rel_search_{sfx}",
                ).strip().lower()
            with f_c3:
                rel_customers = sorted(
                    {
                        str(r.get("Замовник / Представник", "")).strip()
                        for r in candidates
                        if str(r.get("Замовник / Представник", "")).strip()
                    }
                )
                rel_cust = st.selectbox(
                    "Замовник",
                    options=["Всі замовники"] + rel_customers,
                    key=f"rel_cust_{sfx}",
                )

            filtered_rel = []
            for r in candidates:
                arch_flag = _is_archived_value(r.get("Архів", ""))
                if rel_arch_mode == "Приховати архів" and arch_flag:
                    continue
                if rel_arch_mode == "Лише архів" and not arch_flag:
                    continue
                if rel_cust != "Всі замовники" and str(r.get("Замовник / Представник", "")).strip() != rel_cust:
                    continue
                if rel_search:
                    blob = " ".join(
                        str(r.get(k, ""))
                        for k in ("ID Замовлення", "Назва замовлення", "Назва об'єкта", "Місто / Ort", "Замовник / Представник")
                    ).lower()
                    if rel_search not in blob:
                        continue
                filtered_rel.append(r)

            if not filtered_rel:
                st.info("За вказаними фільтрами замовлень не знайдено.")
            else:
                for r in filtered_rel[:25]:
                    oid = str(r.get("ID Замовлення", "")).strip()
                    oname = str(r.get("Назва замовлення", "")).strip()
                    obj_name = str(r.get("Назва об'єкта", "")).strip()
                    label = f"{oid} — {oname}" if oname else oid
                    is_checked = label in st.session_state[rel_state_key]

                    row_c1, row_c2 = st.columns([5, 1])
                    with row_c1:
                        checked_now = st.checkbox(
                            f"**{label}** ({obj_name or 'без об\'єкта'})",
                            value=is_checked,
                            key=f"rel_chk_{sfx}_{oid}",
                        )
                        if checked_now and label not in st.session_state[rel_state_key]:
                            st.session_state[rel_state_key].append(label)
                            st.rerun()
                        elif not checked_now and label in st.session_state[rel_state_key]:
                            st.session_state[rel_state_key] = [
                                x for x in st.session_state[rel_state_key] if x != label
                            ]
                            st.rerun()
                    with row_c2:
                        if st.button("✏️ Відкрити", key=f"rel_edit_btn_{sfx}_{oid}"):
                            _open_related_order_in_edit(oid)

    return st.session_state[rel_state_key]


def _render_linked_persons_section(order_row: dict, all_contacts_records: list[dict], selected_sheet_id: str, sfx: str):
    """Активні кнопки пов'язаних осіб для переходу до картки контакту."""
    st.markdown("#### 👤 Пов'язані особи (натисніть для відкриття картки контакту)")
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
        for person_label in _parse_list(order_row.get(col_name, "")):
            linked_entries.append((short_role, person_label))

    if not linked_entries:
        st.info("До цього замовлення ще не прикріплено пов'язаних осіб.")
        return

    cols = st.columns(min(len(linked_entries), 3))
    for idx, (short_role, person_label) in enumerate(linked_entries):
        with cols[idx % len(cols)]:
            if st.button(
                f"👤 {short_role}: {person_label}",
                key=f"open_linked_contact_{sfx}_{idx}_{person_label}",
                width="stretch",
            ):
                st.session_state.active_linked_contact_label = person_label
                st.rerun()

    active_label = st.session_state.get("active_linked_contact_label")
    if active_label:
        st.markdown("---")
        with st.container(border=True):
            top_c1, top_c2 = st.columns([5, 1])
            with top_c1:
                st.markdown(f"### 📇 Картка пов'язаної особи: **{active_label}**")
            with top_c2:
                if st.button("⬅️ Назад до замовлення", key=f"close_linked_{sfx}", width="stretch"):
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
                default_role="",
                key_suffix=f"linked_order_{sfx}_{active_label}",
                on_success=_on_contact_done,
            )


def render_order_form(
    selected_sheet_id: str,
    drive_folder_id: str,
    order_data_to_edit: dict | None = None,
    key_suffix: str = "new",
    all_contacts_records: list[dict] | None = None,
    all_orders_records: list[dict] | None = None,
    hierarchy: dict | None = None,
    on_success=None,
):
    """Єдина форма створення та редагування замовлення з параметрами режиму."""
    is_edit = order_data_to_edit is not None
    order_row = order_data_to_edit or {}
    order_id = str(order_row.get("ID Замовлення", "")).strip()
    sfx = f"{key_suffix}_{order_id}" if (is_edit and order_id) else key_suffix

    if all_contacts_records is None:
        all_contacts_records = get_all_contacts_records(selected_sheet_id) or []

    if hierarchy is None:
        with st.spinner("Завантаження ієрархії папок з Google Диску..."):
            try:
                hierarchy, _ = get_drive_hierarchy(drive_folder_id)
            except Exception as e:
                st.error(f"Помилка доступу до Google Диску: {e}")
                hierarchy = {}

    if is_edit:
        order_title = str(order_row.get("Назва замовлення", "")).strip()
        header_c1, header_c2 = st.columns([5, 1])
        with header_c1:
            st.subheader(f"✏️ Редагування замовлення: {order_title or order_id}")
        with header_c2:
            if st.button("✖️ Закрити форму", key=f"btn_close_order_{sfx}", width="stretch"):
                if callable(on_success):
                    on_success()
                else:
                    st.rerun()

        folder_url = str(order_row.get("Папка на Диску", "")).strip()
        if folder_url:
            st.link_button("📂 Відкрити папку замовлення на Google Диску", folder_url)
        else:
            st.caption("📂 Посилання на папку Google Диску відсутнє.")

        _render_linked_persons_section(order_row, all_contacts_records, selected_sheet_id, sfx)
        st.markdown("---")

    st.markdown("### 📌 Основна інформація")
    label_style = "font-size: 1.05rem; font-weight: 700; margin-bottom: 0.3rem; display: block;"

    if is_edit:
        meta_c1, meta_c2, meta_c3 = st.columns(3)
        with meta_c1:
            st.text_input(
                "ID Замовлення",
                value=order_id,
                disabled=True,
                key=f"oid_{sfx}",
            )
        with meta_c2:
            st.text_input(
                "Час створення",
                value=str(order_row.get("Час створення", "")),
                disabled=True,
                key=f"created_at_{sfx}",
            )
        with meta_c3:
            st.text_input(
                "Час останнього редагування",
                value=str(order_row.get("Час останнього редагування", "")),
                disabled=True,
                key=f"updated_at_{sfx}",
            )

        st.text_input(
            "Поточний статус",
            value=str(order_row.get("Поточний статус", "Нове замовлення")),
            disabled=True,
            key=f"current_status_{sfx}",
        )

    is_archived_default = _is_archived_value(order_row.get("Архів", False)) if is_edit else False
    chk_archive = st.checkbox(
        "Архів",
        value=is_archived_default,
        key=f"chk_archive_{sfx}",
        help="Позначає замовлення як архівне для фільтрації у менеджері замовлень та звітності.",
    )

    with st.container(border=True):
        customer = render_contact_picker(
            "Замовник / Представник *",
            f"{sfx}_customer",
            "Замовник",
            selected_sheet_id=selected_sheet_id,
            all_contacts_records=all_contacts_records,
        )

    st.markdown(f'<span style="{label_style}">Назва замовлення *</span>', unsafe_allow_html=True)
    order_name = st.text_input(
        "Назва замовлення *",
        value=str(order_row.get("Назва замовлення", "")),
        placeholder="Напр., Кухня фасади МДФ фарбовані",
        key=f"order_name_{sfx}",
        label_visibility="collapsed",
    )

    st.markdown(f'<span style="{label_style}">Суть/Зміст замовлення</span>', unsafe_allow_html=True)
    order_content = st.text_area(
        "Суть/Зміст замовлення",
        value=str(order_row.get("Суть/Зміст замовлення", "")),
        placeholder="Детальний опис того, що саме необхідно зробити...",
        height=125,
        key=f"order_content_{sfx}",
        label_visibility="collapsed",
    )

    related_orders_list = _render_related_orders_section(
        selected_sheet_id=selected_sheet_id,
        sfx=sfx,
        current_order_id=order_id,
        all_orders_records=all_orders_records,
    )

    st.markdown("---")
    st.markdown("### 📍 Локація та адреса виконання замовлення")

    curr_country = str(order_row.get("Країна", "")).strip()
    curr_city = str(order_row.get("Місто / Ort", "")).strip()
    curr_object = str(order_row.get("Назва об'єкта", "")).strip()

    loc_col1, loc_col2, loc_col3 = st.columns(3)
    with loc_col1:
        countries = list(hierarchy.keys()) + ["Інше"]
        if curr_country and curr_country not in countries:
            countries = [curr_country] + countries
        c_idx = countries.index(curr_country) if curr_country in countries else 0
        selected_country = st.selectbox("Країна", options=countries, index=c_idx, key=f"sel_country_{sfx}")

    with loc_col2:
        cities = (
            list(hierarchy.get(selected_country, {}).keys()) + ["Інше"]
            if selected_country != "Інше"
            else ["Інше"]
        )
        if is_edit and curr_city and curr_city not in cities and selected_country == curr_country:
            cities = [curr_city] + cities
        prev_city = st.session_state.get(f"sel_city_{sfx}")
        if prev_city and prev_city not in cities:
            st.session_state[f"sel_city_{sfx}"] = cities[0]
        city_idx = cities.index(curr_city) if curr_city in cities else 0
        selected_city = st.selectbox("Місто / Ort", options=cities, index=city_idx, key=f"sel_city_{sfx}")

    with loc_col3:
        objects = (
            hierarchy.get(selected_country, {}).get(selected_city, []) + ["Інше"]
            if selected_country != "Інше" and selected_city != "Інше"
            else ["Інше"]
        )
        if is_edit and curr_object and curr_object not in objects and (selected_country, selected_city) == (curr_country, curr_city):
            objects = [curr_object] + objects
        prev_obj = st.session_state.get(f"sel_object_{sfx}")
        if prev_obj and prev_obj not in objects:
            st.session_state[f"sel_object_{sfx}"] = objects[0]
        obj_idx = objects.index(curr_object) if curr_object in objects else 0
        selected_object = st.selectbox("Назва об'єкта", options=objects, index=obj_idx, key=f"sel_object_{sfx}")

    address = st.text_area(
        "Адреса виконання замовлення",
        value=str(order_row.get("Адреса", "")),
        placeholder=(
            "Вулиця, будинок, квартира...\n💡 Підказка: якщо вище не вказано"
            " точну країну, місто чи об'єкт (обрано 'Інше'), обов'язково вкажіть їх тут"
            " та нагадайте адміністратору про необхідність коригування."
        ),
        key=f"address_{sfx}",
    )

    st.markdown("---")
    st.markdown("### 👥 Відповідальні особи")

    col3, col4, col5 = st.columns(3)
    with col3:
        with st.container(border=True):
            measurer = render_contact_picker(
                "Замірник", f"{sfx}_measurer", "Замірник",
                selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records,
            )
        with st.container(border=True):
            designer = render_contact_picker(
                "Дизайнер", f"{sfx}_designer", "Дизайнер",
                selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records,
            )
    with col4:
        with st.container(border=True):
            constructor = render_contact_picker(
                "Конструктор", f"{sfx}_constructor", "Конструктор",
                selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records,
            )
        with st.container(border=True):
            producer = render_contact_picker(
                "Виробник", f"{sfx}_producer", "Виробник",
                selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records,
            )
    with col5:
        with st.container(border=True):
            installer = render_contact_picker(
                "Монтажник", f"{sfx}_installer", "Монтажник",
                selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records,
            )
        with st.container(border=True):
            other_persons = render_contact_picker(
                "Інші пов'язані особи", f"{sfx}_other_persons", "",
                selected_sheet_id=selected_sheet_id, all_contacts_records=all_contacts_records,
            )

    st.markdown("---")
    st.markdown("### ⚙️ Типи замовлення та етапи конвеєра")

    existing_types = _parse_list(order_row.get("Тип замовлення", ""))

    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        chk_measuring = st.checkbox("Заміри", value="Заміри" in existing_types, key=f"chk_m_{sfx}")
        chk_design = st.checkbox("Розробка дизайну", value="Розробка дизайну" in existing_types, key=f"chk_d_{sfx}")
    with t_col2:
        chk_constructor = st.checkbox("Розробка конструктиву", value="Розробка конструктиву" in existing_types, key=f"chk_c_{sfx}")
        chk_production = st.checkbox("Виготовлення", value="Виготовлення" in existing_types, key=f"chk_p_{sfx}")
    with t_col3:
        chk_installation = st.checkbox("Монтаж", value="Монтаж" in existing_types, key=f"chk_i_{sfx}")
        chk_delivery_goods = st.checkbox(
            "Поставка готових виробів і фурнітури",
            value="Поставка готових виробів і фурнітури" in existing_types,
            key=f"chk_dg_{sfx}",
        )

    chk_service = st.checkbox("Сервіс і Ремонт", value="Сервіс і Ремонт" in existing_types, key=f"chk_s_{sfx}")

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
                "Заміри статус", opts_m, index=opts_m.index(curr_sm) if curr_sm in opts_m else 0, key=f"s_meas_{sfx}"
            )
        with mc2:
            order_payload_extras["Заміри коментар"] = st.text_input(
                "Заміри коментар", value=str(order_row.get("Заміри коментар", "")), key=f"c_meas_{sfx}"
            )

    if chk_design:
        st.markdown("🎨 **Етап: Розробка дизайну**")
        dc1, dc2 = st.columns(2)
        opts_d = ["в роботі", "перевіряються", "на погодженні", "готово"]
        curr_sd = str(order_row.get("Дизайн статус", "в роботі"))
        with dc1:
            order_payload_extras["Дизайн статус"] = st.selectbox(
                "Дизайн статус", opts_d, index=opts_d.index(curr_sd) if curr_sd in opts_d else 0, key=f"s_des_{sfx}"
            )
        with dc2:
            order_payload_extras["Дизайн коментар"] = st.text_input(
                "Дизайн коментар", value=str(order_row.get("Дизайн коментар", "")), key=f"c_des_{sfx}"
            )

    if chk_constructor:
        st.markdown("🛠 **Етап: Розробка конструктиву**")
        cc1, cc2 = st.columns(2)
        opts_c = ["в роботі", "перевіряються", "готово"]
        curr_sc = str(order_row.get("Конструктив статус", "в роботі"))
        with cc1:
            order_payload_extras["Конструктив статус"] = st.selectbox(
                "Конструктив статус", opts_c, index=opts_c.index(curr_sc) if curr_sc in opts_c else 0, key=f"s_con_{sfx}"
            )
        with cc2:
            order_payload_extras["Конструктив коментар"] = st.text_input(
                "Конструктив коментар", value=str(order_row.get("Конструктив коментар", "")), key=f"c_con_{sfx}"
            )

    if chk_production:
        st.markdown("🏭 **Етап: Виготовлення**")
        pc1, pc2 = st.columns(2)
        opts_p = ["в роботі", "перевіряються", "готово"]
        curr_sp = str(order_row.get("Виробництво статус", "в роботі"))
        with pc1:
            order_payload_extras["Виробництво статус"] = st.selectbox(
                "Виробництво статус", opts_p, index=opts_p.index(curr_sp) if curr_sp in opts_p else 0, key=f"s_prod_{sfx}"
            )
        with pc2:
            order_payload_extras["Виробництво коментар"] = st.text_input(
                "Виробництво коментар", value=str(order_row.get("Виробництво коментар", "")), key=f"c_prod_{sfx}"
            )

    if chk_installation or chk_service:
        st.markdown("🔧 **Етап: Монтаж**")
        ic1, ic2 = st.columns(2)
        opts_i = ["в роботі", "перевіряються", "готово"]
        curr_si = str(order_row.get("Монтаж статус", "в роботі"))
        with ic1:
            order_payload_extras["Монтаж статус"] = st.selectbox(
                "Монтаж статус", opts_i, index=opts_i.index(curr_si) if curr_si in opts_i else 0, key=f"s_inst_{sfx}"
            )
        with ic2:
            order_payload_extras["Монтаж коментар"] = st.text_input(
                "Монтаж коментар", value=str(order_row.get("Монтаж коментар", "")), key=f"c_inst_{sfx}"
            )

    if chk_production or chk_installation or chk_delivery_goods:
        st.markdown("🚚 **Етап: Доставка**")
        doc1, doc2 = st.columns(2)
        opts_del = ["відвантажено", "розвантаження", "готово"]
        curr_sdel = str(order_row.get("Доставка статус", "відвантажено"))
        with doc1:
            order_payload_extras["Доставка статус"] = st.selectbox(
                "Доставка статус", opts_del, index=opts_del.index(curr_sdel) if curr_sdel in opts_del else 0, key=f"s_del_{sfx}"
            )
        with doc2:
            order_payload_extras["Доставка коментар"] = st.text_input(
                "Доставка коментар", value=str(order_row.get("Доставка коментар", "")), key=f"c_del_{sfx}"
            )

    if is_edit:
        extra_table_fields = [k for k in order_row.keys() if k not in STANDARD_FORM_FIELDS]
        if extra_
