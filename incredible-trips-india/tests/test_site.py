"""End-to-end smoke tests with a temporary isolated database."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TEMP=tempfile.TemporaryDirectory()
os.environ['DATA_DIR']=TEMP.name
from fastapi.testclient import TestClient
import app as site

class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(site.app)

    def token(self,path):
        response=self.client.get(path)
        self.assertEqual(response.status_code,200)
        return self.client.cookies.get('iti_csrf')

    def test_public_pages_and_filter(self):
        for path in ['/','/tours','/about','/contact','/tours/royal-rajasthan-discovery','/login','/register','/health']:
            self.assertEqual(self.client.get(path).status_code,200,path)
        self.assertIn('Royal Rajasthan',self.client.get('/tours?state=Rajasthan').text)
        self.assertNotIn('Kashmir Valley Escape',self.client.get('/tours?state=Rajasthan').text)

    def test_enquiry_submission(self):
        csrf=self.token('/contact')
        r=self.client.post('/contact',data={'csrf':csrf,'name':'Test Visitor','email':'visitor@example.com','phone':'9999999999','destination':'Kashmir','message':'Please call me'},follow_redirects=False)
        self.assertEqual(r.status_code,303)
        with site.db() as c:self.assertIsNotNone(c.execute("SELECT id FROM enquiries WHERE email='visitor@example.com'").fetchone())

    def test_csrf_and_admin_access(self):
        self.assertEqual(self.client.post('/contact',data={'csrf':'wrong','name':'x','email':'x@x.com','phone':'9999999999'}).status_code,403)
        self.assertEqual(self.client.get('/admin/tours',follow_redirects=False).status_code,303)

    def test_register_book_and_admin_edit(self):
        csrf=self.token('/register')
        r=self.client.post('/register',data={'csrf':csrf,'name':'Demo Customer','phone':'8888888888','email':'demo-customer@example.com','password':'strongpassword123','next':'/account'},follow_redirects=False)
        self.assertEqual(r.status_code,303)
        self.assertEqual(self.client.get('/account').status_code,200)
        self.assertEqual(self.client.get('/admin').status_code,403)
        csrf=self.token('/book/1')
        r=self.client.post('/book/1',data={'csrf':csrf,'travel_date':'2030-04-10','travelers':'2','note':'Window room'},follow_redirects=False)
        self.assertEqual(r.status_code,303)
        with site.db() as c:
            self.assertIsNotNone(c.execute("SELECT id FROM bookings WHERE note='Window room'").fetchone())
            c.execute('INSERT INTO users(name,email,phone,password,role,created_at) VALUES (?,?,?,?,?,?)',('Owner','owner@example.com','',site.hash_password('ownerpass123456'),'admin',site.now()))
        csrf=self.token('/login')
        r=self.client.post('/login',data={'csrf':csrf,'email':'owner@example.com','password':'ownerpass123456','next':'/admin'},follow_redirects=False)
        self.assertEqual(r.status_code,303)
        self.assertEqual(self.client.get('/admin').status_code,200)
        self.assertEqual(self.client.get('/admin/tours/new').status_code,200)
        csrf=self.token('/admin/tours/new')
        r=self.client.post('/admin/tours/save',data={'csrf':csrf,'title':'New Demo Tour','category_id':'1','destination':'Jaipur','state':'Rajasthan','duration':'3 Days','price':'12000','description':'A great short trip','highlights':'City Palace','itinerary':'Day 1: Arrive','featured':'on','active':'on'},follow_redirects=False)
        self.assertEqual(r.status_code,303)
        self.assertIn('New Demo Tour',self.client.get('/tours').text)
        csrf=self.token('/admin/settings')
        r=self.client.post('/admin/settings',data={'csrf':csrf,'hero_title':'New Homepage Headline'},follow_redirects=False)
        self.assertEqual(r.status_code,303)
        self.assertIn('New Homepage Headline',self.client.get('/').text)

if __name__=='__main__':unittest.main()
