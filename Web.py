from flask import Flask, render_template, request, redirect
from Database import Database

app = Flask(__name__)
db = Database('localhost', 'Database', 'User1', '2051')
sites = ['dodo']  # список сайтов


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        site = request.form['site']
        # Далее можно обработать выбор пользователя и перенаправить на страницу с результатами
        if site == 'dodo':
            return redirect('/dodo/cities')
    else:
        return render_template('index.html', sites=sites)


@app.route('/dodo/cities')
def dodo_cities():
    cities = db.get_all_cities()
    return render_template('cities.html', cities=cities)


@app.route('/products/<string:city_name>')
def products(city_name):
    city_id = db.get_city_id(city_name)
    sort_order = request.args.get('sort_order')
    products = db.get_products_by_city(city_id)
    return render_template('products.html', city_name=city_name, selected_city_id=city_id, products=products)


@app.template_filter('format_price')
def format_price(value):
    if value:
        value = str(value)
        if len(value) >= 7:
            return value[:3] + '₽'
        else:
            return value[:4] + '₽'
    return ''


@app.route('/products')
def all_city_products():
    products = db.get_all_products()
    return render_template('products.html', products=products)


@app.route('/price_history/<int:product_id>/<int:city_id>')
def price_history(product_id, city_id):
    product_name = db.get_product_name(product_id)  # Получаем название товара из базы данных
    product_icon = db.get_product_icon(product_id)  # Получаем иконку товара из базы данных
    current_price = db.get_current_price(product_id)  # Получаем текущую цену товара из базы данных
    price_history = db.get_price_history_for_product(product_id, city_id) # Получаем данные истории цен из базы данных
    return render_template('price_history.html', price_history=price_history, product_name=product_name, product_icon=product_icon, current_price=current_price)



if __name__ == '__main__':
    app.run(debug=True)
