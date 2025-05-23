from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import sqlite3
from datetime import datetime, date
import csv
import io
import os

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # Keep this for flash messages

# Database file name
DATABASE = 'bachatgat.db'

# --- Database Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated groups table to include group_profit and default_interest_rate
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            bank_account_details TEXT,
            group_profit REAL DEFAULT 0.0,
            default_interest_rate REAL DEFAULT 12.0
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
    
    # Updated transactions table to optionally link to loans
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            group_id INTEGER NOT NULL,
            loan_id INTEGER, -- New: Link to loans table
            type TEXT NOT NULL, -- 'contribution', 'loan_disbursement', 'loan_repayment', 'interest_paid'
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            is_cash_payment BOOLEAN DEFAULT 0,
            is_paid BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id),
            FOREIGN KEY (loan_id) REFERENCES loans (id)
        )
    ''')
    
    # Updated loans table for better tracking and dynamic interest rates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            original_amount REAL NOT NULL,
            outstanding_balance REAL NOT NULL,
            current_interest_rate REAL NOT NULL, -- Annual rate, e.g., 12.0 for 12%
            issue_date TEXT NOT NULL,
            last_interest_calc_date TEXT NOT NULL, -- Date interest was last factored into balance or paid
            status TEXT DEFAULT 'active', -- 'active', 'paid_off', 'default'
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    
    # The 'interest_distributions' table is no longer strictly needed as 'interest_paid' will directly
    # update 'group_profit' and be recorded as a transaction.
    # If you still need a detailed breakdown for audit, you can keep it, but it's redundant for profit.
    # I'm commenting it out as per the new logic of direct group profit update.
    # cursor.execute('''
    #     CREATE TABLE IF NOT EXISTS interest_distributions (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         loan_id INTEGER NOT NULL,
    #         user_id_paying_interest INTEGER NOT NULL,
    #         amount_paid_as_interest REAL NOT NULL,
    #         date TEXT NOT NULL,
    #         distributed_to_group_id INTEGER NOT NULL,
    #         FOREIGN KEY (loan_id) REFERENCES loans (id),
    #         FOREIGN KEY (user_id_paying_interest) REFERENCES users (id),
    #         FOREIGN KEY (distributed_to_group_id) REFERENCES groups (id)
    #     )
    # ''')
    conn.commit()
    conn.close()

# --- Helper Functions for Data Retrieval ---
def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def get_group(group_id):
    conn = get_db_connection()
    group = conn.execute('SELECT * FROM groups WHERE id = ?', (group_id,)).fetchone()
    conn.close()
    return group

def get_admin_user_id():
    conn = get_db_connection()
    admin_user = conn.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1").fetchone()
    conn.close()
    return admin_user['id'] if admin_user else None

def get_loan_details(loan_id):
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id = ?', (loan_id,)).fetchone()
    conn.close()
    return loan

# --- Core Business Logic Functions ---

# Refactored: Group profit is now directly stored and updated in the groups table
def calculate_group_balance(group_id):
    conn = get_db_connection()
    # The group_profit from the table directly reflects the profit
    group_profit_from_db = conn.execute(
        "SELECT group_profit FROM groups WHERE id = ?", (group_id,)
    ).fetchone()
    conn.close()
    return group_profit_from_db[0] if group_profit_from_db else 0.0


# New: Function to calculate simple interest due
def calculate_interest_due(principal, annual_interest_rate_percent, start_date_str, end_date_str):
    if not principal or principal <= 0:
        return 0.0

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return 0.0 # Handle invalid date formats

    if end_date < start_date:
        return 0.0

    days = (end_date - start_date).days
    annual_interest_rate_decimal = annual_interest_rate_percent / 100.0
    daily_interest_rate = annual_interest_rate_decimal / 365.0 # Assuming 365 days for simplicity

    interest = principal * daily_interest_rate * days
    return round(interest, 2) # Round to 2 decimal places for currency


