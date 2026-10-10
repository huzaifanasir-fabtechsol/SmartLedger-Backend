import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'
os.environ['POSTGRES_DB'] = 'taxmgmt_db'
os.environ['POSTGRES_USER'] = 'taxmgmt_user'
os.environ['POSTGRES_PASSWORD'] = 'taxmgmt_db_secure_pass_9281'
os.environ['POSTGRES_HOST'] = '127.0.0.1'
os.environ['POSTGRES_PORT'] = '5433'

import django
from django.conf import settings

# Modify DATABASES setting before or after setup properly
django.setup()

from django.db import connections
from django.apps import apps
from django.core.management.color import no_style

# Configure sqlite properly in connections
settings.DATABASES['sqlite'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db.sqlite3',
    'USER': '',
    'PASSWORD': '',
    'HOST': '',
    'PORT': '',
    'TIME_ZONE': None,
    'CONN_MAX_AGE': 0,
    'CONN_HEALTH_CHECKS': False,
    'OPTIONS': {},
    'AUTOCOMMIT': True,
    'ATOMIC_REQUESTS': False,
    'TEST': {},
}

models_in_order = [
    # Auth & Account
    ('account', 'User'),
    ('account', 'TaxRate'),
    ('authtoken', 'Token'),
    ('auth', 'Group'),
    
    # Revenue foundational
    ('revenue', 'CarCategory'),
    ('revenue', 'Customer'),
    ('revenue', 'Saler'),
    ('revenue', 'CompanyAccount'),
    ('revenue', 'Auction'),
    ('revenue', 'Car'),
    ('revenue', 'Transaction'),
    ('revenue', 'Order'),
    ('revenue', 'OrderItem'),
    
    # Expense
    ('expense', 'ExpenseCategory'),
    ('expense', 'Restaurant'),
    ('expense', 'SparePart'),
    ('expense', 'Expense'),
    
    # HR
    ('hr', 'Employee'),
    ('hr', 'Salary'),
]

print("Starting data migration from db.sqlite3 to PostgreSQL...")

for app_label, model_name in models_in_order:
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        print(f"Skipping {app_label}.{model_name} (not found)")
        continue
    
    source_count = model.objects.using('sqlite').count()
    if source_count == 0:
        print(f"- {app_label}.{model_name}: 0 objects found.")
        continue
    
    print(f"- Migrating {source_count} objects for {app_label}.{model_name}...")
    
    # Fetch all records from sqlite
    sqlite_objs = list(model.objects.using('sqlite').all())
    
    # Delete any existing in postgres to avoid conflict
    model.objects.using('default').all().delete()
    
    # Bulk create into PostgreSQL
    batch_size = 500
    for i in range(0, len(sqlite_objs), batch_size):
        chunk = sqlite_objs[i:i+batch_size]
        model.objects.using('default').bulk_create(chunk, ignore_conflicts=False)
    
    # Reset sequence if model has an AutoField id
    with connections['default'].cursor() as cursor:
        sequence_sql = connections['default'].ops.sequence_reset_sql(no_style(), [model])
        for sql in sequence_sql:
            try:
                cursor.execute(sql)
            except Exception as e:
                print(f"  Warning sequence reset: {e}")
            
    print(f"  ✓ Successfully copied {len(sqlite_objs)} {model_name} objects and reset sequences.")

# Also handle m2m relationships if any (e.g. User.groups, User.user_permissions)
from django.db import connection as pg_conn
sqlite_conn = connections['sqlite']

with sqlite_conn.cursor() as s_cur:
    # Users groups
    s_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_groups';")
    if s_cur.fetchone():
        s_cur.execute("SELECT id, user_id, group_id FROM users_groups;")
        user_groups = s_cur.fetchall()
        if user_groups:
            with pg_conn.cursor() as p_cur:
                p_cur.execute("TRUNCATE TABLE users_groups RESTART IDENTITY CASCADE;")
                for row in user_groups:
                    p_cur.execute("INSERT INTO users_groups (id, user_id, group_id) VALUES (%s, %s, %s);", row)
                p_cur.execute("SELECT setval(pg_get_serial_sequence('users_groups', 'id'), coalesce(max(id), 1)) FROM users_groups;")
            print(f"  ✓ Copied {len(user_groups)} users_groups records.")

    # Users user_permissions
    s_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_user_permissions';")
    if s_cur.fetchone():
        s_cur.execute("SELECT id, user_id, permission_id FROM users_user_permissions;")
        user_perms = s_cur.fetchall()
        if user_perms:
            with pg_conn.cursor() as p_cur:
                p_cur.execute("TRUNCATE TABLE users_user_permissions RESTART IDENTITY CASCADE;")
                for row in user_perms:
                    p_cur.execute("INSERT INTO users_user_permissions (id, user_id, permission_id) VALUES (%s, %s, %s);", row)
                p_cur.execute("SELECT setval(pg_get_serial_sequence('users_user_permissions', 'id'), coalesce(max(id), 1)) FROM users_user_permissions;")
            print(f"  ✓ Copied {len(user_perms)} users_user_permissions records.")

print("All data migrated from SQLite to PostgreSQL successfully!")
