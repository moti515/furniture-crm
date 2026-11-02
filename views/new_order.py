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
      order_content = st.text_area(
          "Суть/Зміст замовлення",
          placeholder="Детальний опис того, що саме необхідно зробити...",
      )
      order_type = st.multiselect(
          "Тип замовлення",
          options=[
              "Повний цикл",
              "Монтаж",
              "Готові вироби",
              "Сервіс і ремонт",
              "Проєкт",
          ],
      )

    with col2:
      # --- ЛОГІКА ІЄРАРХІЇ КРАЇНА -> МІСТО -> ОБ'ЄКТ ---
      countries = list(hierarchy.keys()) + ["Інше"]
      selected_country = st.selectbox("Країна", options=countries)

      if selected_country == "Інше":
        country_input = st.text_input("Введіть назву нової країни")
        cities = ["Інше"]
      else:
        country_input = selected_country
        cities = list(hierarchy.get(selected_country, {}).keys()) + ["Інше"]

      selected_city = st.selectbox("Місто / Ort", options=cities)

      if selected_city == "Інше":
        city_input = st.text_input("Введіть назву нового міста")
        objects = ["Інше"]
      else:
        city_input = selected_city
        objects = (
            hierarchy.get(selected_country, {}).get(selected_city, [])
            + ["Інше"]
        )

      selected_object = st.selectbox("Назва об'єкта", options=objects)

      if selected_object == "Інше":
        object_input = st.text_input("Введіть назву нового об'єкта")
      else:
        object_input = selected_object

    address = st.text_area(
        "Точна адреса монтажу",
        placeholder=(
            "Вулиця, будинок, квартира...\n💡 Підказка: якщо вище обрано"
            " 'Інше', вкажіть деталі тут."
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

    submitted = st.form_submit_button(
        "💾 Зберегти замовлення та створити папки на Диску"
    )

    if submitted:
      if not order_name or not customer:
        st.error(
            "❌ Будь ласка, заповніть обов'язкові поля: Замовник та Назва"
            " замовлення."
        )
      else:
        with st.spinner(
            "Створення папок на Google Диску та збереження даних..."
        ):
          try:
            final_country = (
                country_input
                if selected_country == "Інше"
                else selected_country
            )
            final_city = (
                city_input if selected_city == "Інше" else selected_city
            )
            final_object = (
                object_input if selected_object == "Інше" else selected_object
            )

            temp_folder_name = f"Нове замовлення - {order_name}"

            folder_link = create_order_folder_structure(
                drive_folder_id,
                final_country,
                final_city,
                final_object,
                temp_folder_name,
            )

            # Дані для збереження в таблицю Orders (з урахуванням нової колонки Суть/Зміст замовлення)
            order_payload = {
                "Замовник / Представник": customer,
                "Країна": final_country,
                "Місто / Ort": final_city,
                "Назва об'єкта": final_object,
                "Адреса": address,
                "Назва замовлення": order_name,
                "Суть/Зміст замовлення": order_content,
                "Тип замовлення": ", ".join(order_type),
                "Замірник": measurer,
                "Дизайнер": designer,
                "Конструктор": constructor,
                "Виробник": producer,
                "Монтажник": installer,
                "Інші пов'язані особи": other_persons,
                "Папка на Диску": folder_link,
            }

            new_id = save_new_order(selected_sheet_id, order_payload)

            st.success(
                f"✅ Замовлення **{new_id}** успішно створено!"
                f" [Відкрити папку на Диску]({folder_link})"
            )
            st.balloons()
          except Exception as e:
            st.error(f"❌ Помилка при збереженні замовлення: {e}")
