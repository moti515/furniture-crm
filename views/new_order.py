import pandas as pd
import streamlit as st
from utils.drive_service import (
    create_order_folder_structure,
    get_drive_hierarchy,
)
from utils.sheets_service import get_contacts_list, save_new_order


def render_new_order_view(selected_sheet_id, drive_folder_id):
  st.subheader("➕ Створення нового замовлення")

  # 1. Перевірка наявності контактів
  contacts = get_contacts_list(selected_sheet_id)
  if not contacts:
    st.warning(
        "⚠️ У базі ще немає жодного контакту. Будь ласка, додайте замовника в"
        " розділі '👥 Контакти'."
    )
    if st.button(" перейти до Контактів"):
      st.session_state["navigation"] = "👥 Контакти"
      st.rerun()
    return

  # 2. Отримання ієрархії папок з Google Drive
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
      customer = st.selectbox(
          "Замовник / Представник *",
          options=contacts,
          help="Оберіть особу з довідника контактів",
      )
      order_name = st.text_input(
          "Назва замовлення *",
          placeholder="Напр., Кухня фасади МДФ фарбовані",
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
      measurer = st.selectbox("Замірник", options=[""] + contacts)
      designer = st.selectbox("Дизайнер", options=[""] + contacts)
    with col4:
      constructor = st.selectbox("Конструктор", options=[""] + contacts)
      producer = st.selectbox("Виробник", options=[""] + contacts)
    with col5:
      installer = st.selectbox("Монтажник", options=[""] + contacts)
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
            # Визначаємо фінальні назви для папок з урахуванням 'Інше'
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

            # Формуємо тимчасове ID або назву для папки замовлення
            temp_folder_name = f"Нове замовлення - {order_name}"

            # Створюємо структуру папок на Диску
            folder_link = create_order_folder_structure(
                drive_folder_id,
                final_country,
                final_city,
                final_object,
                temp_folder_name,
            )

            # Дані для збереження в таблицю Orders
            order_payload = {
                "Замовник / Представник": customer,
                "Країна": final_country,
                "Місто / Ort": final_city,
                "Назва об'єкта": final_object,
                "Адреса": address,
                "Назва замовлення": order_name,
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

            # Перейменовуємо папку на Диску, додаючи згенерований ID
            # (можна реалізувати виклик перейменування через drive_service за потреби)

            st.success(
                f"✅ Замовлення **{new_id}** успішно створено!"
                f" [Відкрити папку на Диску]({folder_link})"
            )
            st.balloons()
          except Exception as e:
            st.error(f"❌ Помилка при збереженні замовлення: {e}")
