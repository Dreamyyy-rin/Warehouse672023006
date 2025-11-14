"""Whitebox Testing - Authentication Blueprint"""
import pytest
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash, check_password_hash


class TestLoginLogic:
    @patch('blueprints.auth_bp.users_col')
    @patch('blueprints.auth_bp.SessionManager')
    def test_login_valid_credentials(self, mock_session, mock_users, client):
        """Test login dengan credentials valid."""
        mock_user = {
            "_id": "123",
            "username": "john",
            "password": generate_password_hash("pass123"),
            "role": "user"
        }
        mock_users.find_one.return_value = mock_user
        mock_session.generate_token.return_value = "valid_token_abc123"
        response = client.post('/login', data={'username': 'john', 'password': 'pass123'})
        assert response.status_code in [301, 302], f"Expected redirect, got {response.status_code}"
        assert 'Set-Cookie' in response.headers
        print("✓ Login dengan credentials valid berhasil")
    
    @patch('blueprints.auth_bp.users_col')
    def test_login_wrong_password(self, mock_users, client):
        """Test login dengan password yang salah"""
        mock_user = {
            "username": "john",
            "password": generate_password_hash("correctpass"),
            "role": "user"
        }
        mock_users.find_one.return_value = mock_user
        response = client.post('/login', data={'username': 'john', 'password': 'wrongpass'})
        assert response.status_code == 200, "Should return login page"
        print("✓ Login dengan password salah ditolak")
    
    @patch('blueprints.auth_bp.users_col')
    def test_login_user_not_found(self, mock_users, client):
        """Test login dengan user yang tidak terdaftar"""
        mock_users.find_one.return_value = None
        response = client.post('/login', data={'username': 'nonexistent', 'password': 'any'})
        assert response.status_code == 200
        print("✓ Login user tidak terdaftar ditolak")
    
    def test_login_empty_username(self, client):
        """Test login dengan username kosong (should return login page)"""
        response = client.post('/login', data={'username': '', 'password': 'pass'})
        assert response.status_code == 200
        print("✓ Login dengan username kosong ditolak")
    
    def test_login_empty_password(self, client):
        """Test login dengan password kosong"""
        response = client.post('/login', data={'username': 'user', 'password': ''})
        assert response.status_code == 200
        print("✓ Login dengan password kosong ditolak")


class TestSessionManagement:
    def test_token_generation(self, session_manager):
        """Test token generation with valid username and role"""
        token = session_manager.generate_token("john", "admin")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        print("✓ Token generation berhasil")
    
    def test_token_verification_valid(self, session_manager):
        """Test token verification with valid token"""
        token = session_manager.generate_token("john", "admin")
        payload = session_manager.verify_token(token)        
        assert payload is not None
        assert payload['username'] == 'john'
        assert payload['role'] == 'admin'
        print("✓ Token verification valid berhasil")
    
    def test_token_verification_invalid(self, session_manager):
        """Test token verification with invalid token"""
        payload = session_manager.verify_token("invalid_token_xyz123")
        assert payload is None
        print("✓ Token verification invalid ditolak")
    
    def test_token_verification_malformed(self, session_manager):
        """Test token verification with malformed token"""
        payload = session_manager.verify_token("not.a.jwt")
        assert payload is None
        print("✓ Token malformed ditolak")


class TestAuthenticationDecorators:
    @patch('blueprints.auth_bp.SessionManager')
    def test_login_required_without_token(self, mock_session, client):    
        """Test protected route tanpa token redirect ke login"""
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code in [301, 302]
        print("✓ Protected route tanpa token redirect ke login")
    
    @patch('blueprints.auth_bp.SessionManager')
    def test_login_required_with_invalid_token(self, mock_session, client):
        """Test protected route dengan invalid token redirect ke login"""
        mock_session.verify_token.return_value = None
        client.set_cookie('token', 'invalid_token')
        response = client.get('/dashboard', follow_redirects=False)
        assert response.status_code in [301, 302]
        print("✓ Protected route dengan invalid token redirect")
    
    def test_login_required_with_valid_token(self, client, test_user_token):
        """Test protected route dengan valid token berhasil diakses"""        
        client.set_cookie('token', test_user_token)
        response = client.get('/dashboard')
        assert response.status_code != 401
        assert response.status_code != 403
        print("✓ Protected route dengan valid token berhasil")


