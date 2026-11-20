"""Create or reset the single admin login. Run: python create_admin.py"""
import getpass
import sqlite3
from app import db,hash_password,now

email=input('Admin email: ').strip().lower()
if '@' not in email:raise SystemExit('Please enter a valid email.')
name=input('Admin display name [Umesh Tripathi]: ').strip() or 'Umesh Tripathi'
password=getpass.getpass('Admin password (at least 12 characters): ')
if len(password)<12:raise SystemExit('Password must be at least 12 characters.')
confirm=getpass.getpass('Confirm password: ')
if password!=confirm:raise SystemExit('Passwords do not match.')
with db() as c:
    row=c.execute('SELECT id,role FROM users WHERE email=?',(email,)).fetchone()
    if row and row['role']!='admin':raise SystemExit('Email belongs to a customer account. Use a different admin email.')
    if row:c.execute('UPDATE users SET password=?,name=? WHERE id=?',(hash_password(password),name,row['id']))
    else:c.execute('INSERT INTO users(name,email,phone,password,role,created_at) VALUES (?,?,?,?,?,?)',(name,email,'',hash_password(password),'admin',now()))
print('Admin account ready. Sign in at /login, then open /admin.')
