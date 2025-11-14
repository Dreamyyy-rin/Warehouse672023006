from pymongo import MongoClient
from bson.json_util import loads
from bson.objectid import ObjectId
import re

class MongoConnection:
    def __init__(self, connection_string,db_name):
        self.connection_string = connection_string
        self.db_name = db_name
        self.client = None
        self.db = None
        self.__getConnection()

    def __getConnection(self):
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.db_name]
            self.client.admin.command('ping')
            print("Berhasil Connect ke MongoDB")
        except Exception as e:
            print(f"Gagal Connect ke MongoDB: {e}")

    def find(self, collection, query, project={},Limit=0, sort=[],multi = False):
        result ={
            'status': False,
            'data': None,
            'message': 'Terjadi kesalahan saat mengambil data'
        }
        try:
            if multi:
                resultFind = self.db[collection].find(query,projection=project,limit=Limit,sort=sort)
                resultFind = list(resultFind)
            else:
                resultFind = self.db[collection].find_one(query,projection=project,sort=sort)
            if resultFind:
                result['status'] = True
                result['data'] = resultFind
                result['message'] = 'Berhasil mengambil data'
        except Exception as e:
            print(f"Gagal mengambil data: {e}")
        return result

    def insert(self, collection, data,multi=False):
        result = {
            'status': False,
            'data': None,
            'message': 'Terjadi kesalahan saat menambahkan data'
        }
        try:
            if multi:
                resultInsert = self.db[collection].insert_many(data)
            else:
                resultInsert = self.db[collection].insert_one(data)
            if resultInsert.acknowledged:
                result['status'] = True
                result['message'] = 'Berhasil menambahkan data'
                if multi:
                    result['data'] = {'inserted_ids': resultInsert.inserted_ids}
                else:
                    result['data'] = {'inserted_id': resultInsert.inserted_id}
        except Exception as e:
            print(f"Gagal menambahkan data: {e}")
        return result

    def update(self, collection, query, data ,multi=False):
        result = {
            'status': False,
            'data': None,
            'message': 'Terjadi kesalahan saat memperbarui data'
        }
        try:
            if multi:
                resultUpdate = self.db[collection].update_many(query, {'$set': data})
            else:
                resultUpdate = self.db[collection].update_one(query, {'$set': data})
            if resultUpdate.acknowledged:
                result['status'] = True
                result['message'] = 'Berhasil memperbarui data'
                result['data'] = {
                    'matched_count': resultUpdate.matched_count,
                    'modified_count': resultUpdate.modified_count
                }
        except Exception as e:
            print(f"Gagal memperbarui data: {e}")
        return result

    def delete(self, collection, query,multi=False):
        result = {
            'status': False,
            'data': None,
            'message': 'Terjadi kesalahan saat menghapus data'
        }
        try:
            if multi:
                resultDelete = self.db[collection].delete_many(query)
            else:
                resultDelete = self.db[collection].delete_one(query)
            if resultDelete.acknowledged:
                result['status'] = True
                result['message'] = 'Berhasil menghapus data'
                result['data'] = {
                    'deleted_count': resultDelete.deleted_count
                }
        except Exception as e:
            print(f"Gagal menghapus data: {e}")
        return result

    # new wrapper
    def aggregate(self, collection, pipeline):
        try:
            cursor = self.db[collection].aggregate(pipeline)
            return list(cursor)
        except Exception as e:
            print(f"Gagal menjalankan aggregate: {e}")
            return []

class SafeMongoQuery:
    @staticmethod
    def escape_query(query):
        if isinstance(query, str):
            return re.escape(query)
        return query
        
    @staticmethod
    def safe_object_id(id_str):
        try:
            return ObjectId(id_str)
        except:
            return None
