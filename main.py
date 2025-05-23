from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
import sqlite3
from datetime import datetime, date, timedelta
import csv
import io
import os

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # Keep this for flash messages

# Database file name
DATABASE = 'bachatgat.db'

# --- Marathi Labels Dictionary ---
MARATHI_LABELS = {
    'app_name': 'बचत गट व्यवस्थापन',
    'select_group': 'गट निवडा',
    'add_group': 'नवीन गट जोडा',
    'group_name': 'गटाचे नाव',
    'bank_account_details': 'बँक खात्याचा तपशील',
    'default_interest_rate': 'कर्जावरील पूर्वनिर्धारित व्याज दर (%)',
    'add': 'जोडा',
    'group_financial_summary': 'गटाचा आर्थिक सारांश',
    'overall_summary': 'एकूण सारांश',
    'total_contributions': 'एकूण योगदान',
    'total_loans_disbursed': 'वितरित एकूण कर्ज',
    'total_loan_repayments': 'एकूण कर्ज परतफेड',
    'total_interest_received': 'मिळालेले एकूण व्याज',
    'overall_profit': 'एकूण नफा',
    'monthly_profit': 'मासिक नफा (या महिन्याचा)',
    'yearly_profit': 'वार्षिक नफा (या वर्षाचा)',
    'monthly_investment': 'मासिक गुंतवणूक (या महिन्याची)',
    'yearly_investment': 'वार्षिक गुंतवणूक (या वर्षाची)',
    'group_profit_label': 'गट नफा',
    'users_and_loans_summary': 'सदस्य आणि कर्जाचा सारांश',
    'user_name': 'सदस्य नाव',
    'loan_amount_outstanding': 'थकबाकी कर्ज रक्कम',
    'interest_paid': 'व्याज भरले',
    'remaining_loan_amount_with_interest': 'व्याजसह उर्वरित कर्ज रक्कम',
    'monthly_contribution_status': 'मासिक योगदान स्थिती',
    'active': 'सक्रिय',
    'inactive': 'निष्क्रिय',
    'add_new_user': 'नवीन सदस्य जोडा',
    'user_name_input': 'सदस्य नाव',
    'is_admin': 'प्रशासक आहे का?',
    'toggle_status': 'स्थिती बदला',
    'add_contribution': 'योगदान जोडा',
    'amount': 'रक्कम',
    'is_cash_payment': 'रोख भरणा आहे का?',
    'mark_paid': 'भरणा झाला म्हणून चिन्हांकित करा',
    'add_new_loan': 'नवीन कर्ज जोडा',
    'loan_amount': 'कर्ज रक्कम',
    'loan_issue_date': 'कर्ज दिल्याची तारीख',
    'loan_interest_rate': 'कर्जावरील व्याज दर (%)',
    'repay_loan': 'कर्ज परतफेड करा',
    'repayment_amount': 'परतफेड रक्कम',
    'change_interest_rate': 'व्याज दर बदला',
    'new_interest_rate': 'नवीन व्याज दर (%)',
    'loan_id': 'कर्ज आयडी',
    'status_active': 'सक्रिय',
    'status_paid_off': 'कर्ज फेडले',
    'status_pending_cash_payment': 'रोख भरणा बाकी',
    'bulk_upload_transactions': 'बल्क व्यवहार अपलोड करा',
    'bulk_upload_users': 'बल्क सदस्य अपलोड करा',
    'download_sample_transactions': 'व्यवहार नमुना CSV डाउनलोड करा',
    'download_sample_users': 'सदस्य नमुना CSV डाउनलोड करा',
    'choose_csv_file': 'CSV फाइल निवडा',
    'upload': 'अपलोड करा',
    'no_file_part': 'फाइलचा भाग नाही',
    'no_selected_file': 'कोणतीही फाइल निवडली नाही',
    'invalid_file_type': 'चुकीचा फाइल प्रकार. कृपया CSV फाइल अपलोड करा.',
    'upload_complete': 'बल्क अपलोड पूर्ण झाले. {processed_count} व्यवहार यशस्वीरित्या प्रक्रिया केले, {error_count} त्रुटी.',
    'upload_error': 'बल्क अपलोड दरम्यान त्रुटी: {error}',
    'user_not_found_in_group': "गट '{group_name}' मध्ये सदस्य '{user_name}' सापडला नाही.",
    'unknown_transaction_type': "अज्ञात व्यवहार प्रकार '{transaction_type}'",
    'data_conversion_error': "डेटा रूपांतरण त्रुटी: {error}",
    'error_processing_row': "पंक्ती प्रक्रिया करताना त्रुटी: {error}",
    'loan_id_missing': "कर्ज परतफेडीसाठी 'loan_id' आवश्यक आहे.",
    'loan_not_found': "कर्ज आयडी {loan_id} या सदस्यासाठी या गटात सापडला नाही.",
    'loan_already_paid_off': "हे कर्ज आधीच फेडले गेले आहे.",
    'loan_id_not_for_new_loan': "'loan_disbursement' साठी 'loan_id' देऊ नये.",
    'invalid_interest_rate': "नवीन कर्जासाठी व्याज दर '{rate}' अवैध आहे. तो 0 आणि 100 च्या दरम्यान असावा.",
    'group_added_success': 'गट यशस्वीरित्या जोडला!',
    'group_exists_error': 'त्रुटी: या नावाने गट आधीच अस्तित्वात आहे.',
    'interest_rate_number_error': 'त्रुटी: पूर्वनिर्धारित व्याज दर एक संख्या असणे आवश्यक आहे.',
    'error_adding_group': 'गट जोडताना त्रुटी: {error}',
    'user_added_success': 'सदस्य "{name}" यशस्वीरित्या जोडला!',
    'error_adding_user': 'सदस्य जोडताना त्रुटी: {error}',
    'unauthorized_access': 'अनधिकृत प्रवेश.',
    'user_status_changed': 'सदस्य स्थिती "{status}" मध्ये बदलली.',
    'user_not_found': 'सदस्य सापडला नाही.',
    'contribution_added_success': '₹{amount:.2f} चे योगदान {user_name} साठी जोडले. स्थिती: {status}.',
    'pending_cash_payment': 'रोख भरणा बाकी',
    'paid_upi_bank': 'भरले (UPI/बँक)',
    'error_adding_contribution': 'योगदान जोडताना त्रुटी: {error}',
    'cash_payment_marked_paid': 'रोख भरणा भरले म्हणून चिन्हांकित केला.',
    'payment_already_paid': 'भरणा आधीच भरले म्हणून चिन्हांकित केला आहे.',
    'transaction_not_found': 'व्यवहार सापडला नाही किंवा प्रलंबित रोख भरणा नाही.',
    'invalid_user_or_group': 'अवैध सदस्य आयडी किंवा सदस्य निर्दिष्ट गटाशी संबंधित नाही.',
    'invalid_group_id': 'अवैध गट आयडी.',
    'loan_amount_positive_error': 'कर्ज रक्कम सकारात्मक असणे आवश्यक आहे.',
    'interest_rate_range_error': 'व्याज दर 0 आणि 100 च्या दरम्यान असणे आवश्यक आहे.',
    'loan_disbursed_success': 'कर्ज आयडी {loan_id} ची ₹{amount:.2f} रक्कम {user_name} ला {rate}% वार्षिक व्याजाने वितरित केली.',
    'input_error': 'इनपुट त्रुटी: {error}',
    'error_adding_loan': 'कर्ज जोडताना त्रुटी: {error}',
    'loan_rate_changed_success': 'कर्ज आयडी {loan_id} साठी व्याज दर {old_rate}% वरून {new_rate}% मध्ये बदलला.',
    'error_changing_loan_rate': 'व्याज दर बदलताना त्रुटी: {error}',
    'repayment_amount_positive_error': 'परतफेड रक्कम सकारात्मक असणे आवश्यक आहे.',
    'loan_repayment_processed_success': 'कर्ज परतफेड ₹{repayment_amount:.2f} कर्ज आयडी {loan_id} साठी प्रक्रिया केली. '
                                         'मूळ रक्कम ₹{actual_principal_repaid:.2f} नी कमी झाली, व्याजाचा भाग: ₹{interest_paid_amount:.2f}. '
                                         'उर्वरित शिल्लक: ₹{new_outstanding_balance:.2f}.',
    'loan_fully_paid_off': 'कर्ज आयडी {loan_id} पूर्णपणे फेडले गेले आहे!',
    'error_repaying_loan': 'कर्ज परतफेड प्रक्रिया करताना त्रुटी: {error}',
    'user_exists_in_group': "पंक्ती {row_num}: सदस्य '{user_name}' गट आयडी {target_group_id} मध्ये आधीच अस्तित्वात आहे.",
    'user_added_to_group': "पंक्ती {row_num}: सदस्य '{user_name}' गट आयडी {target_group_id} मध्ये जोडला.",
    'group_not_found': "पंक्ती {row_num}: गट '{group_identifier}' सापडला नाही.",
    'missing_user_or_group': "पंक्ती {row_num}: पंक्ती वगळत आहे: 'user_name' किंवा 'group_id'/'group_name' गहाळ आहे.",
    'confirm_duplicates_title': 'दुबार व्यवहार आढळले',
    'confirm_duplicates_message': 'या फाइलमध्ये एकाच सदस्यासाठी एकापेक्षा जास्त व्यवहार (योगदान किंवा परतफेड) आहेत. तुम्हाला हे व्यवहार स्वीकारायचे आहेत का?',
    'duplicate_details': 'दुबार व्यवहाराचा तपशील:',
    'transaction_type': 'व्यवहाराचा प्रकार',
    'transaction_amount': 'रक्कम',
    'transaction_date': 'तारीख',
    'accept_all_duplicates': 'सर्व दुबार व्यवहार स्वीकारा',
    'reject_duplicates': 'दुबार व्यवहार नाकारा',
    'duplicate_transactions_rejected': 'दुबार व्यवहार नाकारले गेले. कोणतीही नवीन व्यवहार जोडली नाही.',
    'processing_duplicates_accepted': 'दुबार व्यवहार स्वीकारले गेले. प्रक्रिया सुरू आहे...',
    'processing_duplicates_rejected': 'दुबार व्यवहार नाकारले गेले.',
    'please_select_group': 'कृपया गट निवडा',
    'view_all_transactions': 'सर्व व्यवहार पहा',
    'back_to_summary': 'सारांशाकडे परत',
    'filter_transactions': 'व्यवहार फिल्टर करा',
    'from_date': 'पासूनची तारीख',
    'to_date': 'पर्यंतची तारीख',
    'filter': 'फिल्टर करा',
    'all_transactions_for': '{user_name} चे सर्व व्यवहार',
    'description': 'वर्णन',
    'download_transactions_csv': 'व्यवहार CSV डाउनलोड करा',
    'download_users_csv': 'सदस्य CSV डाउनलोड करा',
    'total_transactions': 'एकूण व्यवहार',
    'total_loans': 'एकूण कर्ज',
    'current_loan_status': 'चालू कर्ज स्थिती',
    'original_amount': 'मूळ रक्कम',
    'outstanding_balance': 'थकबाकी शिल्लक',
    'interest_rate': 'व्याज दर',
    'issue_date': 'दिलेली तारीख',
    'last_interest_calc_date': 'शेवटची व्याज गणना तारीख',
    'status': 'स्थिती',
    'view_details': 'तपशील पहा',
    'total_pending_cash_payments': 'प्रलंबित रोख भरणा',
}


