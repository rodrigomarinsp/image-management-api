# test_user_management.py
import unittest
import json
from app import create_app, db
from models import User, Team

class UserManagementTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test admin user
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()
        
        # Login to get auth token
        response = self.client.post('/api/login', 
                                   data=json.dumps({'username': 'admin', 'password': 'password'}),
                                   content_type='application/json')
        self.token = json.loads(response.data)['token']
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_create_team(self):
        # Test team creation
        team_data = {'name': 'Engineering'}
        response = self.client.post('/api/teams', 
                                   headers={'Authorization': f'Bearer {self.token}'},
                                   data=json.dumps(team_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('Engineering', response.get_data(as_text=True))
        
    def test_create_user(self):
        # Create a team first
        team_data = {'name': 'Engineering'}
        self.client.post('/api/teams', 
                        headers={'Authorization': f'Bearer {self.token}'},
                        data=json.dumps(team_data),
                        content_type='application/json')
        
        # Create a user in that team
        user_data = {
            'username': 'testuser',
            'email': 'rodrigomarinsp@gmail.com',
            'password': '',
            'team_name': 'Engineering'
        }
        response = self.client.post('/api/users', 
                                   headers={'Authorization': f'Bearer {self.token}'},
                                   data=json.dumps(user_data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('testuser', response.get_data(as_text=True))
        
if __name__ == '__main__':
    unittest.main()
