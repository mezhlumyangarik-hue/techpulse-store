import os, stripe
from flask import Flask, render_template, request, redirect, session, url_for, flash # Ավելացրու flash-ը վերևում
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
stripe.api_key = "sk_test_51TRz8s6nZy1YHtdO67ycmmgWxRcBZPy688ULXkB0LaaLJolxPFnlTX9PXe1ynBwKusNS47sd7F2SZclSgPdBBkFJ006QE4b3vh" 
app.config['SECRET_KEY'] = 'techpulse_v3_fixed'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)


with app.app_context():
    db.create_all()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    category = db.Column(db.String(50))
    img_main = db.Column(db.String(255))
    img_gallery = db.Column(db.Text)
    description = db.Column(db.Text)

T = {
    'en': {'home':'Home','shop':'Shop','bag':'Bag','search':'Search...','more':'Learn more','add':'Add to Bag','clear':'Clear Bag'},
    'am': {'home':'Գլխավոր','shop':'Խանութ','bag':'Զամբյուղ','search':'Փնտրել...','more':'Իմանալ ավելին','add':'Ավելացնել','clear':'Մաքրել'},
    'ru': {'home':'Главная','shop':'Магазин','bag':'Корзина','search':'Поиск...','more':'Подробнее','add':'В корзину','clear':'Очистить'}
}

@app.context_processor
def inject_globals():
    l = session.get('lang', 'am')
    return dict(t=T.get(l, T['am']))


# --- ADMIN LOGICS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Սա այն գաղտնաբառն է, որով պետք է մտնես
        if request.form.get('password') == "admin123":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
    return render_template('login.html')

@app.route('/panel', methods=['GET', 'POST'])
def admin_panel():
    # Ստուգում ենք՝ արդյոք ադմինը մուտք է գործել
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # Ապրանք ավելացնելու կոդը
        file = request.files.get('img_main')
        gallery_files = request.files.getlist('img_gallery')
        
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Gallery նկարները պահում ենք ստորակետով բաժանված
            gal_names = [secure_filename(g.filename) for g in gallery_files if g.filename]
            for g in gallery_files:
                if g.filename:
                    g.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(g.filename)))
            
            new_p = Product(
                name=request.form.get('name'),
                price=float(request.form.get('price')),
                category=request.form.get('category'),
                img_main=filename,
                img_gallery=",".join(gal_names),
                description=request.form.get('description')
            )
            db.session.add(new_p)
            db.session.commit()
            return redirect(url_for('admin_panel'))
            
    products = Product.query.all()
    return render_template('admin.html', products=products)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    p = Product.query.order_by(Product.id.desc()).limit(3).all()
    return render_template('index.html', products=p)

@app.route('/shop')
def shop():
    cat = request.args.get('cat', '')
    q = request.args.get('q', '')
    prods = Product.query
    if q: prods = prods.filter(Product.name.contains(q))
    if cat: prods = prods.filter_by(category=cat)
    return render_template('shop.html', products=prods.all(), current_cat=cat)
@app.route('/product/<int:id>')
def product_detail(id):
    p = Product.query.get_or_404(id)
    # Այստեղ ստուգում ենք՝ արդյոք gallery-ն դատարկ չէ, նոր բաժանում ենք
    g = p.img_gallery.split(',') if (p.img_gallery and p.img_gallery.strip()) else []
    return render_template('product_detail.html', product=p, gallery=g)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session: session['cart'] = []
    c = list(session['cart'])
    c.append({'name':request.form.get('name'),'price':float(request.form.get('price')),'img':request.form.get('img')})
    session['cart'] = c
    session.modified = True
    
    # Ավելացնում ենք ծանուցումը
    flash("Added to bag!", "success") 
    
    return redirect(request.referrer or url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:idx>')
def remove_from_cart(idx):
    c = list(session.get('cart', []))
    if 0 <= idx < len(c): c.pop(idx)
    session['cart'] = c
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    c = session.get('cart', [])
    tot = sum(i['price'] for i in c)
    return render_template('cart.html', cart=c, total=tot)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    c = session.get('cart', [])
    items = [{'price_data':{'currency':'usd','product_data':{'name':i['name']},'unit_amount':int(i['price']*100)},'quantity':1} for i in c]
    s = stripe.checkout.Session.create(payment_method_types=['card'], line_items=items, mode='payment', success_url=url_for('payment_success',_external=True), cancel_url=url_for('cart',_external=True))
    return redirect(s.url, code=303)

@app.route('/payment_success')
def payment_success():
    session.pop('cart', None)
    return render_template('success.html')

@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

if __name__ == "__main__":
    with app.app_context(): db.create_all()
    app.run(debug=True, port=5001)