def get_marathi_label(key):
    """Retrieves the Marathi label for a given key, with a fallback to English if not found."""
    return MARATHI_LABELS.get(key, key.replace('_', ' ').title())


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
    
    # REMOVED interest_distributions table as per new logic:
    # 'interest_paid' transactions directly update 'group_profit'.
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

def calculate_group_balance(group_id):
    conn = get_db_connection()
    group_profit_from_db = conn.execute(
        "SELECT group_profit FROM groups WHERE id = ?", (group_id,)
    ).fetchone()
    conn.close()
    return group_profit_from_db[0] if group_profit_from_db else 0.0

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

def calculate_contribution_status(user_id, group_id, target_date_str=None):
    """
    Checks if a user has made any contribution (type='contribution', is_paid=1)
    in the month of the target_date_str. If target_date_str is None, uses current month.
    Returns 'received' or 'not_received'.
    """
    conn = get_db_connection()
    if target_date_str:
        target_month = datetime.strptime(target_date_str, '%Y-%m-%d').strftime('%Y-%m')
    else:
        target_month = datetime.now().strftime('%Y-%m')

    count = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND group_id = ? AND type = 'contribution' AND is_paid = 1 AND date LIKE ?",
        (user_id, group_id, f'{target_month}%')
    ).fetchone()[0]
    conn.close()
    return 'received' if count > 0 else 'not_received'

