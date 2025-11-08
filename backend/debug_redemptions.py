import sqlite3
import json
from datetime import datetime

DB_PATH = "app/database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("DEBUGGING REDEMPTION CODES")
print("=" * 80)

# Check all loyalty accounts
print("\n1. All Loyalty Accounts:")
cursor.execute("SELECT id, user_id, points_balance FROM loyalty_accounts")
accounts = cursor.fetchall()
for account_id, user_id, points in accounts:
    print(f"  Account {account_id}: User {user_id}, Points: {points}")

# Check all redemptions
print("\n2. All Redemptions:")
cursor.execute("""
    SELECT id, loyalty_account_id, reward_code, reward_value, status, 
           expires_at, redemption_type, created_at
    FROM redemptions
""")
redemptions = cursor.fetchall()
for row in redemptions:
    redemption_id, acct_id, code, value, status, expires, rtype, created = row
    print(f"  ID {redemption_id}: Code='{code}', Value={value}, Status='{status}', Expires={expires}")

# Check specifically for customer1 (usually user_id = 1)
print("\n3. Redemptions for User 1 (customer1):")
cursor.execute("""
    SELECT la.id, r.reward_code, r.reward_value, r.status, r.expires_at
    FROM loyalty_accounts la
    JOIN redemptions r ON la.id = r.loyalty_account_id
    WHERE la.user_id = 1
""")
user1_redemptions = cursor.fetchall()
if user1_redemptions:
    for acct_id, code, value, status, expires in user1_redemptions:
        print(f"  Account {acct_id}: Code='{code}', Value={value}, Status='{status}', Expires={expires}")
else:
    print("  No redemptions found for user 1")

# Check loyalty transactions
print("\n4. Loyalty Transactions for User 1:")
cursor.execute("""
    SELECT id, loyalty_account_id, points_earned, points_spent, transaction_type, created_at
    FROM loyalty_transactions
    WHERE loyalty_account_id IN (SELECT id FROM loyalty_accounts WHERE user_id = 1)
""")
transactions = cursor.fetchall()
for trans_id, acct_id, earned, spent, trans_type, created in transactions:
    print(f"  Transaction {trans_id}: Earned={earned}, Spent={spent}, Type='{trans_type}'")

# Check all users
print("\n5. All Users:")
cursor.execute("SELECT id, email, full_name FROM users LIMIT 10")
users = cursor.fetchall()
for user_id, email, name in users:
    print(f"  User {user_id}: {email} ({name})")

conn.close()

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("If there are no redemptions with status 'active', you need to:")
print("1. Redeem loyalty points to create a discount code, OR")
print("2. Create test redemption codes via the loyalty/redeem endpoint, OR")
print("3. Add test data directly to the database")
print("=" * 80)
