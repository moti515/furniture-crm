import pandas as pd
import streamlit as st
from utils.drive_service import get_drive_hierarchy
from utils.sheets_service import (
    get_all_contacts_records,
    get_orders_data,
)
from views.new_order import (
    render_order_form,
    sync_order_pickers_state,
)

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


def _is_archived_order(row: dict) -> bool:
    val = row.get("Архів", "")
    if isinstance(val, bool):
        return val
    s = str(val or "").strip().lower()
    if s in ("так", "true", "1", "yes", "архів", "в архіві"):
        return True
    for col_name in ("В архіві", "Архівне", "Статус", "Стан"):
        c_val = str(row.get(col_name, "")).strip().lower()
        if c_val in ("так", "true", "1", "yes", "архів", "в архіві") or "архів" in c_val or "archive" in c_val:
            return True
    return False


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

    pre_filtered = []
    for row in raw_orders:
        is_arch = _is_archived_order(row)
        if archive_mode == "Ні (лише активні)" and is_arch:
            continue
        if archive_mode == "Лише архів" and not is_arch:
            continue
        if selected_customer != "Всі замовники" and str(row.get("Замовник / Представник", "")).strip() != selected_customer:
            continue
        pre_filtered.append(row)

    c_col, m_col, o_col = st.columns(3)

    with c_col:
        avail_countries = sorted({str(r.get("Країна", "")).strip() for r in pre_filtered if str(r.get("Країна", "")).strip()})
        prev_country = st.session_state.get("mgr_country_filter", "Всі країни")
        country_opts = ["Всі країни"] + avail_countries
        c_index = country_opts.index(prev_country) if prev_country in country_opts else 0
        sel_country = st.selectbox("🌍 Країна", options=country_opts, index=c_index, key="mgr_country_filter")

    after_country = [
        r for r in pre_filtered
        if sel_country == "Всі країни" or str(r.get("Країна", "")).strip() == sel_country
    ]

    with m_col:
        avail_cities = sorted({str(r.get("Місто / Ort", "")).strip() for r in after_country if str(r.get("Місто / Ort", "")).strip()})
        prev_city = st.session_state.get("mgr_city_filter", "Всі міста")
        city_opts = ["Всі міста"] + avail_cities
        m_index = city_opts.index(prev_city) if prev_city in city_opts else 0
        sel_city = st.selectbox("🏙 Місто / Ort", options=city_opts, index=m_index, key="mgr_city_filter")

    after_city = [
        r for r in after_country
        if sel_city == "Всі міста" or str(r.get("Місто / Ort", "")).strip() == sel_city
    ]

    with o_col:
        avail_objects = sorted({str(r.get("Назва об'єкта", "")).strip() for r in after_city if str(r.get("Назва об'єкта", "")).strip()})
        prev_obj = st.session_state.get("mgr_object_filter", "Всі об'єкти")
        obj_opts = ["Всі об'єкти"] + avail_objects
        o_index = obj_opts.index(prev_obj) if prev_obj in obj_opts else 0
        sel_object = st.selectbox("🏢 Назва об'єкта", options=obj_opts, index=o_index, key="mgr_object_filter")

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
                sync_order_pickers_state(selected_order, key_suffix=f"edit_{selected_order_id}", force=True)
                st.rerun()
    else:
        st.info("Замовлень за заданими умовами фільтрації не знайдено.")

    if st.session_state.edit_order_id:
        target_order = next(
            (r for r in raw_orders if str(r.get("ID Замовлення", "")).strip() == st.session_state.edit_order_id),
            None,
        )
        if target_order:
            target_id = str(target_order.get("ID Замовлення", "")).strip()
            sync_order_pickers_state(target_order, key_suffix=f"edit_{target_id}", force=False)
            st.markdown("---")

            def _on_edit_done():
                st.session_state.edit_order_id = None
                st.session_state.active_linked_contact_label = None
                st.session_state.orders_table_nonce = st.session_state.get("orders_table_nonce", 0) + 1
                st.rerun()

            render_order_form(
                selected_sheet_id=selected_sheet_id,
                drive_folder_id=drive_folder_id,
                order_data_to_edit=target_order,
                key_suffix="edit",
                all_contacts_records=all_contacts_records,
                hierarchy=hierarchy,
                on_success=_on_edit_done,
            )