# --- Flask Routes ---

@app.route('/')
def index():
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM groups').fetchall()
    selected_group_id = request.args.get('group_id', type=int)

    users_data_for_table = []
    group_current_profit = 0.0 
    admin_user_id = get_admin_user_id()
    reports = {}

    if selected_group_id:
        # Get the group's profit directly from the group table
        group_data = conn.execute('SELECT group_profit FROM groups WHERE id = ?', (selected_group_id,)).fetchone()
        group_current_profit = group_data['group_profit'] if group_data else 0.0

        users = conn.execute('SELECT * FROM users WHERE group_id = ? ORDER BY name ASC', (selected_group_id,)).fetchall()
        
        for user in users:
            user_id = user['id']
            user_name = user['name']
            
            # 1. Loan Amount Outstanding (sum of outstanding_balance for active loans)
            # 2. Total Interest Paid (by that user across all their loans)
            # 3. Remaining Loan Amount (Outstanding + Accrued Interest for active loans)
            # 4. Monthly Contribution Status
            
            active_loans = conn.execute(
                "SELECT * FROM loans WHERE user_id = ? AND status = 'active'",
                (user_id,)
            ).fetchall()

            total_loan_amount_outstanding = 0.0
            remaining_loan_amount_with_accrued_interest = 0.0
            
            for loan in active_loans:
                total_loan_amount_outstanding += loan['outstanding_balance']
                
                # Calculate accrued interest up to today
                accrued_interest = calculate_interest_due(
                    loan['outstanding_balance'],
                    loan['current_interest_rate'],
                    loan['last_interest_calc_date'],
                    datetime.now().strftime('%Y-%m-%d')
                )
                remaining_loan_amount_with_accrued_interest += loan['outstanding_balance'] + accrued_interest

            # Total interest paid by this user across ALL their loans (historical included)
            total_interest_paid = conn.execute(
                "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'interest_paid' AND is_paid = 1",
                (user_id,)
            ).fetchone()[0] or 0.0
            
            # Monthly Contribution Status for the current month
            monthly_contribution_status = calculate_contribution_status(user_id, selected_group_id)

            users_data_for_table.append({
                'user_id': user_id,
                'user_name': user_name,
                'user_status': user['status'],
                'is_admin': user['is_admin'],
                'total_loan_amount_outstanding': round(total_loan_amount_outstanding, 2),
                'total_interest_paid': round(total_interest_paid, 2),
                'remaining_loan_amount_with_accrued_interest': round(remaining_loan_amount_with_accrued_interest, 2),
                'monthly_contribution_status': monthly_contribution_status,
                'loans': active_loans # Pass active loans for detailed view if needed
            })
        
        # Calculate overall group reports
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
        
        # Total Pending Cash Payments
        total_pending_cash_payments = conn.execute(
            "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND is_cash_payment = 1 AND is_paid = 0",
            (selected_group_id,)
        ).fetchone()[0] or 0.0

        reports = {
            'total_contributions': round(total_contributions, 2),
            'total_loans_disbursed': round(total_loans_disbursed, 2),
            'total_loan_repayments': round(total_loan_repayments, 2),
            'total_interest_received': round(total_interest_received, 2),
            'overall_profit': round(overall_profit, 2),
            'monthly_profit': round(monthly_profit, 2),
            'yearly_profit': round(yearly_profit, 2),
            'monthly_investment': round(monthly_investment, 2),
            'yearly_investment': round(yearly_investment, 2),
            'total_pending_cash_payments': round(total_pending_cash_payments, 2),
        }
    conn.close()

    return render_template('index.html',
                            groups=groups,
                            users_data_for_table=users_data_for_table, # NEW: Pass consolidated user data
                            selected_group_id=selected_group_id,
                            group_current_profit=group_current_profit,
                            reports=reports,
                            admin_user_id=admin_user_id,
                            current_date=datetime.now().strftime('%Y-%m-%d'),
                            get_group=get_group,
                            calculate_interest_due=calculate_interest_due,
                            get_marathi_label=get_marathi_label) # Pass the Marathi label function

