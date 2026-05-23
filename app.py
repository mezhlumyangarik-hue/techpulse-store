import os, stripe
import cloudinary
import cloudinary.uploader  # Ավելացրինք Cloudinary գրադարանը նկարների համար
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
stripe.api_key = "sk_test_51TRz8s6nZy1YHtdO67ycmmgWxRcBZPy688ULXkB0LaaLJolxPFnlTX9PXe1ynBwKusNS47sd7F2SZclSgPdBBkFJ006QE4b3vh" 
app.config['SECRET_KEY'] = 'techpulse_v3_fixed'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app) 

# Կարգավորում ենք Cloudinary-ն քո տվյալներով
cloudinary.config( 
  cloud_name = "dguh3cevv", 
  api_key = "475575884566416", 
  api_secret = "maxXk_8VH9_axbaY0tIQCd8KSOQ",
  secure = True
)

# Ավտոմատ ստեղծել նկարների թղթապանակը (լոկալ ստուգումների համար)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 1. Սկզբից սահմանում ենք Աղյուսակը (Model)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    category = db.Column(db.String(50))
    img_main = db.Column(db.String(255))
    img_gallery = db.Column(db.Text)
    description = db.Column(db.Text)

# 2. Միայն Մոդելից հետո հրամայում ենք Flask-ին ստեղծել այն բազայում
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
            # Գլխավոր նկարը ուղարկում ենք Cloudinary
            upload_result = cloudinary.uploader.upload(file)
            main_image_url = upload_result['secure_url']
            
            # Պատկերասրահի (Gallery) նկարները ուղարկում ենք Cloudinary
            gal_urls = []
            for g in gallery_files:
                if g.filename:
                    g_upload_result = cloudinary.uploader.upload(g)
                    gal_urls.append(g_upload_result['secure_url'])
            
            new_p = Product(
                name=request.form.get('name'),
                price=float(request.form.get('price')),
                category=request.form.get('category'),
                img_main=main_image_url,                     # Պահում ենք Cloudinary-ի հղումը
                img_gallery=",".join(gal_urls),              # Ստորակետով բաժանված հղումներ
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
    g = p.img_gallery.split(',') if (p.img_gallery and p.img_gallery.strip()) else []
    return render_template('product_detail.html', product=p, gallery=g)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session: session['cart'] = []
    c = list(session['cart'])
    c.append({'name':request.