# The 'distribute_interest_to_group' is removed as interest_paid will directly update group_profit.
# If you need to record individual distributions, you'd need a different mechanism or reintroduce
# a modified version of this function that only tracks the distribution, not the profit addition.

# --- Flask Routes ---

@app.route('/')
def index():
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM groups').fetchall()
    selected_group_id = request.args.get('group_id', type=int)

    users = []
    user_transactions = {}
    user_loans = {}
    group_current_profit = 0.0 # Renamed for clarity to reflect what's stored in group_profit
    admin_user_id = get_admin_user_id()

    if selected_group_id:
        users = conn.execute('SELECT * FROM users WHERE group_id = ? ORDER BY name ASC', (selected_group_id,)).fetchall()
        
        # Get the group's profit directly from the group table
        group_data = conn.execute('SELECT group_profit FROM groups WHERE id = ?', (selected_group_id,)).fetchone()
        group_current_profit = group_data['group_profit'] if group_data else 0.0

        for user in users:
            transactions = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC",
                (user['id'],)
            ).fetchall()
            user_transactions[user['id']] = transactions

            loans = conn.execute(
                "SELECT * FROM loans WHERE user_id = ? ORDER BY issue_date DESC", # Show all loans, not just active
                (user['id'],)
            ).fetchall()
            user_loans[user['id']] = loans

    conn.close()

    # Calculate reports for the selected group
    reports = {}
    if selected_group_id:
        conn = get_db_connection()
        
        # Total contributions (paid)
        total_contributions = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'contribution' AND is_paid = 1",
            (selected_group_id,)
        ).fetchone()[0] or 0.0
        
        # Total loans disbursed (money flowing out)
        total_loans_disbursed = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'loan_disbursement'",
            (selected_group_id,)
        ).fetchone()[0] or 0.0
        
        # Total loan repayments (money flowing in)
        total_loan_repayments = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'loan_repayment'",
            (selected_group_id,)
        ).fetchone()[0] or 0.0

        # Total interest received (from interest_paid transactions)
        total_interest_received = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'interest_paid'",
            (selected_group_id,)
        ).fetchone()[0] or 0.0
        
        # Overall profit is now directly group_profit from the table
        overall_profit = group_current_profit

        current_year = datetime.now().strftime('%Y')
        current_month = datetime.now().strftime('%Y-%m')

        # Monthly/Yearly Profit (from interest_paid transactions)
        monthly_profit = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'interest_paid' AND date LIKE ?",
            (selected_group_id, f'{current_month}%')
        ).fetchone()[0] or 0.0
        yearly_profit = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'interest_paid' AND date LIKE ?",
            (selected_group_id, f'{current_year}%')
        ).fetchone()[0] or 0.0
        
        # Monthly/Yearly Investment (contributions)
        monthly_investment = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'contribution' AND is_paid = 1 AND date LIKE ?",
            (selected_group_id, f'{current_month}%')
        ).fetchone()[0] or 0.0
        yearly_investment = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'contribution' AND is_paid = 1 AND date LIKE ?",
            (selected_group_id, f'{current_year}%')
        ).fetchone()[0] or 0.0

        reports = {
            'total_contributions': total_contributions,
            'total_loans_disbursed': total_loans_disbursed,
            'total_loan_repayments': total_loan_repayments,
            'total_interest_received': total_interest_received,
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
                            group_current_profit=group_current_profit, # Pass group_current_profit
                            reports=reports,
                            admin_user_id=admin_user_id,
                            current_date=datetime.now().strftime('%Y-%m-%d'),
                            get_group=get_group,
                            calculate_interest_due=calculate_interest_due) # Pass the function to template

