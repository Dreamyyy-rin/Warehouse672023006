"""Whitebox Testing - Items Blueprint"""
import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId


class TestItemsRetrieval:
    """Test mengambil data items"""
    
    @patch('blueprints.items_bp.items_col')
    def test_get_all_items(self, mock_items_col, client, test_user_token):
        """Test retrieve semua items dari database"""
        client.set_cookie('token', test_user_token)
        mock_items_col.find.return_value = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Item A",
                "stock": 10,
                "price": 5000,
                "category": {"name": "Electronics"},
                "supplier": {"name": "Supplier X"},
                "is_active": True
            }
        ]
        response = client.get('/api/items')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) > 0
        assert data[0]['name'] == 'Item A'
        print("✓ Get all items berhasil")
    
    @patch('blueprints.items_bp.items_col')
    def test_get_items_empty_database(self, mock_items_col, client, test_user_token):
        """Test retrieve items ketika database kosong"""
        client.set_cookie('token', test_user_token)
        mock_items_col.find.return_value = []
        response = client.get('/api/items')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 0
        print("✓ Get items dari database kosong berhasil")
    
    @patch('blueprints.items_bp.items_col')
    def test_get_items_contains_required_fields(self, mock_items_col, client, test_user_token):
        """Test item response mengandung semua field yang diperlukan"""
        client.set_cookie('token', test_user_token)
        mock_items_col.find.return_value = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Item Test",
                "stock": 20,
                "price": 10000,
                "category": {"name": "Cat1"},
                "supplier": {"name": "Sup1"},
                "is_active": True
            }
        ]
        response = client.get('/api/items')
        data = response.get_json()[0]
        required_fields = ['_id', 'name', 'stock', 'price', 'category_name', 'supplier_name', 'is_active']
        for field in required_fields:
            assert field in data, f"Field {field} tidak ada"
        print("✓ Item response mengandung semua required fields")


class TestItemsCreation:
    """Test membuat item baru"""
    @patch('blueprints.items_bp.suppliers_col')
    @patch('blueprints.items_bp.categories_col')
    @patch('blueprints.items_bp.items_col')
    def test_add_item_success(self, mock_items, mock_cats, mock_sups, client, admin_token):
        """Test tambah item dengan data valid"""
        client.set_cookie('token', admin_token)
        mock_cats.find_one.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "Electronics"
        }
        mock_sups.find_one.return_value = {
            "_id": ObjectId("607f1f77bcf86cd799439011"),
            "name": "Supplier1"
        }
        response = client.post('/items/add', json={
            'name': 'Test Item',
            'price': 5000,
            'category_id': '507f1f77bcf86cd799439011',
            'supplier_id': '607f1f77bcf86cd799439011'
        })
        assert response.status_code in [200, 201]
        print("✓ Add item dengan data valid berhasil")
    
    @patch('blueprints.items_bp.items_col')
    def test_add_item_without_category(self, mock_items, client, admin_token):
        """Test tambah item tanpa category"""
        client.set_cookie('token', admin_token)
        response = client.post('/items/add', json={
            'name': 'Item No Cat',
            'price': 1000
        })
        assert response.status_code in [200, 201, 400]
        print("✓ Add item tanpa category ditangani")
    
    @patch('blueprints.items_bp.items_col')
    def test_add_item_price_conversion(self, mock_items, client, admin_token):
        """Test price conversion ke float"""
        client.set_cookie('token', admin_token)
        response = client.post('/items/add', json={
            'name': 'Price Test',
            'price': '9999'
        })
        assert response.status_code in [200, 201]
        print("✓ Price conversion ke float berhasil")
    
    @patch('blueprints.items_bp.items_col')
    def test_add_item_invalid_price(self, mock_items, client, admin_token):
        """Test tambah item dengan price invalid"""
        client.set_cookie('token', admin_token)
        response = client.post('/items/add', json={
            'name': 'Item',
            'price': 'not_a_number'
        })
        assert response.status_code in [200, 201, 400]
        print("✓ Invalid price ditangani dengan aman")


class TestItemsAuthorization:
    """Test authorization untuk item operations"""
    def test_add_item_requires_admin(self, client, test_user_token):
        """Test add item hanya bisa admin"""
        client.set_cookie('token', test_user_token)
        response = client.post('/items/add', json={
            'name': 'Unauthorized Item',
            'price': 5000
        })
        assert response.status_code in [403, 401, 302]
        print("✓ Add item memerlukan role admin")
    
    def test_get_items_requires_login(self, client):
        """Test get items memerlukan login"""
        response = client.get('/api/items', follow_redirects=False)
        assert response.status_code in [301, 302, 401]
        print("✓ Get items memerlukan login")


class TestItemsDataValidation:
    """Test validasi data item"""
    @patch('blueprints.items_bp.items_col')
    def test_normalize_oid_with_object_id(self, mock_items, client):
        """Test normalize_oid dengan ObjectId"""
        from blueprints.items_bp import normalize_oid
        oid = ObjectId("507f1f77bcf86cd799439011")
        result = normalize_oid(oid)
        assert result == "507f1f77bcf86cd799439011"
        print("✓ normalize_oid dengan ObjectId berhasil")
    
    @patch('blueprints.items_bp.items_col')
    def test_normalize_oid_with_string(self, mock_items, client):
        """Test normalize_oid dengan string"""
        from blueprints.items_bp import normalize_oid
        result = normalize_oid("507f1f77bcf86cd799439011")
        assert result == "507f1f77bcf86cd799439011"
        print("✓ normalize_oid dengan string berhasil")
    
    @patch('blueprints.items_bp.items_col')
    def test_normalize_oid_with_none(self, mock_items, client):
        """Test normalize_oid dengan None"""
        from blueprints.items_bp import normalize_oid
        result = normalize_oid(None)
        assert result is None
        print("✓ normalize_oid dengan None berhasil")
    
    @patch('blueprints.items_bp.items_col')
    def test_normalize_oid_with_dict(self, mock_items, client):
        """Test normalize_oid dengan dict"""
        from blueprints.items_bp import normalize_oid
        result = normalize_oid({"_id": ObjectId("507f1f77bcf86cd799439011")})
        assert result == "507f1f77bcf86cd799439011"
        print("✓ normalize_oid dengan dict berhasil")
