import psycopg2
import re
from datetime import date, timedelta, datetime
import requests
import base64


class Database:
    def __init__(self, host, database, user, password):
        self.conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        self.cursor = self.conn.cursor()

    # Метод добавления города
    def insert_city(self, name):
        self.cursor.execute(
            "INSERT INTO cities(name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = %s RETURNING id",
            (name, name))
        city_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return city_id

    # Метод добавления названия и ссылки на иконку
    def insert_product(self, name, icon_url):
        response = requests.get(icon_url)
        image_content = response.content
        icon = psycopg2.Binary(image_content)
        self.cursor.execute("INSERT INTO products(name, icon) VALUES (%s, %s) RETURNING id", (name, icon))
        product_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return product_id

    # Метод добавления  иконки
    def insert_image(self, image_data):
        self.cursor.execute("INSERT INTO images(data) VALUES (%s) RETURNING id", (image_data,))
        image_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return image_id

    # Метод добавления цены
    def insert_price(self, price, product_id, city_id, date_value=None):
        if date_value is None:
            date_value = date.today()

        price = re.sub(r'\D', '', price)  # Удаляем все символы, кроме цифр

        if len(price) <= 7:
            formatted_price = price[:3]
        else:
            formatted_price = price[:4]

        # Проверяем последнюю цену для данного товара и города
        self.cursor.execute(
            "SELECT price FROM prices WHERE product_id = %s AND city_id = %s ORDER BY date DESC LIMIT 1",
            (product_id, city_id))
        last_price = self.cursor.fetchone()

        # Если текущая цена не совпадает с последней записанной ценой, добавляем новую запись
        if not last_price or formatted_price != last_price[0]:
            # Удаляем последнюю цену, если она совпадает с текущей
            if last_price and formatted_price == last_price[0]:
                self.cursor.execute(
                    "DELETE FROM prices WHERE product_id = %s AND city_id = %s AND price = %s",
                    (product_id, city_id, formatted_price))

            # Добавляем новую запись в таблицу prices
            self.cursor.execute(
                "INSERT INTO prices(price, product_id, city_id, date) VALUES (%s, %s, %s, %s) RETURNING id",
                (formatted_price, product_id, city_id, date_value))
            price_id = self.cursor.fetchone()[0]

            # Добавляем запись в таблицу price_history
            self.cursor.execute("INSERT INTO price_history(price_id, price, date) VALUES (%s, %s, %s)",
                                (price_id, formatted_price, date_value))

            self.conn.commit()

    # Метод получения продукта по его названию
    def get_product_id(self, name):
        self.cursor.execute("SELECT id FROM products WHERE name=%s", (name,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    # Метод получения списка всех городов
    def get_all_cities(self):
        self.cursor.execute("SELECT name FROM cities")
        cities = self.cursor.fetchall()
        return [city[0] for city in cities]

    # Метод получения ID города по его названию
    def get_city_id(self, city_name):
        self.cursor.execute("SELECT id FROM cities WHERE name=%s", (city_name,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    # Метод получения списка всех продуктов
    def get_all_products(self):
        self.cursor.execute("SELECT name FROM products")
        products = self.cursor.fetchall()
        return [product[0] for product in products]

    # Метод получения истории цен для продукта в городе
    def get_price_history_for_product(self, product_id, city_id):
        self.cursor.execute(
            "SELECT price_history.date, price_history.price FROM price_history INNER JOIN prices ON price_history.price_id = prices.id WHERE prices.product_id = %s AND prices.city_id = %s ORDER BY price_history.date ASC",
            (product_id, city_id))
        price_history = self.cursor.fetchall()
        return price_history

    # Метод получения цены на продукт в определенном городе
    def get_product_price_by_city(self, product_id, city_id):
        self.cursor.execute("SELECT price FROM prices WHERE product_id=%s AND city_id=%s", (product_id, city_id))
        price = self.cursor.fetchone()
        return price[0] if price else None

    # Метод преобразования бинарного кода в картинку
    def convert_bytes_to_image(self, icon_bytes):
        try:
            image = base64.b64encode(icon_bytes).decode('utf-8')
            return image
        except Exception as e:
            print("Error converting bytes to image:", str(e))
            return None

    # Метод получения списка всех цен на продукты в определенном городе
    def get_products_by_city(self, city_id, sort_order=None):
        self.cursor.execute(
            "SELECT products.id, products.name, prices.price, products.icon FROM prices JOIN products ON prices.product_id = products.id WHERE prices.city_id=%s",
            (city_id,))
        products = self.cursor.fetchall()
        formatted_products = []
        for product in products:
            product_id = product[0]
            name = product[1]
            price_str = str(product[2])  # Преобразование в строку
            icon_bytes = product[3]

            icon = self.convert_bytes_to_image(icon_bytes)

            if '₽' in price_str:
                parts = re.split(r'(\d+[\u202f\u00a0]₽)', price_str)
                price_parts = [part for part in parts if part and '₽' in part]
                if len(price_parts) == 1:
                    price = price_parts[0]
                    formatted_price = price
                elif len(price_parts) == 2:
                    discount_price = price_parts[0]
                    regular_price = price_parts[1]
                    if '₽' in regular_price:
                        formatted_price = discount_price.strip()
                    else:
                        formatted_price = '<span style="text-decoration: line-through;">{}</span> {}'.format(
                            regular_price.strip(), discount_price.strip())
                else:
                    formatted_price = price_str.strip()
            else:
                formatted_price = price_str.strip()

            formatted_products.append((product_id, name, formatted_price, icon, price_str, city_id))

        if sort_order == 'desc':
            formatted_products.sort(key=lambda x: x[2], reverse=True)
        elif sort_order == 'asc':
            formatted_products.sort(key=lambda x: x[2])

        return formatted_products

    def get_product_name(self, product_id):
        self.cursor.execute("SELECT name FROM products WHERE id=%s", (product_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def get_product_icon(self, product_id):
        self.cursor.execute("SELECT icon FROM products WHERE id=%s", (product_id,))
        row = self.cursor.fetchone()
        icon_bytes = row[0] if row else None
        if icon_bytes:
            product_icon = self.convert_bytes_to_image(icon_bytes)
            return product_icon
        else:
            return None

    def get_current_price(self, product_id):
        self.cursor.execute("SELECT price FROM prices WHERE product_id=%s ORDER BY date DESC LIMIT 1", (product_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def __del__(self):
        self.conn.close()

    def close(self):
        self.conn.close()