class TestPasswordSecurity:
    def test_password_hashing_basic(self):
        """Test basic password hashing"""
        password = "mypassword123"
        hashed = generate_password_hash(password)
        is_valid = check_password_hash(hashed, password)
        assert hashed != password, "Hash tidak boleh sama dengan plaintext"
        assert is_valid, "Hash harus bisa diverify"
        print("✓ Password hashing basic berhasil")
    
    def test_password_hash_unique(self):
        """Test bahwa setiap hash berbeda meskipun password sama"""
        password = "same_password"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        assert hash1 != hash2, "Hash harus unik setiap kali"
        assert check_password_hash(hash1, password)
        assert check_password_hash(hash2, password)
        print("✓ Password hash unique untuk setiap generation")
    
    def test_wrong_password_rejected(self):
        """Test wrong password ditolak"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = generate_password_hash(password)
        is_valid = check_password_hash(hashed, wrong_password)
        assert not is_valid, "Wrong password harus ditolak"
        print("✓ Wrong password ditolak dengan benar")


class TestInputSanitization:
    @patch('blueprints.auth_bp.users_col')
    def test_sql_injection_attempt(self, mock_users, client):
        """Test SQL injection attempt di login"""
        mock_users.find_one.return_value = None
        response = client.post('/login', data={
            'username': "' OR '1'='1",
            'password': "anything"
        })
        assert response.status_code == 200
        print("✓ SQL injection attempt ditangani dengan aman")
    
    @patch('blueprints.auth_bp.users_col')
    def test_xss_attempt_in_username(self, mock_users, client):
        """Test XSS attempt di username field"""
        mock_users.find_one.return_value = None
        response = client.post('/login', data={
            'username': "<script>alert('xss')</script>",
            'password': "test"
        })
        assert response.status_code == 200
        print("✓ XSS attempt di username ditangani")
    
    def test_username_sanitization(self):
        """Test username sanitization function"""
        from common.utils import sanitize_text
        malicious = "<img src=x onerror='alert(1)'>"
        cleaned = sanitize_text(malicious)
        assert '<' not in cleaned
        assert '>' not in cleaned
        assert cleaned == "img src=x onerror='alert(1)'"
        print("✓ Username sanitization berhasil")


class TestLogoutFunctionality:
    @patch('blueprints.auth_bp.SessionManager')
    def test_logout_removes_cookie(self, mock_session, client, test_user_token):
        """Test logout menghapus token cookie"""
        client.set_cookie('token', test_user_token)
        response = client.post('/logout', follow_redirects=False)
        assert response.status_code in [301, 302]
        print("✓ Logout berhasil dan redirect")
    
    @patch('blueprints.auth_bp.SessionManager')
    def test_logout_without_token(self, mock_session, client):
        """Test logout tanpa token tetap berhasil"""
        response = client.post('/logout', follow_redirects=False)
        
        assert response.status_code in [301, 302, 200]
        print("✓ Logout tanpa token tetap berhasil")


class TestRoleBasedAccess:
    def test_admin_role_extraction(self, session_manager):
        """Test admin role correctly stored di token"""
        token = session_manager.generate_token("admin_user", "admin")
        payload = session_manager.verify_token(token)
        assert payload['role'] == 'admin'
        print("✓ Admin role extraction berhasil")
    
    def test_user_role_extraction(self, session_manager):
        """Test user role correctly stored di token"""
        token = session_manager.generate_token("normal_user", "user")
        payload = session_manager.verify_token(token)
        assert payload['role'] == 'user'
        print("✓ User role extraction berhasil")
    
    def test_different_roles_different_tokens(self, session_manager):
        """Test different roles produce different tokens"""
        admin_token = session_manager.generate_token("admin", "admin")
        user_token = session_manager.generate_token("user", "user")
        
        admin_payload = session_manager.verify_token(admin_token)
        user_payload = session_manager.verify_token(user_token)
        assert admin_token != user_token
        assert admin_payload['role'] == 'admin'
        assert user_payload['role'] == 'user'
        print("✓ Different roles produce different tokens")

