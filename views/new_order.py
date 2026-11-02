from datetime import datetime
import pandas as pd
import streamlit as st
from utils.drive_service import (
    create_order_folder_structure,
    get_drive_hierarchy,
)
from utils.sheets_service import (
    get_contacts_list,
    save_new_order,
    save_new_contact,
)


def render_new_order_view(selected_sheet_id, drive_folder_id):
  st.subheader("➕ Створення нового замовлення")

  # Отримуємо актуальний список контактів з бази
  contacts = get_contacts_list(selected_sheet_id)

  # Допоміжна функція для вибору контакту з можливістю швидкого додавання нового
  def contact_selector_with_add(label, key_suffix, default_role=""):
    options = [""] + contacts + ["➕ Додати новий контакт..."]
    selected = st.selectbox(label, options=options, key=f"sel_{key_suffix}")

    if selected == "➕ Додати новий контакт...":
      st.markdown(f"**📝 Додавання нового контакту ({label})**")
      with st.expander(f"Форма нового контакту ({label})", expanded=True):
        new_name = st.text_input("ПІБ / Назва *", key=f"new_name_{key_suffix}")
        col_a, col_b = st.columns(2)
        with col_a:
          new_phone = st.text_input("Телефон", key=f"new_phone_{key_suffix}")
          new_email = st.text_input("Email", key=f"new_email_{key_suffix}")
        with col_b:
          new_role = st.text_input("Роль / Категорія", value=default_role, key=f"new_role_{key_suffix}")
          new_comment = st.text_input("Коментар", key=f"new_com_{key_suffix}")

        if st.button("💾 Зберегти контакт", key=f"btn_save_contact_{key_suffix}"):
          if not new_name:
            st.error("❌ Введіть ПІБ або назву контакту.")
          else:
            contact_data = {
                "ПІБ / Назва": new_name,
                "Роль / Категорія": new_role,
                "Телефон(и)": new_phone,
                "Email(и)": new_email,
                "Коментар": new_comment,
            }
            success = save_new_contact(selected_sheet_id, contact_data)
            if success:
              st.success(f"✅ Контакт '{new_name}' успішно додано!")
              st.rerun()
            else:
              st.error("❌ Помилка збереження контакту.")
      return ""
    return selected

  # Завантаження ієрархії папок з Google Drive
  with st.spinner("Завантаження ієрархії папок з Google Диску..."):
    try:
      hierarchy, _ = get_drive_hierarchy(drive_folder_id)
    except Exception as e:
      st.error(f"Помилка доступу до Google Диску: {e}")
      hierarchy = {}

  with st.form("new_order_form"):
    st.markdown("### 📌 Основна інформація")
    
    col1, col2 = st.columns(2)
    with col1:
      customer = contact_selector_with_add("Замовник / Представник *", "customer", "Замовник")
      order_name = st.text_input(
          "Назва замовлення *",
          placeholder="Напр., Кухня фасади МДФ фарбовані",
      )
    with col2:
      order_content = st.text_area(
          "Суть/Зміст замовлення",
          placeholder="Детальний опис того, що саме необхідно зробити...",
          height=105
      )

    st.markdown("---")
    st.markdown("### 📍 Локація та адреса виконання замовлення")
    
    loc_col1, loc_col2, loc_col3 = st.columns(3)
    with loc_col1:
      countries = list(hierarchy.keys()) + ["Інше"]
      selected_country = st.selectbox("Країна", options=countries)
    with loc_col2:
      cities = list(hierarchy.get(selected_country, {}).keys()) + ["Інше"] if selected_country != "Інше" else ["Інше"]
      selected_city = st.selectbox("Місто / Ort", options=cities)
    with loc_col3:
      objects = (
          hierarchy.get(selected_country, {}).get(selected_city, []) + ["Інше"]
          if selected_country != "Інше" and selected_city != "Інше"
          else ["Інше"]
      )
      selected_object = st.selectbox("Назва об'єкта", options=objects)

    address = st.text_area(
        "Адреса виконання замовлення",
        placeholder=(
            "Вулиця, будинок, квартира...\n💡 Підказка: якщо вище не вказано"
            " точну країну, місто чи об'єкт (обрано 'Інше'), обов'язково вкажіть їх тут"
            " та нагадайте адміністратору про необхідність коригування."
        ),
    )

    st.markdown("---")
    st.markdown("### 👥 Відповідальні особи")
    col3, col4, col5 = st.columns(3)
    with col3:
      measurer = contact_selector_with_add("Замірник", "measurer", "Замірник")
      designer = contact_selector_with_add("Дизайнер", "designer", "Дизайнер")
    with col4:
      constructor = contact_selector_with_add("Конструктор", "constructor", "Конструктор")
      producer = contact_selector_with_add("Виробник", "producer", "Виробник")
    with col5:
      installer = contact_selector_with_add("Монтажник", "installer", "Монтажник")
      other_persons = st.text_input("Інші пов'язані особи")

    st.markdown("---")
    st.markdown("### ⚙️ Типи замовлення та етапи конвеєра")
    
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
      chk_measuring = st.checkbox("Заміри")
      chk_design = st.checkbox("Розробка дизайну")
    with t_col2:
      chk_constructor = st.checkbox("Розробка конструктиву")
      chk_production = st.checkbox("Виготовлення")
    with t_col3:
      chk_installation = st.checkbox("Монтаж")
      chk_delivery_goods = st.checkbox("Поставка готових виробів і фурнітури")
    
    chk_service = st.checkbox("Сервіс і Ремонт")

    # Збираємо список активних типів замовлення для запису в комірку
    active_types = []
    if chk_measuring: active_types.append("Заміри")
    if chk_design: active_types.append("Розробка дизайну")
    if chk_constructor: active_types.append("Розробка конструктиву")
    if chk_production: active_types.append("Виготовлення")
    if chk_installation: active_types.append("Монтаж")
    if chk_delivery_goods: active_types.append("Поставка готових виробів і фурнітури")
    if chk_service: active_types.append("Сервіс і Ремонт")

    # Динамічні поля статусів і коментарів на основі вибраних чекбоксів
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

    submitted = st.form_submit_button(
        "💾 Зберегти замовлення та створити папки на Диску"
    )

    if submitted:
      if not order_name or not customer:
        st.error(
            "❌ Будь ласка, заповніть обов'язкові поля: Замовник та Назва замовлення."
        )
      else:
        with st.spinner(
            "Створення папок на Google Диску та збереження даних..."
        ):
          try:
            # Якщо вибрано "Інше", передаємо це значення у структуру папок (створиться папка "Інше")
            final_country = selected_country
            final_city = selected_city
            final_object = selected_object

            temp_folder_name = f"Нове замовлення - {order_name}"

            folder_link = create_order_folder_structure(
                drive_folder_id,
                final_country,
                final_city,
                final_object,
                temp_folder_name,
            )

            # Формуємо словник даних для запису в Orders
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

            # Додаємо статусні поля і коментарі, які були активовані через чекбокси
            order_payload.update(order_payload_extras)

            new_id = save_new_order(selected_sheet_id, order_payload)

            st.success(
                f"✅ Замовлення **{new_id}** успішно створено!"
                f" [Відкрити папку на Диску]({folder_link})"
            )
            st.balloons()
          except Exception as e:
            st.error(f"❌ Помилка при збереженні замовлення: {e}")
