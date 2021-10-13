'''
for future integrations
from pymongo import MongoClient
db_client = MongoClient(port=27017)
db = db_client.admin.up_database_test

result = db.insert_one({'user': 'h.tony.deng@gmail.com', 'code': 'cododooo'})

from security import SecurityClient
crypt = SecurityClient(config('SECRET_KEY'), config('SECRET_PASSWORD'))
print(crypt.encryptPayload({'hello': 'world'}))
'''
