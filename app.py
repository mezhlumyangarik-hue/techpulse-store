import os, stripe
import cloudinary
import cloudinary.uploader
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='static')
app.wsgi_app = app  # Պարտադիր է Vercel-ի համար

stripe.api_key = "sk_test_51TRz8s6nZy1YHtdO67ycmmgWxRcBZPy688ULXkB0LaaLJolxPFnlTX9PXe1ynBwKusNS47sd7F2SZclSgPdBBkFJ006QE4b3vh" 
app.config['SECRET_KEY'] = 'techpulse_v3_fixed'

# ՃԻՇՏ ԿԱՐԳԱՎՈՐՈՒՄ VERCEL-Ի ՀԱՄԱՐ.
# Եթե կայքն աշխատում է Vercel-ում, բազան ստեղծում ենք /tmp պապկայում, որ սերվերը չկախվի
if os.environ.get('VERCEL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/database.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app) 

# Կարգավորում ենք Cloudinary-ն
cloudinary.config( 
  cloud_name = "dguh3cevv", 
  api_key = "475575884566416", 
  api_secret = "maxXk_8VH9_axbaY0tIQCd8KSOQ",
  secure = True
)

# Մոդել (Աղյուսակ)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    category = db.Column(db.String(50))
    img_main = db.Column(db.String(255))
    img_gallery = db.Column(db.Text)
    description = db.Column(db.Text)

# ԱՎՏՈՄԱՏ ՍՏԵՂԾՈՒՄ ԵՎ՛ ԼՈԿԱԼ, ԵՎ՛ VERCEL-Ի ՎՐԱ՝ ԱՌԱՆՑ ԿԱԽՎԵԼՈՒ
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
            
    try:
        products = Product.query.all()
    except:
        products = []
    return render_template('admin.html', products=products)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
        
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Ապրանքը հաջողությամբ ջնջվեց։')
    return redirect(url_for('admin_panel'))

# --- USER FRONTEND LOGICS ---

@app.route('/')
def index():
    try:
        p = Product.query.order_by(Product.id.desc()).limit(3).all()
    except:
        p = []
    return render_template('index.html', products=p)

@app.route('/shop')
def shop():
    cat = request.args.get('cat', '')
    q = request.args.get('q', '')
    try:
        prods = Product.query
        if q: prods = prods.filter(Product.name.contains(q))
        if cat: prods = prods.filter_by(category=cat)
        res = prods.all()
    except:
        res = []
    return render_template('shop.html', products=res, current_cat=cat)

@app.route('/product/<int:id>')
def product_detail(id):
    p = Product.query.get_or_404(id)
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