@app.route('/add_group', methods=['POST'])
def add_group():
    name = request.form['group_name']
    bank_account_details = request.form.get('bank_account_details', '')
    default_interest_rate = float(request.form.get('default_interest_rate', 12.0))
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO groups (name, bank_account_details, group_profit, default_interest_rate) VALUES (?, ?, ?, ?)',
                     (name, bank_account_details, 0.0, default_interest_rate))
        conn.commit()
        flash(get_marathi_label('group_added_success'), 'success')
    except sqlite3.IntegrityError:
        flash(get_marathi_label('group_exists_error'), 'danger')
    except ValueError:
        flash(get_marathi_label('interest_rate_number_error'), 'danger')
    except Exception as e:
        flash(get_marathi_label('error_adding_group').format(error=e), 'danger')
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form['user_name']
    group_id = request.form['group_id']
    is_admin = request.form.get('is_admin') == 'on'
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (name, group_id, is_admin, status) VALUES (?, ?, ?, ?)',
                     (name, group_id, is_admin, 'active'))
        conn.commit()
        flash(get_marathi_label('user_added_success').format(name=name), 'success')
    except Exception as e:
        flash(get_marathi_label('error_adding_user').format(error=e), 'danger')
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    if get_admin_user_id() is None or get_admin_user_id() != 1: # Basic admin check
        flash(get_marathi_label('unauthorized_access'), 'danger')
        user_info = get_user(user_id)
        return redirect(url_for('index', group_id=user_info['group_id'] if user_info else None))
        
    conn = get_db_connection()
    user = conn.execute('SELECT status, group_id FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_status = 'inactive' if user['status'] == 'active' else 'active'
        conn.execute('UPDATE users SET status = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        flash(get_marathi_label('user_status_changed').format(status=new_status), 'success')
    else:
        flash(get_marathi_label('user_not_found'), 'danger')
    conn.close()
    return redirect(url_for('index', group_id=user['group_id'] if user else None))

@app.route('/add_monthly_contribution/<int:user_id>', methods=['POST'])
def add_monthly_contribution(user_id):
    amount = float(request.form['amount'])
    date_str = datetime.now().strftime('%Y-%m-%d')
    is_cash_payment = request.form.get('is_cash_payment') == 'on'
    is_paid = 0 if is_cash_payment else 1

    user = get_user(user_id)
    if not user:
        flash(get_marathi_label('user_not_found'), 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO transactions (user_id, group_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, user['group_id'], 'contribution', amount, date_str, 'Monthly Contribution', is_cash_payment, is_paid)
        )
        conn.commit()
        status_msg = get_marathi_label('pending_cash_payment') if is_cash_payment else get_marathi_label('paid_upi_bank')
        flash(get_marathi_label('contribution_added_success').format(amount=amount, user_name=user["name"], status=status_msg), 'success')
    except Exception as e:
        flash(get_marathi_label('error_adding_contribution').format(error=e), 'danger')
    finally:
        conn.close()
    return redirect(url_for('index', group_id=user['group_id']))

@app.route('/mark_payment_paid/<int:transaction_id>', methods=['POST'])
def mark_payment_paid(transaction_id):
    if get_admin_user_id() is None or get_admin_user_id() != 1: # Basic admin check
        flash(get_marathi_label('unauthorized_access'), 'danger')
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    transaction = conn.execute('SELECT user_id, group_id, is_paid FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
    if transaction and transaction['is_paid'] == 0:
        conn.execute('UPDATE transactions SET is_paid = 1 WHERE id = ?', (transaction_id,))
        conn.commit()
        flash(get_marathi_label('cash_payment_marked_paid'), 'success')
    elif transaction and transaction['is_paid'] == 1:
        flash(get_marathi_label('payment_already_paid'), 'info')
    else:
        flash(get_marathi_label('transaction_not_found'), 'danger')
    conn.close()
    return redirect(url_for('index', group_id=transaction['group_id'] if transaction else None))

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
            flash(get_marathi_label('invalid_user_or_group'), 'danger')
            return redirect(url_for('index', group_id=group_id))
        if not group:
            flash(get_marathi_label('invalid_group_id'), 'danger')
            return redirect(url_for('index'))
        if amount <= 0:
            flash(get_marathi_label('loan_amount_positive_error'), 'danger')
            return redirect(url_for('index', group_id=group_id))
        if not (0 < interest_rate <= 100):
            flash(get_marathi_label('interest_rate_range_error'), 'danger')
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
        conn.execute(
            'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, group_id, loan_id, 'loan_disbursement', amount, issue_date_str, f'Loan Disbursed to {user["name"]} (Loan ID: {loan_id})')
        )
        conn.commit()
        flash(get_marathi_label('loan_disbursed_success').format(loan_id=loan_id, amount=amount, user_name=user["name"], rate=interest_rate), 'success')
    except ValueError as ve:
        flash(get_marathi_label('input_error').format(error=ve), 'danger')
    except Exception as e:
        flash(get_marathi_label('error_adding_loan').format(error=e), 'danger')
        conn.rollback() # Rollback if any error occurs
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/change_loan_interest_rate', methods=['POST'])
def change_loan_interest_rate():
    try:
        loan_id = int(request.form['loan_id'])
        new_rate = float(request.form['new_interest_rate'])
        
        if not (0 < new_rate <= 100):
            flash(get_marathi_label('interest_rate_range_error'), 'danger')
            return redirect(url_for('index'))

        conn = get_db_connection()
        loan = conn.execute('SELECT * FROM loans WHERE id = ?', (loan_id,)).fetchone()

        if not loan:
            flash(get_marathi_label('loan_not_found').format(loan_id=loan_id), 'danger')
            conn.close()
            return redirect(url_for('index'))

        old_rate = loan['current_interest_rate']
        conn.execute('UPDATE loans SET current_interest_rate = ? WHERE id = ?', (new_rate, loan_id))
        conn.commit()
        flash(get_marathi_label('loan_rate_changed_success').format(loan_id=loan_id, old_rate=old_rate, new_rate=new_rate), 'success')
    except ValueError as ve:
        flash(get_marathi_label('input_error').format(error=ve), 'danger')
    except Exception as e:
        flash(get_marathi_label('error_changing_loan_rate').format(error=e), 'danger')
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
        flash(get_marathi_label('loan_not_found').format(loan_id=loan_id), 'danger')
        conn.close()
        return redirect(url_for('index'))
    if loan['status'] == 'paid_off':
        flash(get_marathi_label('loan_already_paid_off'), 'info')
        conn.close()
        return redirect(url_for('index', group_id=loan['group_id']))
    if repayment_amount <= 0:
        flash(get_marathi_label('repayment_amount_positive_error'), 'danger')
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
            flash(get_marathi_label('loan_fully_paid_off').format(loan_id=loan_id), 'info')
        
        conn.commit()
        flash(get_marathi_label('loan_repayment_processed_success').format(
            repayment_amount=repayment_amount, loan_id=loan_id, 
            actual_principal_repaid=actual_principal_repaid, 
            interest_paid_amount=interest_paid_amount, 
            new_outstanding_balance=new_outstanding_balance
        ), 'success')

    except Exception as e:
        flash(get_marathi_label('error_repaying_loan').format(error=e), 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=loan['group_id']))


@app.route('/bulk_upload_transactions', methods=['GET', 'POST'])
def bulk_upload_transactions():
    selected_group_id = request.args.get('group_id', type=int)
    if not selected_group_id:
        flash(get_marathi_label('please_select_group'), 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash(get_marathi_label('no_file_part'), 'danger')
            return redirect(request.url)
        file = request.files['csv_file']
        if file.filename == '':
            flash(get_marathi_label('no_selected_file'), 'danger')
            return redirect(request.url)
        if not file.filename.endswith('.csv'):
            flash(get_marathi_label('invalid_file_type'), 'danger')
            return redirect(request.url)
        
        stream = io.TextIOWrapper(file, encoding='utf-8')
        csv_reader = csv.DictReader(stream)
        
        # List to store parsed rows for potential processing
        transactions_to_process = []
        # For duplicate detection: (user_id, type, date) -> count
        transaction_occurrence = {} 
        # For displaying duplicates to user: (user_id, type, date) -> [list of original rows]
        duplicates_found = {} 

        conn = get_db_connection()
        for row_idx, row in enumerate(csv_reader):
            row_num = row_idx + 1 # For clearer error messages
            user_name = row.get('user_name', '').strip()
            transaction_type = row.get('type', '').strip().lower()
            amount_str = row.get('amount', '').strip()
            date_str = row.get('date', datetime.now().strftime('%Y-%m-%d')).strip()
            is_cash = row.get('is_cash_payment', '0').strip().lower() in ['1', 'true', 'yes']
            is_paid_status = row.get('is_paid', '1').strip().lower() in ['1', 'true', 'yes']
            loan_id_str = row.get('loan_id', '').strip()
            new_loan_interest_rate_str = row.get('new_loan_interest_rate', '').strip()

            try:
                user = conn.execute(
                    'SELECT id, group_id FROM users WHERE name = ? AND group_id = ?',
                    (user_name, selected_group_id)
                ).fetchone()
                if not user:
                    flash(f"{get_marathi_label('error_processing_row').format(row_num=row_num)}: {get_marathi_label('user_not_found_in_group').format(user_name=user_name, group_name=get_group(selected_group_id)['name'])}", 'warning')
                    continue # Skip to next row
                
                user_id = user['id']
                group_id = user['group_id']
                amount = float(amount_str)
                loan_id = int(loan_id_str) if loan_id_str else None
                new_loan_interest_rate = float(new_loan_interest_rate_str) if new_loan_interest_rate_str else None

                # Basic validation for transaction type
                valid_types = ['contribution', 'loan_disbursement', 'loan_repayment', 'interest_paid']
                if transaction_type not in valid_types:
                    flash(f"{get_marathi_label('error_processing_row').format(row_num=row_num)}: {get_marathi_label('unknown_transaction_type').format(transaction_type=transaction_type)}", 'warning')
                    continue

                # Prepare row data, including original_row for confirmation
                row_data = {
                    'row_num': row_num,
                    'user_id': user_id,
                    'user_name': user_name,
                    'group_id': group_id,
                    'type': transaction_type,
                    'amount': amount,
                    'date': date_str,
                    'is_cash_payment': is_cash,
                    'is_paid': is_paid_status,
                    'loan_id': loan_id,
                    'new_loan_interest_rate': new_loan_interest_rate,
                    'original_row_data': dict(row) # Keep original CSV row for display
                }
                transactions_to_process.append(row_data)

                # Duplicate detection for (user, type, date) within THIS upload file
                # A user making multiple contributions on the same day, or multiple repayments
                # It's important to distinguish between separate repayments for different loans vs same loan.
                # For simplicity in pop-up, I'll flag (user_id, type, date, loan_id if available)
                
                # For loan repayments/interest paid, consider loan_id as part of uniqueness
                unique_key_components = [user_id, transaction_type, date_str]
                if transaction_type in ['loan_repayment', 'interest_paid'] and loan_id:
                    unique_key_components.append(loan_id)
                elif transaction_type == 'loan_disbursement': # A user can only get one loan per entry in CSV
                     unique_key_components.append(f"new_loan_{datetime.now().microsecond}") # Pseudo-unique for new loan
                
                unique_key = tuple(unique_key_components)

                if unique_key in transaction_occurrence:
                    if unique_key not in duplicates_found:
                        duplicates_found[unique_key] = [transaction_occurrence[unique_key]] # Add first occurrence
                    duplicates_found[unique_key].append(row_data)
                else:
                    transaction_occurrence[unique_key] = row_data # Store the first occurrence
            
            except ValueError as ve:
                flash(f"{get_marathi_label('error_processing_row').format(row_num=row_num)}: {get_marathi_label('data_conversion_error').format(error=ve)} - Data: {dict(row)}", 'danger')
                continue
            except Exception as e:
                flash(f"{get_marathi_label('error_processing_row').format(row_num=row_num)}: {get_marathi_label('error_processing_row').format(error=e)} - Data: {dict(row)}", 'danger')
                continue
        
        conn.close() # Close connection used for preliminary checks

        if duplicates_found:
            # Store duplicates and all transactions in session for confirmation step
            session['transactions_to_process'] = transactions_to_process
            session['duplicates_found'] = list(duplicates_found.values()) # Convert dict_values to list
            session['selected_group_id_for_upload'] = selected_group_id
            return redirect(url_for('confirm_duplicate_transactions'))
        else:
            # No duplicates, proceed directly to processing all transactions
            return process_bulk_transactions(transactions_to_process, selected_group_id, confirm_accept=True)
            
    return render_template('bulk_upload_transactions.html', 
                           selected_group_id=selected_group_id,
                           get_marathi_label=get_marathi_label)

@app.route('/confirm_duplicate_transactions', methods=['GET', 'POST'])
def confirm_duplicate_transactions():
    if 'duplicates_found' not in session or 'transactions_to_process' not in session or 'selected_group_id_for_upload' not in session:
        flash(get_marathi_label('unauthorized_access'), 'danger')
        return redirect(url_for('index'))

    duplicates = session['duplicates_found']
    selected_group_id = session['selected_group_id_for_upload']
    
    # Get group name for display
    group = get_group(selected_group_id)
    group_name = group['name'] if group else 'Unknown Group'

    if request.method == 'POST':
        action = request.form.get('action')
        transactions_to_process = session.pop('transactions_to_process', [])
        selected_group_id = session.pop('selected_group_id_for_upload', None)
        session.pop('duplicates_found', None) # Clear duplicates from session

        if action == 'accept':
            flash(get_marathi_label('processing_duplicates_accepted'), 'info')
            return process_bulk_transactions(transactions_to_process, selected_group_id, confirm_accept=True)
        elif action == 'reject':
            flash(get_marathi_label('duplicate_transactions_rejected'), 'warning')
            return redirect(url_for('index', group_id=selected_group_id))
        
    return render_template('confirm_duplicate_transactions.html', 
                           duplicates=duplicates,
                           selected_group_id=selected_group_id,
                           group_name=group_name,
                           get_marathi_label=get_marathi_label)

def process_bulk_transactions(transactions_data, selected_group_id, confirm_accept=False):
    """
    Internal function to process bulk transactions after (optional) duplicate confirmation.
    """
    processed_count = 0
    error_count = 0
    messages = []
    conn = get_db_connection()
    try:
        for row_data in transactions_data:
            user_id = row_data['user_id']
            user_name = row_data['user_name']
            group_id = row_data['group_id']
            transaction_type = row_data['type']
            amount = row_data['amount']
            date_str = row_data['date']
            is_cash = row_data['is_cash_payment']
            is_paid_status = row_data['is_paid']
            loan_id = row_data['loan_id']
            new_loan_interest_rate = row_data['new_loan_interest_rate']
            row_num = row_data['row_num']

            try:
                if transaction_type == 'contribution':
                    conn.execute(
                        'INSERT INTO transactions (user_id, group_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (user_id, group_id, 'contribution', amount, date_str, 'Bulk Uploaded Contribution', is_cash, is_paid_status)
                    )
                    messages.append(f"पंक्ती {row_num}: ₹{amount} चे योगदान {user_name} साठी प्रक्रिया केले.")
                    processed_count += 1

                elif transaction_type == 'loan_repayment':
                    if not loan_id:
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('loan_id_missing').format(user_name=user_name)}")
                        error_count += 1
                        continue
                    
                    loan = conn.execute('SELECT * FROM loans WHERE id = ? AND user_id = ? AND group_id = ?', (loan_id, user_id, group_id)).fetchone()
                    if not loan:
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('loan_not_found').format(loan_id=loan_id, user_name=user_name)}")
                        error_count += 1
                        continue
                    if loan['status'] == 'paid_off':
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('loan_already_paid_off').format(loan_id=loan_id)}")
                        error_count += 1
                        continue

                    outstanding_balance_at_last_calc_date = loan['outstanding_balance']
                    last_calc_date_str = loan['last_interest_calc_date']
                    current_annual_rate = loan['current_interest_rate']
                    
                    accrued_interest_since_last_calc = calculate_interest_due(
                        outstanding_balance_at_last_calc_date, 
                        current_annual_rate, 
                        last_calc_date_str, 
                        date_str
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
                        (new_outstanding_balance, date_str, loan_id)
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
                        conn.execute(
                            'UPDATE groups SET group_profit = group_profit + ? WHERE id = ?',
                            (interest_paid_amount, group_id)
                        )

                    if new_outstanding_balance <= 0:
                        conn.execute('UPDATE loans SET status = "paid_off" WHERE id = ?', (loan_id,))
                        messages.append(f"पंक्ती {row_num}: कर्ज आयडी {loan_id} पूर्णपणे फेडले गेले.")
                    
                    messages.append(f"पंक्ती {row_num}: कर्ज परतफेड ₹{amount} {user_name} साठी (कर्ज आयडी {loan_id}) प्रक्रिया केली.")
                    processed_count += 1

                elif transaction_type == 'interest_paid':
                    if not loan_id:
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('loan_id_missing').format(user_name=user_name)}")
                        error_count += 1
                        continue
                    
                    loan = conn.execute('SELECT id, user_id, group_id FROM loans WHERE id = ? AND user_id = ? AND group_id = ?', (loan_id, user_id, group_id)).fetchone()
                    if not loan:
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('loan_not_found').format(loan_id=loan_id, user_name=user_name)}")
                        error_count += 1
                        continue
                    
                    conn.execute(
                        'INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (user_id, group_id, loan_id, 'interest_paid', amount, date_str, f'Bulk Uploaded Interest paid for Loan ID {loan_id}')
                    )
                    conn.execute(
                        'UPDATE groups SET group_profit = group_profit + ? WHERE id = ?',
                        (amount, group_id)
                    )
                    messages.append(f"पंक्ती {row_num}: ₹{amount} व्याज {user_name} साठी (कर्ज आयडी {loan_id}) प्रक्रिया केले. गट नफ्यात जोडले.")
                    processed_count += 1

                elif transaction_type == 'loan_disbursement':
                    if loan_id: # For new loans, loan_id should not be provided in CSV
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('loan_id_not_for_new_loan').format(user_name=user_name)}")
                        error_count += 1
                        continue

                    group = get_group(group_id)
                    loan_interest_rate = new_loan_interest_rate if new_loan_interest_rate is not None else group['default_interest_rate']
                    
                    if not (0 < loan_interest_rate <= 100):
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('invalid_interest_rate').format(rate=loan_interest_rate, user_name=user_name)}")
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
                    messages.append(f"पंक्ती {row_num}: {new_loan_id} कर्ज (ID: {new_loan_id}) ₹{amount} चे {user_name} ला {loan_interest_rate}% वार्षिक व्याजाने वितरित केले.")
                    processed_count += 1

            except ValueError as ve:
                messages.append(f"पंक्ती {row_num}: {get_marathi_label('data_conversion_error').format(error=ve)}")
                error_count += 1
            except Exception as row_e:
                messages.append(f"पंक्ती {row_num}: {get_marathi_label('error_processing_row').format(error=row_e)}")
                error_count += 1
        
        conn.commit()
        flash(get_marathi_label('upload_complete').format(processed_count=processed_count, error_count=error_count), 'success')
        for msg in messages:
            flash(msg, 'info')
    except Exception as e:
        conn.rollback()
        flash(get_marathi_label('upload_error').format(error=e), 'danger')
    finally:
        conn.close()
    return redirect(url_for('index', group_id=selected_group_id))


