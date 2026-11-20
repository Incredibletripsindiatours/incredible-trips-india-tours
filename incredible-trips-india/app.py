"""Incredible Trips India Tours — compact, self-hosted FastAPI application."""
import os
import re
import secrets
import sqlite3
import hashlib
import hmac
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from PIL import Image, UnidentifiedImageError

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'site.db'
UPLOADS = DATA / 'uploads'
UPLOADS.mkdir(exist_ok=True)
SECRET = os.environ.get('SECRET_KEY', '')
if not SECRET:
    secret_file = DATA / '.secret_key'
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48))
        try: secret_file.chmod(0o600)
        except OSError: pass
    SECRET = secret_file.read_text().strip()
signer = URLSafeTimedSerializer(SECRET, salt='incredible-trips-session')
app = FastAPI(title='Incredible Trips India Tours')
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
templates = Jinja2Templates(directory=str(BASE / 'templates'))

@contextmanager
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def now(): return datetime.now().strftime('%Y-%m-%d %H:%M')
def hash_password(password):
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 260000)
    return f'{salt.hex()}${key.hex()}'
def verify_password(password, encoded):
    try:
        salt, expected = encoded.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 260000)
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError): return False

def init_db():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL DEFAULT '', password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS tours (id INTEGER PRIMARY KEY, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL, category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL, destination TEXT NOT NULL, state TEXT NOT NULL, duration TEXT NOT NULL, price INTEGER NOT NULL DEFAULT 0, image TEXT NOT NULL DEFAULT '', description TEXT NOT NULL, highlights TEXT NOT NULL DEFAULT '', itinerary TEXT NOT NULL DEFAULT '', featured INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS enquiries (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL, destination TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'New', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), tour_id INTEGER NOT NULL REFERENCES tours(id), travel_date TEXT NOT NULL, travelers INTEGER NOT NULL, note TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Requested', created_at TEXT NOT NULL);
        ''')
        defaults = {
            'brand':'Incredible Trips India Tours','tagline':'Discover. Explore. Experience India.',
            'hero_title':'Discover the India you’ve always dreamed of.',
            'hero_subtitle':'From royal Rajasthan to the snow-kissed Himalayas — extraordinary journeys, thoughtfully planned.',
            'hero_image':'https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=1800&q=85',
            'about_title':'Every journey should feel incredible.',
            'about_text':'Incredible Trips India Tours brings together heritage, culture, mountains, wildlife and spiritual experiences. Tell us how you love to travel, and we’ll help craft a memorable Indian getaway.',
            'owner':'Umesh Tripathi','phone':'9999853218','phone_alt':'9999753218',
            'email':'incredibletripsindiatours1@gmail.com','address':'India',
            'footer_text':'Handpicked journeys across India. Travel with wonder.',
        }
        for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO settings VALUES (?,?)',(k,v))
        categories = [('Heritage & Royal','Palaces, forts and living history'),('Spiritual','Sacred cities and timeless traditions'),('Hills & Adventure','Mountain escapes and outdoor thrills'),('Nature & Wildlife','National parks and scenic retreats'),('Family & Leisure','Easy, memorable holidays for everyone')]
        for n,d in categories: c.execute('INSERT OR IGNORE INTO categories(name,description) VALUES (?,?)',(n,d))
        if not c.execute('SELECT id FROM tours LIMIT 1').fetchone():
            examples = [
                ('Royal Rajasthan Discovery','royal-rajasthan-discovery',1,'Jaipur • Jodhpur • Udaipur • Jaisalmer','Rajasthan','7 Days / 6 Nights',24999,'https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=900&q=85','Discover regal forts, vibrant bazaars, golden dunes and the romance of Rajasthan.','Amber Fort\nCity Palace\nDesert sunset\nHeritage stays','Day 1: Arrival in Jaipur\nDay 2: Jaipur sightseeing\nDay 3: Drive to Jodhpur\nDay 4: Jodhpur exploration\nDay 5: Jaisalmer desert experience\nDay 6: Udaipur leisure\nDay 7: Departure',1),
                ('Sacred Uttar Pradesh','sacred-uttar-pradesh',2,'Varanasi • Ayodhya • Prayagraj','Uttar Pradesh','5 Days / 4 Nights',14999,'https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=900&q=85','Experience sacred ghats, ancient temples and the spiritual heart of North India.','Ganga Aarti\nTemple visits\nHeritage walks','Day 1: Varanasi arrival\nDay 2: Ghats and temples\nDay 3: Prayagraj\nDay 4: Ayodhya\nDay 5: Departure',1),
                ('Himalayan Hideaway','himalayan-hideaway',3,'Shimla • Manali • Solang Valley','Himachal Pradesh','6 Days / 5 Nights',19999,'https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=900&q=85','Breathe in crisp mountain air and unwind among pine forests and Himalayan views.','Mountain views\nSolang Valley\nScenic drives','Day 1: Shimla arrival\nDay 2: Shimla local tour\nDay 3: Transfer to Manali\nDay 4: Solang Valley\nDay 5: Manali leisure\nDay 6: Departure',1),
                ('Kashmir Valley Escape','kashmir-valley-escape',5,'Srinagar • Gulmarg • Pahalgam','Jammu & Kashmir','5 Days / 4 Nights',22999,'https://images.unsplash.com/photo-1595815771614-ade9d652a65d?auto=format&fit=crop&w=900&q=85','Lakes, alpine meadows and unforgettable mountain panoramas in the valley.','Dal Lake\nGulmarg excursion\nPahalgam scenery','Day 1: Srinagar arrival\nDay 2: Gulmarg\nDay 3: Pahalgam\nDay 4: Srinagar sightseeing\nDay 5: Departure',1),
                ('Uttarakhand Mountain & River','uttarakhand-mountain-river',3,'Rishikesh • Mussoorie • Haridwar','Uttarakhand','5 Days / 4 Nights',16999,'https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=900&q=85','A refreshing mix of mountain views, riverside moments and spiritual landmarks.','Rishikesh riverfront\nMussoorie viewpoints\nHaridwar Ganga Aarti','Day 1: Haridwar\nDay 2: Rishikesh\nDay 3: Mussoorie\nDay 4: Mussoorie leisure\nDay 5: Departure',0),
                ('Madhya Pradesh Wild & Wonderful','madhya-pradesh-wild-wonderful',4,'Khajuraho • Orchha • Bandhavgarh','Madhya Pradesh','6 Days / 5 Nights',25999,'https://images.unsplash.com/photo-1561731216-c3a4d99437d5?auto=format&fit=crop&w=900&q=85','Explore UNESCO heritage, medieval towns and the wild heart of central India.','Khajuraho temples\nOrchha heritage\nWildlife experiences','Day 1: Arrival\nDay 2: Khajuraho\nDay 3: Orchha\nDay 4: Bandhavgarh\nDay 5: Nature activities\nDay 6: Departure',0),
                ('Punjab Heritage Trail','punjab-heritage-trail',1,'Amritsar • Anandpur Sahib','Punjab','4 Days / 3 Nights',12999,'https://images.unsplash.com/photo-1606293926075-69a00dbfde81?auto=format&fit=crop&w=900&q=85','Rich traditions, memorable cuisine and historic sites in vibrant Punjab.','Golden Temple\nLocal cuisine\nHeritage experiences','Day 1: Amritsar arrival\nDay 2: Amritsar sightseeing\nDay 3: Anandpur Sahib\nDay 4: Departure',0),
            ]
            c.executemany('INSERT INTO tours(title,slug,category_id,destination,state,duration,price,image,description,highlights,itinerary,featured,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',[( *t, now()) for t in examples])

init_db()

def settings(c): return {r['key']:r['value'] for r in c.execute('SELECT * FROM settings')}
def current_user(request,c):
    token = request.cookies.get('iti_session')
    if not token: return None
    try: data = signer.loads(token,max_age=60*60*24*14)
    except (BadSignature,SignatureExpired): return None
    return c.execute('SELECT id,name,email,phone,role FROM users WHERE id=?',(data.get('id'),)).fetchone()
def csrf_token(request):
    if not hasattr(request.state,'csrf'):
        request.state.csrf = secrets.token_urlsafe(24)
    return request.state.csrf

def page(request, name, **kwargs):
    with db() as c:
        context={'request':request,'site':settings(c),'user':current_user(request,c),'categories':c.execute('SELECT * FROM categories ORDER BY name').fetchall(),'csrf':csrf_token(request)}
    context.update(kwargs)
    response=templates.TemplateResponse(request,name,context)
    if request.cookies.get('iti_csrf') != context['csrf']:
        response.set_cookie('iti_csrf',context['csrf'],httponly=True,samesite='lax',secure=os.environ.get('COOKIE_SECURE')=='1')
    return response

def validate_csrf(request,token):
    if not token or not hmac.compare_digest(request.cookies.get('iti_csrf',''),token):
        raise HTTPException(403,'Invalid form token. Refresh the page and try again.')
def redirect(path): return RedirectResponse(path,status_code=303)
def require_user(request,c,admin=False):
    user=current_user(request,c)
    if not user: raise HTTPException(401,'Please log in first.')
    if admin and user['role']!='admin': raise HTTPException(403,'Admin access only.')
    return user

def slugify(text): return re.sub(r'[^a-z0-9]+','-',text.lower()).strip('-') or uuid.uuid4().hex[:8]
def safe_return(path): return path if path.startswith('/') and not path.startswith('//') and not path.startswith('/\\') else '/'

def flash_url(path,message): return path + ('&' if '?' in path else '?') + 'notice=' + quote(message)

@app.get('/',response_class=HTMLResponse)
def home(request:Request):
    with db() as c:
        tours=c.execute('SELECT tours.*, categories.name AS category FROM tours LEFT JOIN categories ON tours.category_id=categories.id WHERE active=1 ORDER BY featured DESC,id LIMIT 6').fetchall()
    return page(request,'home.html',tours=tours)

@app.get('/tours',response_class=HTMLResponse)
def tours(request:Request,q:str='',state:str='',category:str=''):
    with db() as c:
        sql='SELECT tours.*, categories.name AS category FROM tours LEFT JOIN categories ON tours.category_id=categories.id WHERE active=1'; params=[]
        if q: sql+=' AND (title LIKE ? OR destination LIKE ? OR state LIKE ?)'; params.extend(['%'+q+'%']*3)
        if state: sql+=' AND state=?'; params.append(state)
        if category: sql+=' AND categories.name=?'; params.append(category)
        sql+=' ORDER BY featured DESC,tours.id DESC'
        rows=c.execute(sql,params).fetchall()
        states=[r[0] for r in c.execute('SELECT DISTINCT state FROM tours WHERE active=1 ORDER BY state')]
    return page(request,'tours.html',tours=rows,states=states,q=q,state=state,selected_category=category)

@app.get('/tours/{slug}',response_class=HTMLResponse)
def tour_detail(request:Request,slug:str):
    with db() as c:
        tour=c.execute('SELECT tours.*,categories.name AS category FROM tours LEFT JOIN categories ON tours.category_id=categories.id WHERE slug=? AND active=1',(slug,)).fetchone()
    if not tour: raise HTTPException(404,'Tour not found')
    return page(request,'tour_detail.html',tour=tour)

@app.get('/about',response_class=HTMLResponse)
def about(request:Request): return page(request,'about.html')
@app.get('/contact',response_class=HTMLResponse)
def contact(request:Request): return page(request,'contact.html')
@app.post('/contact')
def contact_submit(request:Request,csrf:str=Form(...),name:str=Form(...),email:str=Form(...),phone:str=Form(...),destination:str=Form(''),message:str=Form('')):
    validate_csrf(request,csrf)
    if not name.strip() or '@' not in email or len(phone.strip())<8: return redirect(flash_url('/contact','Please enter valid contact details.'))
    with db() as c: c.execute('INSERT INTO enquiries(name,email,phone,destination,message,created_at) VALUES (?,?,?,?,?,?)',(name.strip()[:120],email.strip()[:160],phone.strip()[:30],destination.strip()[:120],message.strip()[:3000],now()))
    return redirect(flash_url('/contact','Thanks! Your enquiry has been received. We will contact you soon.'))

@app.get('/login',response_class=HTMLResponse)
def login_page(request:Request,next:str='/account'): return page(request,'auth.html',mode='login',next=safe_return(next))
@app.get('/register',response_class=HTMLResponse)
def register_page(request:Request,next:str='/account'): return page(request,'auth.html',mode='register',next=safe_return(next))
@app.post('/register')
def register(request:Request,csrf:str=Form(...),name:str=Form(...),email:str=Form(...),phone:str=Form(...),password:str=Form(...),next:str=Form('/account')):
    validate_csrf(request,csrf)
    if len(password)<10 or not name.strip() or '@' not in email or len(phone.strip())<8: return redirect(flash_url('/register?next='+quote(safe_return(next)),'Enter valid details and a password of at least 10 characters.'))
    try:
        with db() as c:
            cursor=c.execute('INSERT INTO users(name,email,phone,password,role,created_at) VALUES (?,?,?,?,?,?)',(name.strip()[:120],email.strip().lower()[:160],phone.strip()[:30],hash_password(password),'customer',now()))
            user_id=cursor.lastrowid
    except sqlite3.IntegrityError: return redirect(flash_url('/register','An account with this email already exists.'))
    response=redirect(safe_return(next));response.set_cookie('iti_session',signer.dumps({'id':user_id}),httponly=True,samesite='lax',secure=os.environ.get('COOKIE_SECURE')=='1',max_age=1209600);return response
@app.post('/login')
def login(request:Request,csrf:str=Form(...),email:str=Form(...),password:str=Form(...),next:str=Form('/account')):
    validate_csrf(request,csrf)
    with db() as c: user=c.execute('SELECT * FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
    if not user or not verify_password(password,user['password']): return redirect(flash_url('/login?next='+quote(safe_return(next)),'Incorrect email or password.'))
    destination='/admin' if user['role']=='admin' and next=='/account' else safe_return(next)
    response=redirect(destination);response.set_cookie('iti_session',signer.dumps({'id':user['id']}),httponly=True,samesite='lax',secure=os.environ.get('COOKIE_SECURE')=='1',max_age=1209600);return response
@app.post('/logout')
def logout(request:Request,csrf:str=Form(...)):
    validate_csrf(request,csrf);response=redirect('/');response.delete_cookie('iti_session');return response

@app.get('/account',response_class=HTMLResponse)
def account(request:Request):
    with db() as c:
        user=current_user(request,c)
        if not user: return redirect('/login?next=/account')
        bookings=c.execute('SELECT bookings.*,tours.title,tours.slug FROM bookings JOIN tours ON tours.id=bookings.tour_id WHERE user_id=? ORDER BY bookings.id DESC',(user['id'],)).fetchall()
    return page(request,'account.html',bookings=bookings)
@app.get('/book/{tour_id}',response_class=HTMLResponse)
def booking_page(request:Request,tour_id:int):
    with db() as c:
        tour=c.execute('SELECT * FROM tours WHERE id=? AND active=1',(tour_id,)).fetchone()
        if not tour: raise HTTPException(404)
        if not current_user(request,c): return redirect('/login?next='+quote('/book/'+str(tour_id)))
    return page(request,'book.html',tour=tour)
@app.post('/book/{tour_id}')
def book(request:Request,tour_id:int,csrf:str=Form(...),travel_date:str=Form(...),travelers:int=Form(...),note:str=Form('')):
    validate_csrf(request,csrf)
    with db() as c:
        user=require_user(request,c)
        if not c.execute('SELECT 1 FROM tours WHERE id=? AND active=1',(tour_id,)).fetchone(): raise HTTPException(404)
        try: valid_date=datetime.strptime(travel_date,'%Y-%m-%d').date()>=datetime.now().date()
        except ValueError: valid_date=False
        if not valid_date or not 1<=travelers<=30: raise HTTPException(400,'Choose a future date and 1–30 travellers.')
        c.execute('INSERT INTO bookings(user_id,tour_id,travel_date,travelers,note,created_at) VALUES (?,?,?,?,?,?)',(user['id'],tour_id,travel_date,travelers,note[:2000],now()))
    return redirect(flash_url('/account','Your booking request has been submitted. Our team will contact you to confirm availability and pricing.'))

@app.get('/media/{filename}')
def media(filename:str):
    if not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp)',filename): raise HTTPException(404)
    path=UPLOADS/filename
    if not path.is_file(): raise HTTPException(404)
    return FileResponse(path,headers={'Cache-Control':'public, max-age=604800','X-Content-Type-Options':'nosniff'})

async def image_value(file:UploadFile|None,existing:str=''):
    if not file or not file.filename: return existing
    if file.content_type not in ('image/jpeg','image/png','image/webp'): raise HTTPException(400,'Upload a JPG, PNG or WebP image.')
    content=await file.read(5*1024*1024+1)
    if len(content)>5*1024*1024: raise HTTPException(400,'Image must be under 5 MB.')
    import io
    try:
        im=Image.open(io.BytesIO(content));im.verify()
        im=Image.open(io.BytesIO(content)).convert('RGB');im.thumbnail((1800,1400))
    except (UnidentifiedImageError,OSError,ValueError): raise HTTPException(400,'Invalid image file.')
    name=uuid.uuid4().hex+'.jpg';im.save(UPLOADS/name,format='JPEG',quality=86,optimize=True)
    return '/media/'+name

def admin_guard(request):
    with db() as c:
        user=current_user(request,c)
        if not user: return redirect('/login?next=/admin')
        if user['role']!='admin': raise HTTPException(403)
    return None

@app.get('/admin',response_class=HTMLResponse)
def admin(request:Request):
    guard=admin_guard(request)
    if guard: return guard
    with db() as c:
        stats={key:c.execute(f'SELECT COUNT(*) FROM {key}').fetchone()[0] for key in ['tours','enquiries','bookings','users']}
        latest=c.execute('SELECT * FROM enquiries ORDER BY id DESC LIMIT 5').fetchall()
    return page(request,'admin_dashboard.html',stats=stats,latest=latest)
@app.get('/admin/tours',response_class=HTMLResponse)
def admin_tours(request:Request):
    guard=admin_guard(request)
    if guard:return guard
    with db() as c: rows=c.execute('SELECT tours.*,categories.name AS category FROM tours LEFT JOIN categories ON tours.category_id=categories.id ORDER BY tours.id DESC').fetchall()
    return page(request,'admin_tours.html',tours=rows)
@app.get('/admin/tours/new',response_class=HTMLResponse)
@app.get('/admin/tours/{tour_id}/edit',response_class=HTMLResponse)
def admin_tour_edit(request:Request,tour_id:int=0):
    guard=admin_guard(request)
    if guard:return guard
    with db() as c: tour=c.execute('SELECT * FROM tours WHERE id=?',(tour_id,)).fetchone() if tour_id else None
    if tour_id and not tour: raise HTTPException(404)
    return page(request,'admin_tour_form.html',tour=tour)
@app.post('/admin/tours/save')
async def admin_tour_save(request:Request,csrf:str=Form(...),tour_id:int=Form(0),title:str=Form(...),category_id:int=Form(...),destination:str=Form(...),state:str=Form(...),duration:str=Form(...),price:int=Form(0),description:str=Form(...),highlights:str=Form(''),itinerary:str=Form(''),image_url:str=Form(''),image:UploadFile|None=File(None),featured:str=Form(''),active:str=Form('')):
    validate_csrf(request,csrf)
    if guard:=admin_guard(request):return guard
    if not title.strip() or price<0: raise HTTPException(400)
    with db() as c:
        old=c.execute('SELECT * FROM tours WHERE id=?',(tour_id,)).fetchone() if tour_id else None
        if tour_id and not old:raise HTTPException(404)
        if not c.execute('SELECT 1 FROM categories WHERE id=?',(category_id,)).fetchone(): raise HTTPException(400,'Invalid category')
        img=await image_value(image,image_url.strip() or (old['image'] if old else ''))
        slug=(old['slug'] if old else slugify(title)+'-'+uuid.uuid4().hex[:5])
        vals=(title.strip()[:180],slug,category_id,destination.strip()[:200],state.strip()[:100],duration.strip()[:80],price,img,description.strip()[:5000],highlights.strip()[:5000],itinerary.strip()[:10000],int(featured=='on'),int(active=='on'))
        if old: c.execute('UPDATE tours SET title=?,slug=?,category_id=?,destination=?,state=?,duration=?,price=?,image=?,description=?,highlights=?,itinerary=?,featured=?,active=? WHERE id=?',vals+(tour_id,))
        else: c.execute('INSERT INTO tours(title,slug,category_id,destination,state,duration,price,image,description,highlights,itinerary,featured,active,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',vals+(now(),))
    return redirect(flash_url('/admin/tours','Tour saved successfully.'))
@app.post('/admin/tours/{tour_id}/delete')
def admin_tour_delete(request:Request,tour_id:int,csrf:str=Form(...)):
    validate_csrf(request,csrf)
    if guard:=admin_guard(request):return guard
    with db() as c:
        if c.execute('SELECT 1 FROM bookings WHERE tour_id=?',(tour_id,)).fetchone(): c.execute('UPDATE tours SET active=0 WHERE id=?',(tour_id,));message='Tour archived because bookings exist.'
        else: c.execute('DELETE FROM tours WHERE id=?',(tour_id,));message='Tour deleted.'
    return redirect(flash_url('/admin/tours',message))

@app.get('/admin/categories',response_class=HTMLResponse)
def admin_categories(request:Request):
    if guard:=admin_guard(request):return guard
    return page(request,'admin_categories.html')
@app.post('/admin/categories')
def admin_category_save(request:Request,csrf:str=Form(...),name:str=Form(...),description:str=Form('')):
    validate_csrf(request,csrf)
    if guard:=admin_guard(request):return guard
    if not name.strip():raise HTTPException(400)
    try:
        with db() as c:c.execute('INSERT INTO categories(name,description) VALUES (?,?)',(name.strip()[:100],description.strip()[:300]))
    except sqlite3.IntegrityError:return redirect(flash_url('/admin/categories','Category already exists.'))
    return redirect(flash_url('/admin/categories','Category added.'))
@app.post('/admin/categories/{category_id}/delete')
def admin_category_delete(request:Request,category_id:int,csrf:str=Form(...)):
    validate_csrf(request,csrf)
    if guard:=admin_guard(request):return guard
    with db() as c:c.execute('DELETE FROM categories WHERE id=?',(category_id,))
    return redirect('/admin/categories')

@app.get('/admin/settings',response_class=HTMLResponse)
def admin_settings(request:Request):
    if guard:=admin_guard(request):return guard
    return page(request,'admin_settings.html')
@app.post('/admin/settings')
async def admin_settings_save(request:Request,csrf:str=Form(...),hero_upload:UploadFile|None=File(None)):
    validate_csrf(request,csrf)
    if guard:=admin_guard(request):return guard
    form=await request.form()
    allowed={'brand','tagline','hero_title','hero_subtitle','hero_image','about_title','about_text','owner','phone','phone_alt','email','address','footer_text'}
    with db() as c:
        for key in allowed:
            if key in form: c.execute('UPDATE settings SET value=? WHERE key=?',(str(form[key])[:5000],key))
        if hero_upload and hero_upload.filename:
            old=c.execute("SELECT value FROM settings WHERE key='hero_image'").fetchone()[0]
            img=await image_value(hero_upload,old)
            c.execute("UPDATE settings SET value=? WHERE key='hero_image'",(img,))
    return redirect(flash_url('/admin/settings','Website settings updated.'))

@app.get('/admin/enquiries',response_class=HTMLResponse)
def admin_enquiries(request:Request):
    if guard:=admin_guard(request):return guard
    with db() as c:rows=c.execute('SELECT * FROM enquiries ORDER BY id DESC').fetchall()
    return page(request,'admin_enquiries.html',enquiries=rows)
@app.post('/admin/enquiries/{enquiry_id}/status')
def enquiry_status(request:Request,enquiry_id:int,csrf:str=Form(...),status:str=Form(...)):
    validate_csrf(request,csrf)
    if guard:=admin_guard(request):return guard
    if status not in ('New','Contacted','Closed'):raise HTTPException(400)
    with db() as c:c.execute('UPDATE enquiries SET status=? WHERE id=?',(status,enquiry_id))
    return redirect('/admin/enquiries')
@app.get('/admin/bookings',response_class=HTMLResponse)
def admin_bookings(request:Request):
    if guard:=admin_guard(request):return guard
    with db() as c:rows=c.execute('SELECT bookings.*,users.name,users.email,users.phone,tours.title FROM bookings JOIN users ON users.id=bookings.user_id JOIN tours ON tours.id=bookings.tour_id ORDER BY bookings.id DESC').fetchall()
    return page(request,'admin_bookings.html',bookings=rows)
@app.post('/admin/bookings/{booking_id}/status')
def booking_status(request:Request,booking_id:int,csrf:str=Form(...),status:str=Form(...)):
    validate_csrf(request,csrf)
    if guard:=admin_guard(request):return guard
    if status not in ('Requested','Contacted','Confirmed','Cancelled'):raise HTTPException(400)
    with db() as c:c.execute('UPDATE bookings SET status=? WHERE id=?',(status,booking_id))
    return redirect('/admin/bookings')

@app.get('/health')
def health():return {'status':'ok'}