@app.route('/add_group', methods=['POST'])
def add_group():
    name = request.form['group_name']
    bank_account_details = request.form.get('bank_account_details', '')
    default_interest_rate = float(request.form.get('default_interest_rate', 12.0)) # New: Default Interest Rate
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO groups (name, bank_account_details, group_profit, default_interest_rate) VALUES (?, ?, ?, ?)',
                     (name, bank_account_details, 0.0, default_interest_rate))
        conn.commit()
        flash('Group added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Error: Group with this name already exists.', 'danger')
    except ValueError:
        flash('Error: Default interest rate must be a number.', 'danger')
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
    # This check needs to be more robust, e.g., actual user login and role checking
    # For now, it assumes admin_user_id 1 is the only admin
    if get_admin_user_id() is None or get_admin_user_id() != 1:
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
    date_str = datetime.now().strftime('%Y-%m-%d')
    is_cash_payment = request.form.get('is_cash_payment') == 'on'
    is_paid = 0 if is_cash_payment else 1

    user = get_user(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        # Transaction type changed to 'contribution' for consistency
        conn.execute(
            'INSERT INTO transactions (user_id, group_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, user['group_id'], 'contribution', amount, date_str, 'Monthly Contribution', is_cash_payment, is_paid)
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
    # This check needs to be more robust
    if get_admin_user_id() is None or get_admin_user_id() != 1:
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

# --- NEW: Manually Add Loan Route ---
@app.route('/add_loan_manual', methods=['POST'])
def add_loan_manual():
    try:
        user_id = int(request.form['user_id'])
        group_id = int(request.form['group_id'])
        amount = float(request.form['loan_amount'])
        issue_date_str = request.form['loan_issue_date']
        interest_rate = float(request.form['loan_interest_rate'])

        user = get_user(user_id)
        group = get_group(group_id)

        if not user or user['group_id'] != group_id:
            flash('Invalid User ID or User does not belong to specified Group.', 'danger')
            return redirect(url_for('index', group_id=group_id))
        if not group:
            flash('Invalid Group ID.', 'danger')
            return redirect(url_for('index'))
        if amount <= 0:
            flash('Loan amount must be positive.', 'danger')
            return redirect(url_for('index', group_id=group_id))
        if not (0 < interest_rate <= 100):
            flash('Interest rate must be between 0 and 100.', 'danger')
            return redirect(url_for('index', group_id=group_id))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into loans table
        cursor.execute(
            '''INSERT INTO loans (user_id, group_id, original_amount, outstanding_balance, current_interest_rate, issue_date, last_interest_calc_date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, group_id, amount, amount, interest_rate, issue_date_str, issue_date_str, 'active')
        )
        loan_id = cursor.lastrowid # Get the ID of the newly inserted loan

        # Record as a loan_disbursement transaction
        cursor.execute(
            'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, group_id, loan_id, 'loan_disbursement', amount, issue_date_str, f'Loan Disbursed to {user["name"]} (Loan ID: {loan_id})')
        )
        conn.commit()
        flash(f'Loan ID {loan_id} of ₹{amount:.2f} disbursed to {user["name"]} at {interest_rate}% annual interest.', 'success')
    except ValueError as ve:
        flash(f'Input error: {ve}', 'danger')
    except Exception as e:
        flash(f'Error adding loan: {e}', 'danger')
        conn.rollback() # Rollback if any error occurs
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

# --- NEW: Change Loan Interest Rate Route ---
@app.route('/change_loan_interest_rate', methods=['POST'])
def change_loan_interest_rate():
    try:
        loan_id = int(request.form['loan_id'])
        new_rate = float(request.form['new_interest_rate'])
        
        if not (0 < new_rate <= 100):
            flash('New interest rate must be between 0 and 100.', 'danger')
            return redirect(url_for('index'))

        conn = get_db_connection()
        loan = conn.execute('SELECT * FROM loans WHERE id = ?', (loan_id,)).fetchone()

        if not loan:
            flash('Loan not found.', 'danger')
            conn.close()
            return redirect(url_for('index'))

        old_rate = loan['current_interest_rate']
        conn.execute('UPDATE loans SET current_interest_rate = ? WHERE id = ?', (new_rate, loan_id))
        conn.commit()
        flash(f'Interest rate for Loan ID {loan_id} changed from {old_rate}% to {new_rate}%.', 'success')
    except ValueError as ve:
        flash(f'Input error: {ve}', 'danger')
    except Exception as e:
        flash(f'Error changing interest rate: {e}', 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=loan['group_id'] if loan else None))


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
    if repayment_amount <= 0:
        flash('Repayment amount must be positive.', 'danger')
        conn.close()
        return redirect(url_for('index', group_id=loan['group_id']))


    outstanding_balance_at_last_calc_date = loan['outstanding_balance']
    last_calc_date_str = loan['last_interest_calc_date']
    current_annual_rate = loan['current_interest_rate']
    
    # Calculate interest accrued since last_interest_calc_date up to today
    accrued_interest_since_last_calc = calculate_interest_due(
        outstanding_balance_at_last_calc_date, 
        current_annual_rate, 
        last_calc_date_str, 
        repayment_date
    )

    principal_repayment_amount = 0.0
    interest_paid_amount = 0.0

    if repayment_amount >= accrued_interest_since_last_calc:
        interest_paid_amount = accrued_interest_since_last_calc
        principal_repayment_amount = repayment_amount - interest_paid_amount
    else:
        # If repayment is less than accrued interest, the entire repayment goes to interest
        interest_paid_amount = repayment_amount
        principal_repayment_amount = 0.0

    new_outstanding_balance = loan['outstanding_balance'] - principal_repayment_amount

    # Ensure outstanding balance doesn't go negative
    if new_outstanding_balance < 0:
        actual_principal_repaid = loan['outstanding_balance'] # Repay only the remaining principal
        interest_paid_amount = max(0, repayment_amount - actual_principal_repaid) # Remaining is interest
        new_outstanding_balance = 0.0
    else:
        actual_principal_repaid = principal_repayment_amount
    
    try:
        # Update loan outstanding balance and last interest calculation date
        conn.execute(
            'UPDATE loans SET outstanding_balance = ?, last_interest_calc_date = ? WHERE id = ?',
            (new_outstanding_balance, repayment_date, loan_id)
        )
        
        # Record the full repayment as a loan_repayment transaction
        conn.execute(
            'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (loan['user_id'], loan['group_id'], loan_id, 'loan_repayment', repayment_amount, repayment_date,
             f'Loan Repayment for Loan ID {loan_id} (Principal: ₹{actual_principal_repaid:.2f}, Interest: ₹{interest_paid_amount:.2f})')
        )
        
        # Record the interest portion as an 'interest_paid' transaction and add to group profit
        if interest_paid_amount > 0:
            conn.execute(
                'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (loan['user_id'], loan['group_id'], loan_id, 'interest_paid', interest_paid_amount, repayment_date,
                 f'Interest paid by {get_user(loan["user_id"])["name"]} for Loan ID {loan_id}')
            )
            # Update group profit directly
            conn.execute(
                'UPDATE groups SET group_profit = group_profit + ? WHERE id = ?',
                (interest_paid_amount, loan['group_id'])
            )

        # Update loan status if fully paid off
        if new_outstanding_balance <= 0:
            conn.execute('UPDATE loans SET status = "paid_off" WHERE id = ?', (loan_id,))
            flash(f'Loan ID {loan_id} has been fully paid off!', 'info')
        
        conn.commit()
        flash(f'Loan repayment of ₹{repayment_amount:.2f} processed for Loan ID {loan_id}. '
              f'Principal reduced by ₹{actual_principal_repaid:.2f}, Interest portion: ₹{interest_paid_amount:.2f}. '
              f'Remaining balance: ₹{new_outstanding_balance:.2f}.', 'success')

    except Exception as e:
        flash(f'Error processing loan repayment: {e}', 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=loan['group_id']))


# --- MODIFIED: Bulk Upload Route for Transactions ---
@app.route('/bulk_upload_transactions', methods=['GET', 'POST']) # Renamed for clarity
def bulk_upload_transactions():
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
                for row_idx, row in enumerate(csv_reader):
                    row_num = row_idx + 1 # For clearer error messages
                    try:
                        user_name = row.get('user_name')
                        transaction_type = row.get('type', '').strip().lower() # Ensure consistent casing
                        amount = float(row.get('amount'))
                        date_str = row.get('date', datetime.now().strftime('%Y-%m-%d'))
                        is_cash = row.get('is_cash_payment', '0').lower() in ['1', 'true', 'yes']
                        is_paid_status = row.get('is_paid', '1').lower() in ['1', 'true', 'yes']
                        loan_id = row.get('loan_id')
                        new_loan_interest_rate = row.get('new_loan_interest_rate')

                        user = conn.execute(
                            'SELECT id, group_id FROM users WHERE name = ? AND group_id = ?',
                            (user_name, selected_group_id)
                        ).fetchone()
                        if not user:
                            messages.append(f"Row {row_num}: Skipping transaction for user '{user_name}': User not found in selected group.")
                            error_count += 1
                            continue
                        
                        user_id = user['id']
                        group_id = user['group_id']

                        if transaction_type == 'contribution':
                            conn.execute(
                                'INSERT INTO transactions (user_id, group_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                (user_id, group_id, 'contribution', amount, date_str, 'Bulk Uploaded Contribution', is_cash, is_paid_status)
                            )
                            messages.append(f"Row {row_num}: Processed contribution of ₹{amount} for {user_name}.")
                            processed_count += 1

                        elif transaction_type == 'loan_repayment':
                            if not loan_id:
                                messages.append(f"Row {row_num}: Skipping loan repayment for '{user_name}': 'loan_id' is missing.")
                                error_count += 1
                                continue
                            
                            loan = conn.execute('SELECT * FROM loans WHERE id = ? AND user_id = ? AND group_id = ?', (loan_id, user_id, group_id)).fetchone()
                            if not loan:
                                messages.append(f"Row {row_num}: Skipping loan repayment for '{user_name}': Loan ID {loan_id} not found for this user in this group.")
                                error_count += 1
                                continue
                            if loan['status'] == 'paid_off':
                                messages.append(f"Row {row_num}: Loan ID {loan_id} is already paid off.")
                                error_count += 1
                                continue

                            outstanding_balance_at_last_calc_date = loan['outstanding_balance']
                            last_calc_date_str = loan['last_interest_calc_date']
                            current_annual_rate = loan['current_interest_rate']
                            
                            accrued_interest_since_last_calc = calculate_interest_due(
                                outstanding_balance_at_last_calc_date, 
                                current_annual_rate, 
                                last_calc_date_str, 
                                date_str # Use the transaction date from CSV
                            )

                            principal_repayment_amount = 0.0
                            interest_paid_amount = 0.0

                            if amount >= accrued_interest_since_last_calc:
                                interest_paid_amount = accrued_interest_since_last_calc
                                principal_repayment_amount = amount - interest_paid_amount
                            else:
                                interest_paid_amount = amount
                                principal_repayment_amount = 0.0

                            new_outstanding_balance = loan['outstanding_balance'] - principal_repayment_amount

                            if new_outstanding_balance < 0:
                                actual_principal_repaid = loan['outstanding_balance']
                                interest_paid_amount = max(0, amount - actual_principal_repaid)
                                new_outstanding_balance = 0.0
                            else:
                                actual_principal_repaid = principal_repayment_amount

                            conn.execute(
                                'UPDATE loans SET outstanding_balance = ?, last_interest_calc_date = ? WHERE id = ?',
                                (new_outstanding_balance, date_str, loan_id) # Update last calc date to transaction date
                            )
                            conn.execute(
                                'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (user_id, group_id, loan_id, 'loan_repayment', amount, date_str,
                                 f'Bulk Uploaded Loan Repayment for Loan ID {loan_id} (Principal: ₹{actual_principal_repaid:.2f}, Interest: ₹{interest_paid_amount:.2f})')
                            )
                            
                            if interest_paid_amount > 0:
                                conn.execute(
                                    'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                    (user_id, group_id, loan_id, 'interest_paid', interest_paid_amount, date_str,
                                     f'Bulk Uploaded Interest paid by {user_name} for Loan ID {loan_id}')
                                )
                                # Update group profit directly
                                conn.execute(
                                    'UPDATE groups SET group_profit = group_profit + ? WHERE id = ?',
                                    (interest_paid_amount, group_id)
                                )

                            if new_outstanding_balance <= 0:
                                conn.execute('UPDATE loans SET status = "paid_off" WHERE id = ?', (loan_id,))
                                messages.append(f"Row {row_num}: Loan ID {loan_id} fully paid off.")
                            
                            messages.append(f"Row {row_num}: Processed loan repayment of ₹{amount} for {user_name} (Loan ID {loan_id}).")
                            processed_count += 1

                        elif transaction_type == 'interest_paid':
                            if not loan_id:
                                messages.append(f"Row {row_num}: Skipping interest paid for '{user_name}': 'loan_id' is missing.")
                                error_count += 1
                                continue
                            
                            loan = conn.execute('SELECT id, user_id, group_id FROM loans WHERE id = ? AND user_id = ? AND group_id = ?', (loan_id, user_id, group_id)).fetchone()
                            if not loan:
                                messages.append(f"Row {row_num}: Skipping interest paid for '{user_name}': Loan ID {loan_id} not found for this user in this group.")
                                error_count += 1
                                continue
                            
                            # Record as an 'interest_paid' transaction
                            conn.execute(
                                'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (user_id, group_id, loan_id, 'interest_paid', amount, date_str, f'Bulk Uploaded Interest paid for Loan ID {loan_id}')
                            )
                            # Update group profit directly
                            conn.execute(
                                'UPDATE groups SET group_profit = group_profit + ? WHERE id = ?',
                                (amount, group_id)
                            )
                            messages.append(f"Row {row_num}: Processed interest paid of ₹{amount} for {user_name} (Loan ID {loan_id}). Added to group profit.")
                            processed_count += 1

                        elif transaction_type == 'loan_disbursement':
                            # Loan ID should not be provided for new disbursements via CSV
                            if loan_id:
                                messages.append(f"Row {row_num}: Skipping loan disbursement for '{user_name}': 'loan_id' should not be provided for new loans.")
                                error_count += 1
                                continue

                            group = get_group(group_id) # Re-fetch group to get default rate
                            loan_interest_rate = float(new_loan_interest_rate) if new_loan_interest_rate else group['default_interest_rate']
                            
                            if not (0 < loan_interest_rate <= 100):
                                messages.append(f"Row {row_num}: Invalid interest rate '{loan_interest_rate}' for new loan for {user_name}. Must be between 0 and 100.")
                                error_count += 1
                                continue

                            cursor = conn.cursor()
                            cursor.execute(
                                '''INSERT INTO loans (user_id, group_id, original_amount, outstanding_balance, current_interest_rate, issue_date, last_interest_calc_date, status)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                (user_id, group_id, amount, amount, loan_interest_rate, date_str, date_str, 'active')
                            )
                            new_loan_id = cursor.lastrowid

                            conn.execute(
                                'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (user_id, group_id, new_loan_id, 'loan_disbursement', amount, date_str, f'Bulk Uploaded Loan Disbursed to {user_name} (Loan ID: {new_loan_id})')
                            )
                            messages.append(f"Row {row_num}: Disbursed new loan (ID: {new_loan_id}) of ₹{amount} to {user_name} at {loan_interest_rate}% annual interest.")
                            processed_count += 1

                        else:
                            messages.append(f"Row {row_num}: Skipping transaction for user '{user_name}': Unknown transaction type '{transaction_type}'.")
                            error_count += 1
                            continue
                    except ValueError as ve:
                        messages.append(f"Row {row_num}: Data conversion error for row for user '{row.get('user_name', 'N/A')}': {ve}")
                        error_count += 1
                    except Exception as row_e:
                        messages.append(f"Row {row_num}: Error processing row for user '{row.get('user_name', 'N/A')}': {row_e}")
                        error_count += 1
                
                conn.commit()
                flash(f'Bulk transaction upload complete. Processed {processed_count} rows, {error_count} errors. See details below.', 'info')
                for msg in messages:
                    flash(msg, 'info')
            except Exception as e:
                conn.rollback()
                flash(f'Error during bulk transaction upload: {e}', 'danger')
            finally:
                conn.close()
        else:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
    return render_template('bulk_upload_transactions.html', selected_group_id=selected_group_id)

@app.route('/download_sample_transaction_csv') # Renamed
def download_sample_transaction_csv():
    sample_csv_content = """user_name,type,amount,date,is_cash_payment,is_paid,loan_id,new_loan_interest_rate
Alice,contribution,1000,2024-05-20,0,1,,
Bob,loan_disbursement,5000,2024-05-22,,,24.0,
Bob,loan_repayment,1000,2024-06-20,,,"LOAN_ID_FOR_BOB",
Charlie,interest_paid,50,2024-06-20,,,"LOAN_ID_FOR_CHARLIE",
Alice,contribution,500,2024-06-25,1,0,,
"""
    return io.BytesIO(sample_csv_content.encode('utf-8')), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=sample_transactions_upload.csv'
    }

# --- NEW: Bulk User Upload Route ---
# (This route is fine as is, no changes needed based on new requirements)
@app.route('/bulk_upload_users', methods=['GET', 'POST'])
def bulk_upload_users():
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
                for row_idx, row in enumerate(csv_reader):
                    row_num = row_idx + 1
                    try:
                        user_name = row.get('user_name')
                        group_identifier = row.get('group_id') or row.get('group_name') # Can use ID or Name
                        is_admin = row.get('is_admin', '0').lower() in ['1', 'true', 'yes'] # Default to not admin
                        status = row.get('status', 'active') # Default to active

                        if not user_name or not group_identifier:
                            messages.append(f"Row {row_num}: Skipping row: 'user_name' or 'group_id'/'group_name' missing.")
                            error_count += 1
                            continue

                        target_group_id = None
                        if str(group_identifier).isdigit():
                            target_group_id = int(group_identifier)
                        else:
                            group_row = conn.execute('SELECT id FROM groups WHERE name = ?', (group_identifier,)).fetchone()
                            if group_row:
                                target_group_id = group_row['id']
                            else:
                                messages.append(f"Row {row_num}: Skipping user '{user_name}': Group '{group_identifier}' not found.")
                                error_count += 1
                                continue

                        existing_user = conn.execute(
                            'SELECT id FROM users WHERE name = ? AND group_id = ?',
                            (user_name, target_group_id)
                        ).fetchone()
                        if existing_user:
                            messages.append(f"Row {row_num}: Skipping user '{user_name}': User already exists in Group ID {target_group_id}.")
                            error_count += 1
                            continue

                        conn.execute(
                            'INSERT INTO users (name, group_id, is_admin, status) VALUES (?, ?, ?, ?)',
                            (user_name, target_group_id, is_admin, status)
                        )
                        messages.append(f"Row {row_num}: Added user '{user_name}' to Group ID {target_group_id}.")
                        processed_count += 1

                    except Exception as row_e:
                        messages.append(f"Row {row_num}: Error processing row for user '{row.get('user_name', 'N/A')}': {row_e}")
                        error_count += 1
                conn.commit()
                flash(f'Bulk user upload complete. Processed {processed_count} rows, {error_count} errors. See details below.', 'info')
                for msg in messages:
                    flash(msg, 'info')
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
"""
    return io.BytesIO(sample_csv_content.encode('utf-8')), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=sample_users_upload.csv'
    }

# --- Run the application ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)