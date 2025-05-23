from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import sqlite3
from datetime import datetime
import csv
import io
import os

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # Needed for flash messages

# Database file name
DATABASE = 'bachatgat.db'

# --- Database Helper Functions (Keep these as they are) ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Ensure all tables (groups, users, transactions, loans, interest_distributions) are defined as before
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            bank_account_details TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            group_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            is_cash_payment BOOLEAN DEFAULT 0,
            is_paid BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            principal_amount REAL NOT NULL,
            outstanding_balance REAL NOT NULL,
            interest_rate_per_month REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interest_distributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            user_id_paying_interest INTEGER NOT NULL,
            amount_paid_as_interest REAL NOT NULL,
            date TEXT NOT NULL,
            distributed_to_group_id INTEGER NOT NULL,
            FOREIGN KEY (loan_id) REFERENCES loans (id),
            FOREIGN KEY (user_id_paying_interest) REFERENCES users (id),
            FOREIGN KEY (distributed_to_group_id) REFERENCES groups (id)
        )
    ''')
    conn.commit()
    conn.close()

# --- Helper Functions for Data Retrieval (Keep these as they are) ---
def get_user(user_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def get_group(group_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    group = conn.execute('SELECT * FROM groups WHERE id = ?', (group_id,)).fetchone()
    conn.close()
    return group

def get_admin_user_id():
    conn = get_db_connection()
    admin_user = conn.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1").fetchone()
    conn.close()
    return admin_user['id'] if admin_user else None

# --- Core Business Logic Functions (Keep these as they are) ---
def calculate_group_balance(group_id):
    conn = get_db_connection()
    total_contributions = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'monthly_contribution' AND is_paid = 1",
        (group_id,)
    ).fetchone()[0] or 0.0
    total_loans_disbursed = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'loan_disbursement'",
        (group_id,)
    ).fetchone()[0] or 0.0
    total_interest_received = conn.execute(
        "SELECT SUM(amount_paid_as_interest) FROM interest_distributions WHERE distributed_to_group_id = ?",
        (group_id,)
    ).fetchone()[0] or 0.0
    conn.close()
    return total_contributions - total_loans_disbursed + total_interest_received

def get_loan_details(loan_id):
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id = ?', (loan_id,)).fetchone()
    conn.close()
    return loan

def distribute_interest_to_group(group_id, amount_to_distribute, loan_id, user_id_paying_interest, date):
    conn = get_db_connection()
    active_users_in_group = conn.execute(
        "SELECT id FROM users WHERE group_id = ? AND status = 'active'", (group_id,)
    ).fetchall()
    if not active_users_in_group:
        flash(f"No active users in group {group_id} to distribute interest.", 'warning')
        conn.close()
        return
    num_users = len(active_users_in_group)
    amount_per_user = amount_to_distribute / num_users
    for user_row in active_users_in_group:
        user_id = user_row['id']
        conn.execute(
            "INSERT INTO transactions (user_id, group_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, group_id, 'interest_distribution', amount_per_user, date,
             f"Share of interest from Loan ID {loan_id} (Paid by User ID {user_id_paying_interest})")
        )
        conn.execute(
            "INSERT INTO interest_distributions (loan_id, user_id_paying_interest, amount_paid_as_interest, date, distributed_to_group_id) VALUES (?, ?, ?, ?, ?)",
            (loan_id, user_id_paying_interest, amount_per_user, date, group_id)
        )
    conn.commit()
    conn.close()
    flash(f"Interest of ₹{amount_to_distribute:.2f} distributed among {num_users} users in the group.", 'success')

# --- Flask Routes ---

@app.route('/')
def index():
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM groups').fetchall()
    selected_group_id = request.args.get('group_id', type=int)

    users = []
    user_transactions = {}
    user_loans = {}
    group_balance = 0.0
    admin_user_id = get_admin_user_id()

    if selected_group_id:
        users = conn.execute('SELECT * FROM users WHERE group_id = ? ORDER BY name ASC', (selected_group_id,)).fetchall()
        group_balance = calculate_group_balance(selected_group_id)

        for user in users:
            transactions = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC",
                (user['id'],)
            ).fetchall()
            user_transactions[user['id']] = transactions

            loans = conn.execute(
                "SELECT * FROM loans WHERE user_id = ? AND status = 'active' ORDER BY start_date DESC",
                (user['id'],)
            ).fetchall()
            user_loans[user['id']] = loans

    conn.close()

    # Calculate reports for the selected group
    reports = {}
    if selected_group_id:
        conn = get_db_connection()
        total_investment = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'monthly_contribution' AND is_paid = 1",
            (selected_group_id,)
        ).fetchone()[0] or 0.0
        total_loan_repaid_by_group_members = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'loan_repayment'",
            (selected_group_id,)
        ).fetchone()[0] or 0.0
        total_interest_received_by_group = conn.execute(
            "SELECT SUM(amount_paid_as_interest) FROM interest_distributions WHERE distributed_to_group_id = ?",
            (selected_group_id,)
        ).fetchone()[0] or 0.0
        overall_profit = total_interest_received_by_group

        current_year = datetime.now().strftime('%Y')
        current_month = datetime.now().strftime('%Y-%m')

        monthly_profit = conn.execute(
            "SELECT SUM(amount_paid_as_interest) FROM interest_distributions WHERE distributed_to_group_id = ? AND date LIKE ?",
            (selected_group_id, f'{current_month}%')
        ).fetchone()[0] or 0.0
        yearly_profit = conn.execute(
            "SELECT SUM(amount_paid_as_interest) FROM interest_distributions WHERE distributed_to_group_id = ? AND date LIKE ?",
            (selected_group_id, f'{current_year}%')
        ).fetchone()[0] or 0.0
        monthly_investment = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'monthly_contribution' AND is_paid = 1 AND date LIKE ?",
            (selected_group_id, f'{current_month}%')
        ).fetchone()[0] or 0.0
        yearly_investment = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'monthly_contribution' AND is_paid = 1 AND date LIKE ?",
            (selected_group_id, f'{current_year}%')
        ).fetchone()[0] or 0.0

        reports = {
            'total_investment': total_investment,
            'total_loan_repaid': total_loan_repaid_by_group_members,
            'total_interest_received': total_interest_received_by_group,
            'overall_profit': overall_profit,
            'monthly_profit': monthly_profit,
            'yearly_profit': yearly_profit,
            'monthly_investment': monthly_investment,
            'yearly_investment': yearly_investment,
        }
        conn.close()

    return render_template('index.html',
                           groups=groups,
                           users=users,
                           selected_group_id=selected_group_id,
                           user_transactions=user_transactions,
                           user_loans=user_loans,
                           group_balance=group_balance,
                           reports=reports,
                           admin_user_id=admin_user_id,
                           current_date=datetime.now().strftime('%Y-%m-%d'),
                           get_group=get_group)

@app.route('/add_group', methods=['POST'])
def add_group():
    name = request.form['group_name']
    bank_account_details = request.form.get('bank_account_details', '')
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO groups (name, bank_account_details) VALUES (?, ?)', (name, bank_account_details))
        conn.commit()
        flash('Group added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Error: Group with this name already exists.', 'danger')
    except Exception as e:
        flash(f'Error adding group: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/add_user', methods=['POST'])
def add_user():
    """Adds a new user to a selected group."""
    name = request.form['user_name']
    group_id = request.form['group_id']
    is_admin = request.form.get('is_admin') == 'on'
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (name, group_id, is_admin, status) VALUES (?, ?, ?, ?)',
                     (name, group_id, is_admin, 'active'))
        conn.commit()
        flash(f'User "{name}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding user: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    if get_admin_user_id() != 1:
        flash("Unauthorized access.", 'danger')
        user_info = get_user(user_id)
        return redirect(url_for('index', group_id=user_info['group_id'] if user_info else None))
    conn = get_db_connection()
    user = conn.execute('SELECT status FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_status = 'inactive' if user['status'] == 'active' else 'active'
        conn.execute('UPDATE users SET status = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        flash(f'User status changed to "{new_status}".', 'success')
    else:
        flash('User not found.', 'danger')
    conn.close()
    user_info = get_user(user_id)
    return redirect(url_for('index', group_id=user_info['group_id'] if user_info else None))

@app.route('/add_monthly_contribution/<int:user_id>', methods=['POST'])
def add_monthly_contribution(user_id):
    amount = float(request.form['amount'])
    date = datetime.now().strftime('%Y-%m-%d')
    is_cash_payment = request.form.get('is_cash_payment') == 'on'
    is_paid = 0 if is_cash_payment else 1

    user = get_user(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO transactions (user_id, group_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, user['group_id'], 'monthly_contribution', amount, date, 'Monthly Contribution', is_cash_payment, is_paid)
        )
        conn.commit()
        flash(f'Contribution of ₹{amount:.2f} added for {user["name"]}. Status: {"Pending Cash Payment" if is_cash_payment else "Paid (UPI/Bank)"}', 'success')
    except Exception as e:
        flash(f'Error adding contribution: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('index', group_id=user['group_id']))

@app.route('/mark_payment_paid/<int:transaction_id>', methods=['POST'])
def mark_payment_paid(transaction_id):
    if get_admin_user_id() != 1:
        flash("Unauthorized access.", 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    transaction = conn.execute('SELECT user_id, group_id, is_paid FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
    if transaction and transaction['is_paid'] == 0:
        conn.execute('UPDATE transactions SET is_paid = 1 WHERE id = ?', (transaction_id,))
        conn.commit()
        flash('Cash payment marked as paid.', 'success')
    elif transaction and transaction['is_paid'] == 1:
        flash('Payment is already marked as paid.', 'info')
    else:
        flash('Transaction not found or not a pending cash payment.', 'danger')
    conn.close()
    return redirect(url_for('index', group_id=transaction['group_id'] if transaction else None))

@app.route('/disburse_loan/<int:user_id>', methods=['POST'])
def disburse_loan(user_id):
    amount = float(request.form['loan_amount'])
    interest_rate_percent = float(request.form['interest_rate'])
    start_date = request.form['start_date']
    end_date = request.form.get('end_date')
    interest_rate_per_month = interest_rate_percent / 100.0

    user = get_user(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO transactions (user_id, group_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, user['group_id'], 'loan_disbursement', amount, start_date, f'Loan Disbursed to {user["name"]}')
        )
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO loans (user_id, group_id, principal_amount, outstanding_balance, interest_rate_per_month, start_date, end_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, user['group_id'], amount, amount, interest_rate_per_month, start_date, end_date, 'active')
        )
        conn.commit()
        flash(f'Loan of ₹{amount:.2f} disbursed to {user["name"]}.', 'success')
    except Exception as e:
        flash(f'Error disbursing loan: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('index', group_id=user['group_id']))

@app.route('/repay_loan/<int:loan_id>', methods=['POST'])
def repay_loan(loan_id):
    repayment_amount = float(request.form['repayment_amount'])
    repayment_date = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id = ?', (loan_id,)).fetchone()

    if not loan:
        flash('Loan not found.', 'danger')
        conn.close()
        return redirect(url_for('index'))
    if loan['status'] == 'paid_off':
        flash('This loan has already been paid off.', 'info')
        conn.close()
        return redirect(url_for('index', group_id=loan['group_id']))

    outstanding_balance = loan['outstanding_balance']
    interest_rate = loan['interest_rate_per_month']
    interest_due = outstanding_balance * interest_rate
    if interest_due < 0:
        interest_due = 0

    principal_paid = 0.0
    interest_paid_portion = 0.0

    if repayment_amount >= interest_due:
        interest_paid_portion = interest_due
        principal_paid = repayment_amount - interest_due
    else:
        interest_paid_portion = repayment_amount
        principal_paid = 0.0

    new_outstanding_balance = outstanding_balance - principal_paid
    if new_outstanding_balance < 0:
        principal_paid = outstanding_balance
        new_outstanding_balance = 0
        interest_paid_portion = repayment_amount - principal_paid

    if interest_paid_portion < 0:
        interest_paid_portion = 0

    try:
        conn.execute(
            'UPDATE loans SET outstanding_balance = ? WHERE id = ?',
            (new_outstanding_balance, loan_id)
        )
        conn.execute(
            'INSERT INTO transactions (user_id, group_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?)',
            (loan['user_id'], loan['group_id'], 'loan_repayment', repayment_amount, repayment_date,
             f'Loan Repayment for Loan ID {loan_id} (Principal: ₹{principal_paid:.2f}, Interest: ₹{interest_paid_portion:.2f})')
        )
        if interest_paid_portion > 0:
            distribute_interest_to_group(
                loan['group_id'], interest_paid_portion, loan_id, loan['user_id'], repayment_date
            )
        if new_outstanding_balance <= 0:
            conn.execute('UPDATE loans SET status = "paid_off" WHERE id = ?', (loan_id,))
            flash(f'Loan ID {loan_id} has been fully paid off!', 'info')
        conn.commit()
        flash(f'Loan repayment of ₹{repayment_amount:.2f} processed for Loan ID {loan_id}. Remaining balance: ₹{new_outstanding_balance:.2f}.', 'success')
    except Exception as e:
        flash(f'Error processing loan repayment: {e}', 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=loan['group_id']))


# Keep your existing bulk_upload for transactions
@app.route('/bulk_upload', methods=['GET', 'POST'])
def bulk_upload():
    selected_group_id = request.args.get('group_id', type=int)
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['csv_file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            stream = io.TextIOWrapper(file, encoding='utf-8')
            csv_reader = csv.DictReader(stream)
            processed_count = 0
            error_count = 0
            messages = []
            conn = get_db_connection()
            try:
                for row in csv_reader:
                    try:
                        user_name = row.get('user_name')
                        transaction_type = row.get('type')
                        amount = float(row.get('amount'))
                        date = row.get('date', datetime.now().strftime('%Y-%m-%d'))
                        is_cash = row.get('is_cash_payment', '0').lower() in ['1', 'true', 'yes']
                        is_paid_status = row.get('is_paid', '1').lower() in ['1', 'true', 'yes']
                        user = conn.execute(
                            'SELECT id, group_id FROM users WHERE name = ? AND group_id = ?',
                            (user_name, selected_group_id)
                        ).fetchone()
                        if not user:
                            messages.append(f"Skipping row for user '{user_name}': User not found in selected group.")
                            error_count += 1
                            continue
                        user_id = user['id']
                        group_id = user['group_id']
                        if transaction_type == 'contribution':
                            conn.execute(
                                'INSERT INTO transactions (user_id, group_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                (user_id, group_id, 'monthly_contribution', amount, date, 'Bulk Uploaded Contribution', is_cash, is_paid_status)
                            )
                            messages.append(f"Processed contribution of ₹{amount} for {user_name}.")
                            processed_count += 1
                        elif transaction_type == 'loan_repayment':
                            loan_id = row.get('loan_id', type=int)
                            if not loan_id:
                                messages.append(f"Skipping loan repayment for '{user_name}': 'loan_id' is missing.")
                                error_count += 1
                                continue
                            loan = conn.execute('SELECT * FROM loans WHERE id = ? AND user_id = ?', (loan_id, user_id)).fetchone()
                            if not loan:
                                messages.append(f"Skipping loan repayment for '{user_name}': Loan ID {loan_id} not found for this user.")
                                error_count += 1
                                continue
                            outstanding_balance = loan['outstanding_balance']
                            interest_rate = loan['interest_rate_per_month']
                            interest_due = outstanding_balance * interest_rate
                            if interest_due < 0: interest_due = 0
                            principal_paid = 0.0
                            interest_paid_portion = 0.0
                            if amount >= interest_due:
                                interest_paid_portion = interest_due
                                principal_paid = amount - interest_due
                            else:
                                interest_paid_portion = amount
                                principal_paid = 0.0
                            new_outstanding_balance = outstanding_balance - principal_paid
                            if new_outstanding_balance < 0:
                                principal_paid = outstanding_balance
                                new_outstanding_balance = 0
                                interest_paid_portion = amount - principal_paid
                            if interest_paid_portion < 0: interest_paid_portion = 0
                            conn.execute(
                                'UPDATE loans SET outstanding_balance = ? WHERE id = ?',
                                (new_outstanding_balance, loan_id)
                            )
                            conn.execute(
                                'INSERT INTO transactions (user_id, group_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?)',
                                (user_id, group_id, 'loan_repayment', amount, date,
                                 f'Bulk Uploaded Loan Repayment for Loan ID {loan_id} (Principal: ₹{principal_paid:.2f}, Interest: ₹{interest_paid_portion:.2f})')
                            )
                            if interest_paid_portion > 0:
                                distribute_interest_to_group(group_id, interest_paid_portion, loan_id, user_id, date)
                            if new_outstanding_balance <= 0:
                                conn.execute('UPDATE loans SET status = "paid_off" WHERE id = ?', (loan_id,))
                            messages.append(f"Processed loan repayment of ₹{amount} for {user_name} (Loan ID {loan_id}).")
                            processed_count += 1
                        else:
                            messages.append(f"Skipping row for user '{user_name}': Unknown transaction type '{transaction_type}'.")
                            error_count += 1
                    except Exception as row_e:
                        messages.append(f"Error processing row for user '{row.get('user_name', 'N/A')}': {row_e}")
                        error_count += 1
                conn.commit()
                flash(f'Bulk upload complete. Processed {processed_count} rows, {error_count} errors. See details below.', 'info')
                for msg in messages:
                    flash(msg, 'info')
            except Exception as e:
                conn.rollback()
                flash(f'Error during bulk upload: {e}', 'danger')
            finally:
                conn.close()
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
    return render_template('bulk_upload.html', selected_group_id=selected_group_id)

@app.route('/download_sample_csv')
def download_sample_csv():
    sample_csv_content = """user_name,type,amount,date,is_cash_payment,is_paid,loan_id
John Doe,contribution,2000,2024-05-20,0,1,
Jane Smith,loan_repayment,5000,2024-05-21,0,1,1
John Doe,contribution,2000,2024-06-20,1,0,
"""
    return io.BytesIO(sample_csv_content.encode('utf-8')), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=sample_bulk_upload.csv'
    }


# --- NEW: Bulk User Upload Route ---
@app.route('/bulk_upload_users', methods=['GET', 'POST'])
def bulk_upload_users():
    selected_group_id = request.args.get('group_id', type=int) # This will be passed from index.html

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['csv_file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            stream = io.TextIOWrapper(file, encoding='utf-8')
            csv_reader = csv.DictReader(stream)
            processed_count = 0
            error_count = 0
            messages = []

            conn = get_db_connection()
            try:
                for row in csv_reader:
                    try:
                        user_name = row.get('user_name')
                        group_identifier = row.get('group_id') or row.get('group_name') # Can use ID or Name
                        is_admin = row.get('is_admin', '0').lower() in ['1', 'true', 'yes'] # Default to not admin
                        status = row.get('status', 'active') # Default to active

                        if not user_name or not group_identifier:
                            messages.append(f"Skipping row: 'user_name' or 'group_id'/'group_name' missing in row: {row}")
                            error_count += 1
                            continue

                        # Determine group_id from identifier (can be ID or Name)
                        target_group_id = None
                        if str(group_identifier).isdigit(): # If it looks like an ID
                            target_group_id = int(group_identifier)
                        else: # Try to find by name
                            group_row = conn.execute('SELECT id FROM groups WHERE name = ?', (group_identifier,)).fetchone()
                            if group_row:
                                target_group_id = group_row['id']
                            else:
                                messages.append(f"Skipping user '{user_name}': Group '{group_identifier}' not found.")
                                error_count += 1
                                continue

                        # Check if user already exists in this specific group
                        existing_user = conn.execute(
                            'SELECT id FROM users WHERE name = ? AND group_id = ?',
                            (user_name, target_group_id)
                        ).fetchone()
                        if existing_user:
                            messages.append(f"Skipping user '{user_name}': User already exists in Group ID {target_group_id}.")
                            error_count += 1
                            continue

                        conn.execute(
                            'INSERT INTO users (name, group_id, is_admin, status) VALUES (?, ?, ?, ?)',
                            (user_name, target_group_id, is_admin, status)
                        )
                        messages.append(f"Added user '{user_name}' to Group ID {target_group_id}.")
                        processed_count += 1

                    except Exception as row_e:
                        messages.append(f"Error processing row for user '{row.get('user_name', 'N/A')}': {row_e}")
                        error_count += 1
                conn.commit()
                flash(f'Bulk user upload complete. Processed {processed_count} rows, {error_count} errors. See details below.', 'info')
                for msg in messages:
                    flash(msg, 'info') # Display individual messages
            except Exception as e:
                conn.rollback()
                flash(f'Error during bulk user upload: {e}', 'danger')
            finally:
                conn.close()
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
    return render_template('bulk_upload_users.html', selected_group_id=selected_group_id)

@app.route('/download_sample_users_csv')
def download_sample_users_csv():
    sample_csv_content = """user_name,group_id,is_admin,status
Alice,1,0,active
Bob,1,1,active
Charlie,2,0,active
""" # Example with group_id. You can also use group_name if that's easier for users.
    return io.BytesIO(sample_csv_content.encode('utf-8')), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=sample_users_upload.csv'
    }


# --- Run the application ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)