@app.route('/bulk_upload_users', methods=['GET', 'POST'])
def bulk_upload_users():
    selected_group_id = request.args.get('group_id', type=int)
    if not selected_group_id:
        flash(get_marathi_label('please_select_group'), 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash(get_marathi_label('no_file_part'), 'danger')
            return redirect(request.url)
        file = request.files['csv_file']
        if file.filename == '':
            flash(get_marathi_label('no_selected_file'), 'danger')
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
                        user_name = row.get('user_name', '').strip()
                        group_identifier = row.get('group_id') or row.get('group_name', '').strip()
                        is_admin = row.get('is_admin', '0').lower() in ['1', 'true', 'yes']
                        status = row.get('status', 'active').strip()

                        if not user_name or not group_identifier:
                            messages.append(get_marathi_label('missing_user_or_group').format(row_num=row_num))
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
                                messages.append(get_marathi_label('group_not_found').format(row_num=row_num, user_name=user_name, group_identifier=group_identifier))
                                error_count += 1
                                continue

                        # Ensure the uploaded user belongs to the currently selected group
                        if target_group_id != selected_group_id:
                            messages.append(f"पंक्ती {row_num}: सदस्य '{user_name}' निवडलेल्या गटाशी संबंधित नाही. (निर्दिष्ट गट ID: {target_group_id}, निवडलेला गट ID: {selected_group_id})")
                            error_count += 1
                            continue


                        existing_user = conn.execute(
                            'SELECT id FROM users WHERE name = ? AND group_id = ?',
                            (user_name, target_group_id)
                        ).fetchone()
                        if existing_user:
                            messages.append(get_marathi_label('user_exists_in_group').format(row_num=row_num, user_name=user_name, target_group_id=target_group_id))
                            error_count += 1
                            continue

                        conn.execute(
                            'INSERT INTO users (name, group_id, is_admin, status) VALUES (?, ?, ?, ?)',
                            (user_name, target_group_id, is_admin, status)
                        )
                        messages.append(get_marathi_label('user_added_to_group').format(row_num=row_num, user_name=user_name, target_group_id=target_group_id))
                        processed_count += 1

                    except Exception as row_e:
                        messages.append(f"पंक्ती {row_num}: {get_marathi_label('error_processing_row').format(error=row_e, user_name=row.get('user_name', 'N/A'))}")
                        error_count += 1
                conn.commit()
                flash(get_marathi_label('upload_complete').format(processed_count=processed_count, error_count=error_count), 'info')
                for msg in messages:
                    flash(msg, 'info')
            except Exception as e:
                conn.rollback()
                flash(get_marathi_label('upload_error').format(error=e), 'danger')
            finally:
                conn.close()
        else:
            flash(get_marathi_label('invalid_file_type'), 'danger')
    return render_template('bulk_upload_users.html', 
                           selected_group_id=selected_group_id,
                           get_marathi_label=get_marathi_label)

@app.route('/download_sample_transaction_csv')
def download_sample_transaction_csv():
    # Updated sample CSV with clearer headers and examples
    sample_csv_content = """user_name,type,amount,date,is_cash_payment,is_paid,loan_id,new_loan_interest_rate
Alice,contribution,1000,2024-05-20,0,1,,
Bob,loan_disbursement,5000,2024-05-22,,,24.0,
Bob,loan_repayment,1000,2024-06-20,0,1,1,
Charlie,interest_paid,50,2024-06-20,0,1,2,
Alice,contribution,500,2024-06-25,1,0,,
""" # Example loan_id 1 for Bob, 2 for Charlie
    return send_from_directory(
        app.root_path, # Or a specific 'static' folder if you prefer
        'sample_transactions_upload.csv',
        mimetype='text/csv',
        as_attachment=True,
        download_name='sample_transactions_upload.csv',
        data=io.BytesIO(sample_csv_content.encode('utf-8'))
    )

@app.route('/download_sample_users_csv')
def download_sample_users_csv():
    sample_csv_content = """user_name,group_id,is_admin,status
Alice,1,0,active
Bob,1,1,active
Charlie,2,0,active
"""
    return send_from_directory(
        app.root_path, # Or a specific 'static' folder if you prefer
        'sample_users_upload.csv',
        mimetype='text/csv',
        as_attachment=True,
        download_name='sample_users_upload.csv',
        data=io.BytesIO(sample_csv_content.encode('utf-8'))
    )

# --- Run the application ---
if __name__ == '__main__':
    # Create the sample CSV files in the application's root directory if they don't exist
    # This is for the `send_from_directory` to work correctly when deploying
    # For `app.run(debug=True)`, it often serves from memory or current directory,
    # but for production, having actual files is better.
    with open('sample_transactions_upload.csv', 'w', encoding='utf-8') as f:
        f.write("""user_name,type,amount,date,is_cash_payment,is_paid,loan_id,new_loan_interest_rate
Alice,contribution,1000,2024-05-20,0,1,,
Bob,loan_disbursement,5000,2024-05-22,,,24.0,
Bob,loan_repayment,1000,2024-06-20,0,1,1,
Charlie,interest_paid,50,2024-06-20,0,1,2,
Alice,contribution,500,2024-06-25,1,0,,
""")
    with open('sample_users_upload.csv', 'w', encoding='utf-8') as f:
        f.write("""user_name,group_id,is_admin,status
Alice,1,0,active
Bob,1,1,active
Charlie,2,0,active
""")

    init_db()
    app.run(debug=True)