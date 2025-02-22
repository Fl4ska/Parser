from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import re
from Database import Database


def load_cities_from_json(file_path):
    """
    Загружает данные о городах из JSON файла.

    Аргументы:
    - file_path (str): Путь к JSON файлу.

    Возвращает:
    - cities (dict): Словарь с данными о городах.
    """
    with open(file_path, encoding='utf-8') as f:
        cities = json.load(f)  # Загрузка данных из JSON файла
    return cities


def find_data(driver, url):
    """
    Извлекает данные со страницы, используя веб-драйвер Selenium.

    Аргументы:
    - driver (WebDriver): Веб-драйвер Selenium.
    - url (str): URL-адрес страницы для извлечения данных.

    Возвращает:
    - sections (list): Список секций на странице.
    """
    driver.get(url)  # Переход по указанному URL-адресу
    sections = driver.find_elements(By.XPATH, "//main//section")  # Поиск всех секций на странице
    return sections


def extract_product_info(product):
    """
    Извлекает информацию о товаре из элемента страницы.

    Аргументы:
    - product (WebElement): Элемент товара на странице.

    Возвращает:
    - title (str): Заголовок товара.
    - icon (str): Ссылка на иконку товара.
    """
    try:
        if product.find_elements(By.XPATH, ".//img"):  # Проверка наличия изображения товара
            img_element = product.find_element(By.XPATH, ".//img")  # Поиск элемента изображения
            title = img_element.get_attribute("title").replace("'",
                                                               "''")  # Извлечение заголовка товара с заменой одиночных кавычек
            icon = img_element.get_attribute("src")
        else:
            title = 'No title'  # Заголовок по умолчанию, если изображение отсутствует
            icon = 'No icon'  # Ссылка на иконку по умолчанию, если изображение отсутствует
        return title, icon
    except:
        return None, None  # В случае ошибки возвращаем None для заголовка и иконки товара


def process_city_data(city, url, driver, db):
    """
    Обрабатывает данные для определенного города.

    Аргументы:
    - city (str): Название города.
    - url (str): URL-адрес страницы города.
    - driver (WebDriver): Объект веб-драйвера.
    - db (Database): Объект базы данных.

    """
    # Добавление города в базу данных
    city_id = db.insert_city(city)

    # Извлечение секций данных со страницы города
    sections = find_data(driver, url)

    # Обход секций и извлечение информации о товарах
    for section in sections:
        products = section.find_elements(By.XPATH, ".//article")
        for product in products:
            # Извлечение информации о товаре
            title, icon = extract_product_info(product)
            if title is None:
                continue

            # Проверка наличия товара в базе данных
            product_id = db.get_product_id(title)
            if product_id is None:
                # Добавление нового товара в базу данных
                product_id = db.insert_product(title, icon)

            # Извлечение цены товара
            price_element = product.find_element(By.XPATH, ".//div[contains(@class, 'product-control-price')]")
            price_text = price_element.text.strip().replace('\u202f', '').replace('₽',
                                                                                  '')  # Удаление неразрывных пробелов и символа "₽"

            if price_text:
                # Проверка наличия непустого значения цены
                price_value = re.sub(r'\D', '', price_text)  # Удаление всех символов, кроме цифр
                if price_value:
                    db.insert_price(price_value, product_id, city_id)  # Вставка цены в базу данных

    # Коммит изменений в базу данных
    db.commit()


if __name__ == '__main__':
    # Создание объекта базы данных
    db = Database('localhost', 'Database', 'User1', '2051')
    # Запуск браузера без графического интерфейса
    options = webdriver.ChromeOptions()
    options.add_argument('window-size=1200x600')
    driver = webdriver.Chrome(options=options)

    # Загрузка ссылок на города из JSON файла
    cities = load_cities_from_json(‘cities.json')

    # Цикл по городам
    for city, url in cities.items():
        try:
            process_city_data(city, url, driver, db)
        except:
            continue

    # Закрытие соединения с базой данных
    db.close()

    # Закрытие браузера
    driver.quit()
