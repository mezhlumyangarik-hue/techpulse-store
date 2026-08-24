import os, stripe
import cloudinary
import cloudinary.uploader
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='static')

stripe.api_key = os.environ.get("STRIPE_API_KEY", "sk_test_51TRz8s6nZy1YHtdO67ycmmgWxRcBZPy688ULXkB0LaaLJolxPFnlTX9PXe1ynBwKusNS47sd7F2SZclSgPdBBkFJ006QE4b3vh") 
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "techpulse_v3_fixed")

if os.environ.get('VERCEL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app) 

cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "dguh3cevv"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY", "475575884566416"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET", "maxXk_8VH9_axbaY0tIQCd8KSOQ"),
  secure = True
)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    category = db.Column(db.String(50))
    img_main = db.Column(db.String(255))
    img_gallery = db.Column(db.Text)
    description = db.Column(db.Text)

# Մշտական (Fallback) ապրանքներ
STATIC_PRODUCTS = [
    Product(id=1, name="iPhone 15 Pro Max", price=1199.00, category="Phones", img_main="https://images.unsplash.com/photo-1695048133142-1a20484d2569?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1695048133142-1a20484d2569?q=80&w=800", description="Titanium design, A17 Pro chip, 48MP main camera with multiple focal lengths."),
    Product(id=2, name="Samsung Galaxy S24 Ultra", price=1299.00, category="Phones", img_main="https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?q=80&w=800", description="Galaxy AI features, built-in S Pen, 200MP camera, Snapdragon 8 Gen 3."),
    Product(id=3, name="Google Pixel 8 Pro", price=999.00, category="Phones", img_main="https://images.unsplash.com/photo-1598327105666-5b89351aff97?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1598327105666-5b89351aff97?q=80&w=800", description="Tensor G3 chip, fully upgraded cameras, best-in-class photo editing tools."),
    Product(id=4, name="MacBook Pro 16 M3 Max", price=2499.00, category="Laptops", img_main="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=800", description="Extreme performance with M3 Max chip, Liquid Retina XDR display, 22 hours battery."),
    Product(id=5, name="Dell XPS 15", price=1899.00, category="Laptops", img_main="https://images.unsplash.com/photo-1593642632823-8f785ba67e45?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1593642632823-8f785ba67e45?q=80&w=800", description="13th Gen Intel Core i9, NVIDIA RTX graphics, 3.5K OLED touch screen."),
    Product(id=6, name="ASUS ROG Zephyrus G16", price=1999.00, category="Laptops", img_main="https://images.unsplash.com/photo-1603302576837-37561b2e2302?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1603302576837-37561b2e2302?q=80&w=800", description="Ultimate gaming laptop with Intel Core Ultra 9, RTX 4080, and ROG Nebula display."),
    Product(id=7, name="AirPods Pro (2nd Gen)", price=249.00, category="Accessories", img_main="https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?q=80&w=800", description="Up to 2x more Active Noise Cancellation, Adaptive Audio, and USB-C charging."),
    Product(id=8, name="Apple Watch Ultra 2", price=799.00, category="Accessories", img_main="https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?q=80&w=800", description="Rugged titanium case, dual-frequency GPS, up to 36 hours of battery life."),
    Product(id=9, name="Sony WH-1000XM5", price=399.00, category="Accessories", img_main="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=800", img_gallery="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=800", description="Industry-leading noise canceling headphones with crystal clear hands-free calling.")
]

with app.app_context():
    db.create_all()

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
        if request.form.get('password') == "admin123":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
    return render_template('login.html')

@app.route('/panel', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        file = request.files.get('img_main')
        gallery_files = request.files.getlist('img_gallery')
        
        if file:
            upload_result = cloudinary.uploader.upload(file)
            main_image_url = upload_result['secure_url']
            
            gal_urls = []
            for g in gallery_files:
                if g.filename:
                    g_upload_result = cloudinary.uploader.upload(g)
                    gal_urls.append(g_upload_result['secure_url'])
            
            new_p = Product(
                name=request.form.get('name'),
                price=float(request.form.get('price')),
                category=request.form.get('category'),
                img_main=main_image_url,
                img_gallery=",".join(gal_urls),
                description=request.form.get('description')
            )
            db.session.add(new_p)
            db.session.commit()
            return redirect(url_for('admin_panel'))
            
    products = Product.query.all() or STATIC_PRODUCTS
    return render_template('admin.html', products=products)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
        
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
    flash('Ապրանքը հաջողությամբ ջնջվեց։')
    return redirect(url_for('admin_panel'))


# --- USER FRONTEND LOGICS ---

@app.route('/')
def index():
    p = []
    try:
        p = Product.query.order_by(Product.id.desc()).limit(3).all()
    except Exception:
        pass
    if not p:
        p = STATIC_PRODUCTS[:3]
    return render_template('index.html', products=p)

@app.route('/shop')
def shop():
    cat = request.args.get('cat', '')
    q = request.args.get('q', '')
    res = []
    try:
        prods = Product.query
        if q: prods = prods.filter(Product.name.contains(q))
        if cat: prods = prods.filter_by(category=cat)
        res = prods.all()
    except Exception:
        pass
    
    if not res:
        res = STATIC_PRODUCTS
        if cat:
            res = [x for x in res if x.category.lower() == cat.lower()]
        if q:
            res = [x for x in res if q.lower() in x.name.lower()]
            
    return render_template('shop.html', products=res, current_cat=cat)

@app.route('/product/<int:id>')
def product_detail(id):
    p = Product.query.get(id)
    if not p:
        p = next((x for x in STATIC_PRODUCTS if x.id == id), STATIC_PRODUCTS[0])
    g = p.img_gallery.split(',') if (p.img_gallery and p.img_gallery.strip()) else []
    return render_template('product_detail.html', product=p, gallery=g)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session: session['cart'] = []
    c = list(session['cart'])
    c.append({'name':request.form.get('name'),'price':float(request.form.get('price')),'img':request.form.get('img')})
    session['cart'] = c
    session.modified = True
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
    app.run(debug=True, port=5001)
