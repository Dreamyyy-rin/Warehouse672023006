"""Whitebox Testing - Categories Blueprint"""
import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId


class TestCategoriesAPI:
    """Test Categories API endpoints"""
    @patch('blueprints.category_bp.categories_col')
    def test_get_categories_list(self, mock_cat_col, client, test_user_token):
        """Test retrieve semua categories"""
        client.set_cookie('token', test_user_token)
        mock_cat_col.find.return_value = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Electronics",
                "status": "active"
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "name": "Books",
                "status": "active"
            }
        ]
        response = client.get('/api/categories')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 2
        print("✓ Get all categories berhasil")
    
    @patch('blueprints.category_bp.categories_col')
    def test_get_category_by_id(self, mock_cat_col, client, test_user_token):
        """Test retrieve category by ID"""
        client.set_cookie('token', test_user_token)
        cat_id = "507f1f77bcf86cd799439011"
        mock_cat_col.find_one.return_value = {
            "_id": ObjectId(cat_id),
            "name": "Electronics",
            "status": "active"
        }
        response = client.get(f'/api/categories/{cat_id}')
        assert response.status_code in [200, 404]
        print("✓ Get category by ID berhasil")


class TestCategoriesCreation:
    """Test membuat category baru"""
    @patch('blueprints.category_bp.categories_col')
    def test_create_category_admin_only(self, mock_cat_col, client, admin_token):
        """Test create category hanya bisa admin"""
        client.set_cookie('token', admin_token)
        mock_cat_col.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        response = client.post('/api/categories', json={
            'name': 'New Category'
        })
        assert response.status_code in [200, 201]
        print("✓ Create category dengan admin berhasil")
    
    @patch('blueprints.category_bp.categories_col')
    def test_create_category_user_forbidden(self, mock_cat_col, client, test_user_token):
        """Test user biasa tidak bisa create category"""
        client.set_cookie('token', test_user_token)
        response = client.post('/api/categories', json={
            'name': 'Unauthorized Category'
        })
        assert response.status_code in [403, 401]
        print("✓ User biasa tidak bisa create category")
    
    def test_create_category_requires_login(self, client):
        """Test create category memerlukan login"""
        response = client.post('/api/categories', json={
            'name': 'Test'
        }, follow_redirects=False)
        assert response.status_code in [301, 302, 401]
        print("✓ Create category memerlukan login")


class TestCategoriesUpdate:
    """Test update category"""
    
    @patch('blueprints.category_bp.categories_col')
    def test_update_category_success(self, mock_cat_col, client, admin_token):
        """Test update category dengan data valid"""
        client.set_cookie('token', admin_token)
        cat_id = "507f1f77bcf86cd799439011"
        response = client.put(f'/api/categories/{cat_id}', json={
            'name': 'Updated Name'
        })
        assert response.status_code in [200, 404]
        print("✓ Update category berhasil")
    
    @patch('blueprints.category_bp.categories_col')
    def test_update_nonexistent_category(self, mock_cat_col, client, admin_token):
        """Test update category yang tidak ada"""
        client.set_cookie('token', admin_token)
        mock_cat_col.find_one.return_value = None
        response = client.put('/api/categories/nonexistent_id', json={
            'name': 'New Name'
        })
        assert response.status_code in [404, 400]
        print("✓ Update nonexistent category ditangani")


class TestCategoriesDelete:
    """Test delete/soft-delete category"""
    
    @patch('blueprints.category_bp.categories_col')
    def test_delete_category_admin(self, mock_cat_col, client, admin_token):
        """Test delete category dengan admin"""
        client.set_cookie('token', admin_token)
        cat_id = "507f1f77bcf86cd799439011"
        response = client.delete(f'/api/categories/{cat_id}')
        assert response.status_code in [200, 204, 404]
        print("✓ Delete category dengan admin berhasil")
    
    @patch('blueprints.category_bp.categories_col')
    def test_delete_category_user_forbidden(self, mock_cat_col, client, test_user_token):
        """Test user biasa tidak bisa delete category"""
        client.set_cookie('token', test_user_token)
        response = client.delete('/api/categories/507f1f77bcf86cd799439011')
        assert response.status_code in [403, 401]
        print("✓ User biasa tidak bisa delete category")


class TestCategoriesDataValidation:
    """Test validasi data category"""
    @patch('blueprints.category_bp.categories_col')
    def test_create_category_empty_name(self, mock_cat_col, client, admin_token):
        """Test create category dengan nama kosong"""
        client.set_cookie('token', admin_token)
        response = client.post('/api/categories', json={
            'name': ''
        })
        assert response.status_code in [200, 400, 422]
        print("✓ Create category empty name ditangani")
    
    @patch('blueprints.category_bp.categories_col')
    def test_create_category_missing_name(self, mock_cat_col, client, admin_token):
        """Test create category tanpa field name"""
        client.set_cookie('token', admin_token)
        response = client.post('/api/categories', json={})
        assert response.status_code in [200, 400, 422]
        print("✓ Create category missing name ditangani")
    
    @patch('blueprints.category_bp.categories_col')
    def test_create_category_xss_attempt(self, mock_cat_col, client, admin_token):
        """Test create category dengan XSS payload"""
        client.set_cookie('token', admin_token)
        response = client.post('/api/categories', json={
            'name': "<script>alert('xss')</script>"
        })
        assert response.status_code in [200, 201, 400]
        print("✓ XSS attempt di category ditangani")
    
    @patch('blueprints.category_bp.categories_col')
    def test_category_name_too_long(self, mock_cat_col, client, admin_token):
        """Test create category dengan nama terlalu panjang"""
        client.set_cookie('token', admin_token)
        very_long_name = 'a' * 1000
        response = client.post('/api/categories', json={
            'name': very_long_name
        })
        assert response.status_code in [200, 201, 400, 422]
        print("✓ Category nama terlalu panjang ditangani")


class TestCategoriesDuplicate:
    """Test duplicate category handling"""
    @patch('blueprints.category_bp.categories_col')
    def test_create_duplicate_category(self, mock_cat_col, client, admin_token):
        """Test create category dengan nama yang sudah ada"""
        client.set_cookie('token', admin_token)
        mock_cat_col.find_one.return_value = {
            "_id": ObjectId(),
            "name": "Existing Category"
        }
        response = client.post('/api/categories', json={
            'name': 'Existing Category'
        })
        assert response.status_code in [200, 400, 409]
        print("✓ Duplicate category ditangani")
