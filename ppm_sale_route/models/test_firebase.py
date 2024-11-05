# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, config
# import firebase_admin
# from firebase_admin import credentials, firestore
#
# firebase_private_key_path = '/home/odoo-dev/Documents/Odoo/ppm_dev/ppm_sale_route/data/odoo-firebase-b5e0f-firebase-adminsdk-pn8bx-e949fc9483.json'
# firebase_database_url = 'https://odoo-firebase-b5e0f-default-rtdb.asia-southeast1.firebasedatabase.app/'
#
# firebase_cred = credentials.Certificate(firebase_private_key_path)
# firebase_app = firebase_admin.initialize_app(firebase_cred)
#
# firebase_db = firestore.client()
#
# doc_ref = firebase_db.collection("users").document("alovelace")
# doc_ref.set({"first": "Ada", "last": "Lovelace", "born": 1815})
