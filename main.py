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
    'app_name': 'अष्टशील महिला बचत गट',
    'select_group': 'गट निवडा',
    'add_group': 'नवीन गट जोडा',
    'group_name': 'गटाचे नाव',
    'bank_account_details': 'बँक खात्याचा तपशील',
    'default_interest_rate': 'कर्जावरील पूर्वनिर्धारित व्याज दर (%)',
    'add': 'जोडा',
    'group_financial_summary': 'गटाचा आर्थिक सारांश',
    'overall_summary': 'एकूण नफा',
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
    'total_contribution_by_user': 'एकूण योगदान',
    'pending_contribution_by_user': 'प्रलंबित योगदान',
    'total_loans_disbursed_to_user': 'एकूण वितरित कर्ज',
    'pending_loan_amount_with_interest': 'प्रलंबित कर्ज (व्याजासह)',
    'users_with_active_loans': 'सक्रिय कर्ज असलेले सदस्य',
    'users_without_active_loans': 'सक्रिय कर्ज नसलेले सदस्य',
    'total_amount_paid_by_user_till_date': 'सदस्याने आजपर्यंत भरलेली एकूण रक्कम',
    'bank_interest_rate': 'बँक व्याज दर',
    'saving_account_balance': 'बचत खाते शिल्लक',
    'edit_bank_interest_rate': 'बँक व्याज दर संपादित करा',
    'update': 'अद्यतनित करा',
    'bank_interest_rate_updated_success': 'बँक व्याज दर यशस्वीरित्या अद्यतनित केला.',
    'error_updating_bank_interest_rate': 'बँक व्याज दर अद्यतनित करताना त्रुटी: {error}',
    'all_users_summary': 'सर्व सदस्यांचा सारांश',
    'view_all_groups_report': 'सर्व गटांचा अहवाल पहा',
    'all_groups_report': 'सर्व गटांचा अहवाल',
    'group_name_report': 'गटाचे नाव',
    'pending_contributions_report': 'प्रलंबित योगदान',
    'total_outstanding_loans_report': 'एकूण थकबाकी कर्ज',
    'total_paid_contributions_report': 'एकूण भरलेले योगदान',
    'monthly_repayment_status_report': 'मासिक परतफेड स्थिती',
    'loans_due_this_month': 'या महिन्यात देय कर्जे',
    'loans_repaid_this_month': 'या महिन्यात परतफेड केलेली कर्जे',
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
    
    # Updated groups table to include group_profit, default_interest_rate, and bank_interest_rate
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            bank_account_details TEXT,
            group_profit REAL DEFAULT 0.0,
            default_interest_rate REAL DEFAULT 12.0,
            bank_interest_rate REAL DEFAULT 3.0 -- New field
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
    
    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE groups ADD COLUMN bank_interest_rate REAL DEFAULT 3.0")
    except sqlite3.OperationalError:
        # Column already exists
        pass

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

# New helper function to calculate all financial summaries for a given group
def get_group_financial_summary_reports(group_id, conn):
    """
    Calculates and returns a dictionary of financial summaries for a given group.
    Reuses logic from the index route's report calculation.
    """
    group_data = conn.execute('SELECT group_profit, bank_interest_rate FROM groups WHERE id = ?', (group_id,)).fetchone()
    group_current_profit = group_data['group_profit'] if group_data else 0.0
    group_bank_interest_rate = group_data['bank_interest_rate'] if group_data and group_data['bank_interest_rate'] is not None else 3.0

    # Calculate overall group reports
    # Total contributions (paid)
    total_contributions = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'contribution' AND is_paid = 1",
        (group_id,)
    ).fetchone()[0] or 0.0
    
    # Total loans disbursed (money flowing out)
    total_loans_disbursed2 = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'loan_disbursement'",
        (group_id,)
    ).fetchone()[0] or 0.0
    
    # Total loan repayments (money flowing in)
    total_loan_repayments = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'loan_repayment'",
        (group_id,)
    ).fetchone()[0] or 0.0
    total_loans_disbursed = total_loans_disbursed2 - total_loan_repayments
    # Total interest received (from interest_paid transactions)
    total_interest_received = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'interest_paid'",
        (group_id,)
    ).fetchone()[0] or 0.0
    
    overall_profit = group_current_profit

    current_year = datetime.now().strftime('%Y')
    current_month = datetime.now().strftime('%Y-%m')

    # Monthly/Yearly Profit (from interest_paid transactions)
    monthly_profit = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'interest_paid' AND date LIKE ?",
        (group_id, f'{current_month}%')
    ).fetchone()[0] or 0.0
    yearly_profit = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'interest_paid' AND date LIKE ?",
        (group_id, f'{current_year}%')
    ).fetchone()[0] or 0.0
    
    # Monthly/Yearly Investment (contributions)
    monthly_investment = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'contribution' AND is_paid = 1 AND date LIKE ?",
        (group_id, f'{current_month}%')
    ).fetchone()[0] or 0.0
    yearly_investment = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND type = 'contribution' AND is_paid = 1 AND date LIKE ?",
        (group_id, f'{current_year}%')
    ).fetchone()[0] or 0.0
    
    # Total Pending Cash Payments
    total_pending_cash_payments = conn.execute(
        "SELECT SUM(amount) FROM transactions WHERE group_id = ? AND is_cash_payment = 1 AND is_paid = 0",
        (group_id,)
    ).fetchone()[0] or 0.0

    # Calculate Saving Account Balance
    # This is total money received by the group minus total money disbursed by the group
    saving_account_balance = (total_contributions + total_loan_repayments + total_interest_received) - \
                             (total_loans_disbursed + total_pending_cash_payments) # Deduct pending cash payments as they are not 'in hand' yet

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
        'saving_account_balance': round(saving_account_balance, 2),
        'bank_interest_rate': group_bank_interest_rate
    }
    return reports

# --- Flask Routes ---

@app.route('/')
def index():
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM groups').fetchall()
    selected_group_id = request.args.get('group_id', type=int)

    all_users_data = [] # Combined list for all users
    group_current_profit = 0.0 
    group_bank_interest_rate = 3.0 # Default value
    admin_user_id = get_admin_user_id()
    reports = {}
    saving_account_balance = 0.0
    users_in_selected_group = [] # For the "Add New Loan" modal dropdown

    if selected_group_id:
        group_data = conn.execute('SELECT group_profit, bank_interest_rate FROM groups WHERE id = ?', (selected_group_id,)).fetchone()
        group_current_profit = group_data['group_profit'] if group_data else 0.0
        group_bank_interest_rate = group_data['bank_interest_rate'] if group_data and group_data['bank_interest_rate'] is not None else 3.0

        users = conn.execute('SELECT * FROM users WHERE group_id = ? ORDER BY name ASC', (selected_group_id,)).fetchall()
        users_in_selected_group = users # Populate for the modal

        for user in users:
            user_id = user['id']
            user_name = user['name']
            
            # Total Contribution by User (paid contributions)
            total_contributions_by_user = conn.execute(
                "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'contribution' AND is_paid = 1",
                (user_id,)
            ).fetchone()[0] or 0.0

            # Pending Contribution by User (cash payments not yet marked as paid)
            pending_contributions_by_user = conn.execute(
                "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'contribution' AND is_cash_payment = 1 AND is_paid = 0",
                (user_id,)
            ).fetchone()[0] or 0.0

            # Total Loans Disbursed to User (original amount of all loans for the user)
            total_loans_disbursed_to_user = conn.execute(
                "SELECT SUM(original_amount) FROM loans WHERE user_id = ?",
                (user_id,)
            ).fetchone()[0] or 0.0
            
            # Total Loan Repayments by User (sum of all loan_repayment transactions by the user)
            total_loan_repayments_by_user = conn.execute(
                "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'loan_repayment' AND is_paid = 1",
                (user_id,)
            ).fetchone()[0] or 0.0

            # Remaining Loan Amount (Outstanding + Accrued Interest for active loans)
            active_loans_raw = conn.execute(
                "SELECT * FROM loans WHERE user_id = ? AND status = 'active'",
                (user_id,)
            ).fetchall()

            # Convert sqlite3.Row objects to dictionaries for JSON serialization
            active_loans = []
            for loan_row in active_loans_raw:
                active_loans.append(dict(loan_row))


            remaining_loan_amount_with_accrued_interest = 0.0
            
            for loan in active_loans:
                accrued_interest = calculate_interest_due(
                    loan['outstanding_balance'],
                    loan['current_interest_rate'],
                    loan['last_interest_calc_date'],
                    datetime.now().strftime('%Y-%m-%d')
                )
                remaining_loan_amount_with_accrued_interest += loan['outstanding_balance'] + accrued_interest

            # Total interest paid by this user across ALL their loans (historical included)
            total_interest_paid_by_user = conn.execute(
                "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'interest_paid' AND is_paid = 1",
                (user_id,)
            ).fetchone()[0] or 0.0
            
            # Monthly Contribution Status for the current month
            monthly_contribution_status = calculate_contribution_status(user_id, selected_group_id)

            # Total Amount Paid by User Till Date (Contributions + Loan Repayments)
            total_amount_paid_by_user_till_date = total_contributions_by_user + total_loan_repayments_by_user

            user_data = {
                'user_id': user_id,
                'user_name': user_name,
                'user_status': user['status'],
                'is_admin': user['is_admin'],
                'total_contributions_by_user': round(total_contributions_by_user, 2),
                'pending_contributions_by_user': round(pending_contributions_by_user, 2),
                'total_loans_disbursed_to_user': round(total_loans_disbursed_to_user, 2),
                'total_interest_paid_by_user': round(total_interest_paid_by_user, 2),
                'remaining_loan_amount_with_accrued_interest': round(remaining_loan_amount_with_accrued_interest, 2),
                'monthly_contribution_status': monthly_contribution_status,
                'total_amount_paid_by_user_till_date': round(total_amount_paid_by_user_till_date, 2),
                'loans': active_loans # Pass active loans for detailed view if needed
            }
            all_users_data.append(user_data)
        
        # Use the new helper function for group reports
        reports = get_group_financial_summary_reports(selected_group_id, conn)

        # Update saving_account_balance based on the reports dictionary
        # This aligns with the previous calculation logic for saving_account_balance
        saving_account_balance = (reports['total_contributions'] + reports['total_loan_repayments'] + reports['total_interest_received']) - \
                                 (reports['total_loans_disbursed'] + reports['total_pending_cash_payments'])
        reports['saving_account_balance'] = round(saving_account_balance, 2)
        
    conn.close()

    return render_template('index.html',
                            groups=groups,
                            all_users_data=all_users_data, # Pass all users data
                            users_in_selected_group=users_in_selected_group, # Pass for Add Loan Modal
                            selected_group_id=selected_group_id,
                            group_current_profit=group_current_profit,
                            reports=reports,
                            admin_user_id=admin_user_id,
                            current_date=datetime.now().strftime('%Y-%m-%d'),
                            get_group=get_group,
                            calculate_interest_due=calculate_interest_due,
                            get_marathi_label=get_marathi_label) # Pass the Marathi label function

@app.route('/all_groups_report')
def all_groups_report():
    conn = get_db_connection()
    groups = conn.execute('SELECT * FROM groups').fetchall()
    report_data = []

    for group in groups:
        group_id = group['id']
        group_name = group['name']
        
        # Use the new helper function to get comprehensive financial summaries for each group
        group_summary_reports = get_group_financial_summary_reports(group_id, conn)
        
        report_data.append({
            'group_name': group_name,
            'reports': group_summary_reports # Embed the reports dictionary
        })
    conn.close()
    return render_template('all_groups_report.html', all_groups_data=report_data, get_marathi_label=get_marathi_label)

@app.route('/add_group', methods=['POST'])
def add_group():
    name = request.form['group_name']
    bank_account_details = request.form.get('bank_account_details', '')
    default_interest_rate = float(request.form.get('default_interest_rate', 12.0))
    bank_interest_rate = float(request.form.get('bank_interest_rate', 3.0)) # New field
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO groups (name, bank_account_details, group_profit, default_interest_rate, bank_interest_rate) VALUES (?, ?, ?, ?, ?)', (name, bank_account_details, 0.0, default_interest_rate, bank_interest_rate))
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

@app.route('/update_bank_interest_rate', methods=['POST'])
def update_bank_interest_rate():
    group_id = request.form.get('group_id', type=int)
    new_bank_rate = request.form.get('new_bank_interest_rate', type=float)
    if not group_id:
        flash(get_marathi_label('invalid_group_id'), 'danger')
        return redirect(url_for('index'))
    if new_bank_rate is None or not (0 <= new_bank_rate <= 100):
        flash(get_marathi_label('interest_rate_range_error'), 'danger')
        return redirect(url_for('index', group_id=group_id))
    conn = get_db_connection()
    try:
        conn.execute('UPDATE groups SET bank_interest_rate = ? WHERE id = ?', (new_bank_rate, group_id))
        conn.commit()
        flash(get_marathi_label('bank_interest_rate_updated_success'), 'success')
    except Exception as e:
        flash(get_marathi_label('error_updating_bank_interest_rate').format(error=e), 'danger')
        conn.rollback() # Ensure rollback on error
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form['user_name']
    group_id = request.form['group_id']
    is_admin = request.form.get('is_admin') == 'on'
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (name, group_id, is_admin, status) VALUES (?, ?, ?, ?)', (name, group_id, is_admin, 'active'))
        conn.commit()
        flash(get_marathi_label('user_added_success').format(name=name), 'success')
    except Exception as e:
        flash(get_marathi_label('error_adding_user').format(error=e), 'danger')
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    if get_admin_user_id() is None or get_admin_user_id() != 1: # Basic admin...
        flash(get_marathi_label('unauthorized_access'), 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_status = 'inactive' if user['status'] == 'active' else 'active'
        conn.execute('UPDATE users SET status = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        flash(get_marathi_label('user_status_changed').format(status=new_status), 'success')
        group_id_to_redirect = user['group_id']
    else:
        flash(get_marathi_label('user_not_found'), 'danger')
        group_id_to_redirect = None # Or a default group ID if possible
    conn.close()
    return redirect(url_for('index', group_id=group_id_to_redirect))

@app.route('/add_contribution', methods=['POST'])
def add_contribution():
    user_id = request.form['user_id']
    group_id = request.form['group_id']
    amount = float(request.form['amount'])
    is_cash_payment = request.form.get('is_cash_payment') == 'on'
    
    # Determine is_paid status based on is_cash_payment
    is_paid = 0 if is_cash_payment else 1
    status_message_key = 'pending_cash_payment' if is_cash_payment else 'paid_upi_bank'

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO transactions (user_id, group_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (user_id, group_id, 'contribution', amount, datetime.now().strftime('%Y-%m-%d'), is_cash_payment, is_paid))
        conn.commit()
        user = get_user(user_id)
        flash(get_marathi_label('contribution_added_success').format(amount=amount, user_name=user['name'], status=get_marathi_label(status_message_key)), 'success')
    except Exception as e:
        flash(get_marathi_label('error_adding_contribution').format(error=e), 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/mark_cash_payment_paid/<int:transaction_id>', methods=['POST'])
def mark_cash_payment_paid(transaction_id):
    conn = get_db_connection()
    group_id_to_redirect = request.form.get('group_id', type=int) # Get group_id from form
    try:
        # Check if the transaction exists and is a pending cash payment
        transaction = conn.execute("SELECT * FROM transactions WHERE id = ? AND is_cash_payment = 1 AND is_paid = 0", (transaction_id,)).fetchone()
        
        if not transaction:
            flash(get_marathi_label('transaction_not_found'), 'danger')
            return redirect(url_for('index', group_id=group_id_to_redirect))
        
        # Mark as paid
        conn.execute("UPDATE transactions SET is_paid = 1 WHERE id = ?", (transaction_id,))
        conn.commit()
        flash(get_marathi_label('cash_payment_marked_paid'), 'success')

    except Exception as e:
        flash(f"Error marking payment as paid: {e}", 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id_to_redirect))

@app.route('/add_loan', methods=['POST'])
def add_loan():
    user_id = request.form.get('user_id', type=int)
    group_id = request.form.get('group_id', type=int)
    loan_amount = float(request.form.get('loan_amount'))
    loan_issue_date = request.form.get('loan_issue_date')
    loan_interest_rate = float(request.form.get('loan_interest_rate')) # This is the annual rate

    if not user_id or not group_id:
        flash(get_marathi_label('invalid_user_or_group'), 'danger')
        return redirect(url_for('index'))

    if loan_amount <= 0:
        flash(get_marathi_label('loan_amount_positive_error'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    if not (0 <= loan_interest_rate <= 100):
        flash(get_marathi_label('interest_rate_range_error'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    conn = get_db_connection()
    try:
        # 1. Record the loan in the loans table
        cursor = conn.cursor()
        cursor.execute('INSERT INTO loans (user_id, group_id, original_amount, outstanding_balance, current_interest_rate, issue_date, last_interest_calc_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (user_id, group_id, loan_amount, loan_amount, loan_interest_rate, loan_issue_date, loan_issue_date, 'active'))
        loan_id = cursor.lastrowid # Get the ID of the newly inserted loan

        # 2. Record the loan disbursement as a transaction
        user = get_user(user_id) # Need user name for flash message
        conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (user_id, group_id, loan_id, 'loan_disbursement', loan_amount, loan_issue_date, f'Loan disbursement for {user["name"]}', 0, 1))
        
        conn.commit()
        flash(get_marathi_label('loan_disbursed_success').format(loan_id=loan_id, amount=loan_amount, user_name=user['name'], rate=loan_interest_rate), 'success')
    except Exception as e:
        flash(get_marathi_label('error_adding_loan').format(error=e), 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/change_loan_interest_rate', methods=['POST'])
def change_loan_interest_rate():
    loan_id = request.form.get('loan_id', type=int)
    new_interest_rate = float(request.form.get('new_interest_rate'))
    group_id = request.form.get('group_id', type=int) # For redirect

    if not loan_id:
        flash(get_marathi_label('loan_id_missing'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    if not (0 <= new_interest_rate <= 100):
        flash(get_marathi_label('interest_rate_range_error'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    conn = get_db_connection()
    try:
        loan = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        if not loan:
            flash(get_marathi_label('loan_not_found').format(loan_id=loan_id), 'danger')
            return redirect(url_for('index', group_id=group_id))

        old_rate = loan['current_interest_rate']
        conn.execute("UPDATE loans SET current_interest_rate = ? WHERE id = ?", (new_interest_rate, loan_id))
        conn.commit()
        flash(get_marathi_label('loan_rate_changed_success').format(loan_id=loan_id, old_rate=old_rate, new_rate=new_interest_rate), 'success')
    except Exception as e:
        flash(get_marathi_label('error_changing_loan_rate').format(error=e), 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))


@app.route('/repay_loan', methods=['POST'])
def repay_loan():
    loan_id = request.form.get('loan_id', type=int)
    repayment_amount = float(request.form.get('repayment_amount'))
    group_id = request.form.get('group_id', type=int) # For redirect

    if not loan_id:
        flash(get_marathi_label('loan_id_missing'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    if repayment_amount <= 0:
        flash(get_marathi_label('repayment_amount_positive_error'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    conn = get_db_connection()
    try:
        loan = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        if not loan or loan['group_id'] != group_id:
            flash(get_marathi_label('loan_not_found').format(loan_id=loan_id), 'danger')
            return redirect(url_for('index', group_id=group_id))

        if loan['status'] == 'paid_off':
            flash(get_marathi_label('loan_already_paid_off'), 'info')
            return redirect(url_for('index', group_id=group_id))

        outstanding_balance = loan['outstanding_balance']
        current_interest_rate = loan['current_interest_rate']
        last_interest_calc_date_str = loan['last_interest_calc_date']
        issue_date_str = loan['issue_date']
        user_id = loan['user_id']

        # Calculate accrued interest since last interest calculation date or issue date if no previous payment
        interest_accrued_today = calculate_interest_due(
            outstanding_balance,
            current_interest_rate,
            last_interest_calc_date_str,
            datetime.now().strftime('%Y-%m-%d')
        )
        
        # How much of the repayment goes to interest and how much to principal
        interest_paid_amount = min(repayment_amount, interest_accrued_today)
        principal_repaid_amount = repayment_amount - interest_paid_amount

        new_outstanding_balance = outstanding_balance - principal_repaid_amount

        # DEBUG: Print loan repayment details before update
        print(f"DEBUG REPAY: Loan ID: {loan_id}, Original Outstanding: {outstanding_balance}, "
              f"Repayment Amount: {repayment_amount}, Interest Accrued: {interest_accrued_today}, "
              f"Interest Paid: {interest_paid_amount}, Principal Repaid: {principal_repaid_amount}, "
              f"New Outstanding: {new_outstanding_balance}")

        # Update loan outstanding balance and last interest calculation date
        conn.execute("UPDATE loans SET outstanding_balance = ?, last_interest_calc_date = ? WHERE id = ?",
                    (new_outstanding_balance, datetime.now().strftime('%Y-%m-%d'), loan_id))

        # Record loan repayment transaction
        conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (user_id, group_id, loan_id, 'loan_repayment', repayment_amount, datetime.now().strftime('%Y-%m-%d'), f'Loan repayment for loan ID {loan_id}', 0, 1))

        # Record interest paid transaction if any interest was paid
        if interest_paid_amount > 0:
            conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, description, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (user_id, group_id, loan_id, 'interest_paid', interest_paid_amount, datetime.now().strftime('%Y-%m-%d'), f'Interest paid for loan ID {loan_id}', 0, 1))
            
            # Update group_profit with the received interest
            conn.execute("UPDATE groups SET group_profit = group_profit + ? WHERE id = ?", (interest_paid_amount, group_id))

        # If loan is fully paid off
        if new_outstanding_balance <= 0:
            conn.execute("UPDATE loans SET status = 'paid_off', outstanding_balance = 0 WHERE id = ?", (loan_id,))
            flash(get_marathi_label('loan_fully_paid_off').format(loan_id=loan_id), 'success')
        
        conn.commit()

        # DEBUG: Verify updated loan status and outstanding balance
        updated_loan = conn.execute("SELECT outstanding_balance, status FROM loans WHERE id = ?", (loan_id,)).fetchone()
        print(f"DEBUG REPAY: After Commit - Loan ID: {loan_id}, DB Outstanding: {updated_loan['outstanding_balance']}, DB Status: {updated_loan['status']}")


        flash(get_marathi_label('loan_repayment_processed_success').format(
            repayment_amount=repayment_amount,
            loan_id=loan_id,
            actual_principal_repaid=principal_repaid_amount,
            interest_paid_amount=interest_paid_amount,
            new_outstanding_balance=new_outstanding_balance
        ), 'success')

    except Exception as e:
        flash(get_marathi_label('error_repaying_loan').format(error=e), 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))


# --- Bulk Upload CSV Functions ---

@app.route('/download_sample_transactions_csv')
def download_sample_transactions_csv():
    # Sample CSV content for transactions
    sample_csv_content = (
        "user_name,type,amount,date,is_cash_payment,is_paid,loan_id,new_loan_interest_rate\n"
        "सदस्य_अ,contribution,500,2024-05-15,0,1,\n"
        "सदस्य_ब,loan_disbursement,10000,2024-05-16,,24.0,\n"
        "सदस्य_क,loan_repayment,1200,2024-05-17,0,1,101\n" # Assuming loan_id 101 exists for सदस्य_क
    )
    
    # Create an in-memory file for the CSV content
    csv_file = io.BytesIO(sample_csv_content.encode('utf-8'))
    
    # Set up Flask response to send the file
    return send_from_directory(
        app.root_path, # Or a specific directory if you save it to disk
        'sample_transactions_upload.csv', # Dummy filename for the download
        mimetype='text/csv',
        as_attachment=True,
        download_name='sample_transactions_upload.csv'
    )

@app.route('/download_sample_users_csv')
def download_sample_users_csv():
    sample_csv_content = (
        "user_name,group_name,is_admin\n"
        "नवीन सदस्य १,गट अ,0\n"
        "नवीन सदस्य २,गट ब,1\n"
    )
    # Create an in-memory file for the CSV content
    csv_file = io.BytesIO(sample_csv_content.encode('utf-8'))
    
    return send_from_directory(
        app.root_path,
        'sample_users_upload.csv',
        mimetype='text/csv',
        as_attachment=True,
        download_name='sample_users_upload.csv'
    )

@app.route('/bulk_upload_users', methods=['POST'])
def bulk_upload_users():
    print(f"DEBUG: bulk_upload_users request.form: {request.form}") # DEBUG PRINT
    group_id = request.form.get('group_id', type=int)
    if not group_id:
        flash(get_marathi_label('please_select_group'), 'danger')
        return redirect(url_for('index'))

    if 'file' not in request.files:
        flash(get_marathi_label('no_file_part'), 'danger')
        return redirect(url_for('index', group_id=group_id))
    
    file = request.files['file']
    if file.filename == '':
        flash(get_marathi_label('no_selected_file'), 'danger')
        return redirect(url_for('index', group_id=group_id))
    
    if not file.filename.endswith('.csv'):
        flash(get_marathi_label('invalid_file_type'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    processed_count = 0
    error_count = 0
    errors = []
    conn = get_db_connection()
    try:
        # Read the file content into a BytesIO object
        file_content = io.BytesIO(file.read())
        file_content.seek(0) # Rewind to the beginning of the stream

        # Decode using utf-8-sig to handle BOM if present, otherwise utf-8
        csv_reader = csv.reader(io.TextIOWrapper(file_content, encoding='utf-8-sig'))
        
        header = [h.strip() for h in next(csv_reader)] # Read header
        
        # Define expected headers and their corresponding DB columns/logic
        expected_headers = ['user_name', 'group_name', 'is_admin']
        if not all(h in header for h in expected_headers):
            flash(f"CSV headers mismatch. Expected: {', '.join(expected_headers)}", 'danger')
            return redirect(url_for('index', group_id=group_id))

        for row_num, row in enumerate(csv_reader, start=2):
            try:
                row_data = dict(zip(header, row))
                user_name = row_data.get('user_name')
                is_admin_str = row_data.get('is_admin', '0').strip()
                is_admin = is_admin_str.lower() in ['1', 'true', 'yes']

                if not user_name:
                    errors.append(get_marathi_label('missing_user_or_group').format(row_num=row_num))
                    error_count += 1
                    continue

                # Check if user already exists in this group
                existing_user = conn.execute("SELECT id FROM users WHERE name = ? AND group_id = ?", (user_name, group_id)).fetchone()
                if existing_user:
                    flash(get_marathi_label('user_exists_in_group').format(row_num=row_num, user_name=user_name, target_group_id=group_id), 'info')
                    processed_count += 1 # Count as processed even if skipped to acknowledge
                    continue

                conn.execute('INSERT INTO users (name, group_id, is_admin, status) VALUES (?, ?, ?, ?)', (user_name, group_id, is_admin, 'active'))
                processed_count += 1
                flash(get_marathi_label('user_added_to_group').format(row_num=row_num, user_name=user_name, target_group_id=group_id), 'success')

            except Exception as e:
                errors.append(get_marathi_label('error_processing_row').format(row_num=row_num, error=e))
                error_count += 1
                conn.rollback() # Rollback current row if error
                continue
        
        conn.commit()
        flash(get_marathi_label('upload_complete').format(processed_count=processed_count, error_count=error_count), 'success')

    except Exception as e:
        flash(get_marathi_label('upload_error').format(error=e), 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))


@app.route('/bulk_upload_transactions', methods=['POST'])
def bulk_upload_transactions():
    print(f"DEBUG: bulk_upload_transactions request.form: {request.form}") # DEBUG PRINT
    group_id = request.form.get('group_id', type=int)
    if not group_id:
        flash(get_marathi_label('please_select_group'), 'danger')
        return redirect(url_for('index'))

    if 'file' not in request.files:
        flash(get_marathi_label('no_file_part'), 'danger')
        return redirect(url_for('index', group_id=group_id))
    
    file = request.files['file']
    if file.filename == '':
        flash(get_marathi_label('no_selected_file'), 'danger')
        return redirect(url_for('index', group_id=group_id))
    
    if not file.filename.endswith('.csv'):
        flash(get_marathi_label('invalid_file_type'), 'danger')
        return redirect(url_for('index', group_id=group_id))

    processed_count = 0
    error_count = 0
    errors = []
    
    # Store transactions for potential duplicate check
    transactions_to_process = []

    conn = get_db_connection()
    try:
        file_content = io.BytesIO(file.read())
        file_content.seek(0) # Rewind to the beginning of the stream
        csv_reader = csv.reader(io.TextIOWrapper(file_content, encoding='utf-8-sig'))
        
        header = [h.strip() for h in next(csv_reader)]
        
        # Define expected headers for transactions
        expected_transaction_headers = ['user_name', 'type', 'amount', 'date', 'is_cash_payment', 'is_paid', 'loan_id', 'new_loan_interest_rate']
        if not all(h in header for h in expected_transaction_headers):
            flash(f"CSV headers mismatch. Expected: {', '.join(expected_transaction_headers)}", 'danger')
            return redirect(url_for('index', group_id=group_id))

        for row_num, row in enumerate(csv_reader, start=2):
            try:
                row_data = dict(zip(header, row))
                user_name = row_data.get('user_name')
                transaction_type = row_data.get('type')
                amount_str = row_data.get('amount')
                date_str = row_data.get('date')
                is_cash_payment_str = str(row_data.get('is_cash_payment', '0')).strip() # Handle None with str()
                is_paid_str = str(row_data.get('is_paid', '1')).strip() # Default to paid for non-cash, handle None with str()
                loan_id_str = str(row_data.get('loan_id', '')).strip() # Handle None with str()
                new_loan_interest_rate_str = str(row_data.get('new_loan_interest_rate', '')).strip() # Handle None with str()

                if not user_name or not transaction_type or not amount_str or not date_str:
                    errors.append(get_marathi_label('missing_user_or_group').format(row_num=row_num))
                    error_count += 1
                    continue
                
                # Data type conversions
                try:
                    amount = float(amount_str)
                    is_cash_payment = is_cash_payment_str.lower() in ['1', 'true', 'yes']
                    is_paid = is_paid_str.lower() in ['1', 'true', 'yes']
                    # For cash payments, is_paid should always be 0 initially unless explicitly marked 1 in CSV
                    if is_cash_payment and not is_paid:
                        is_paid = 0
                    elif is_cash_payment and is_paid: # If cash and explicitly marked paid
                        is_paid = 1
                    elif not is_cash_payment: # Non-cash payments are always paid
                        is_paid = 1

                    # Date format check and conversion
                    datetime.strptime(date_str, '%Y-%m-%d') # Validate date format
                except ValueError as ve:
                    errors.append(get_marathi_label('data_conversion_error').format(error=ve))
                    error_count += 1
                    continue

                # Get user_id for the given user_name and group_id
                user = conn.execute("SELECT id FROM users WHERE name = ? AND group_id = ?", (user_name, group_id)).fetchone()
                if not user:
                    errors.append(get_marathi_label('user_not_found_in_group').format(user_name=user_name, group_name=get_group(group_id)['name']))
                    error_count += 1
                    continue
                user_id = user['id']

                transaction_details = {
                    'row_num': row_num,
                    'user_id': user_id,
                    'group_id': group_id,
                    'type': transaction_type,
                    'amount': amount,
                    'date': date_str,
                    'is_cash_payment': is_cash_payment,
                    'is_paid': is_paid,
                    'loan_id': int(loan_id_str) if loan_id_str else None,
                    'new_loan_interest_rate': float(new_loan_interest_rate_str) if new_loan_interest_rate_str else None
                }
                transactions_to_process.append(transaction_details)

            except Exception as e:
                errors.append(get_marathi_label('error_processing_row').format(row_num=row_num, error=e))
                error_count += 1
                continue
        
        # Check for duplicates before processing
        duplicate_transactions_found = []
        for i, t1 in enumerate(transactions_to_process):
            for j, t2 in enumerate(transactions_to_process):
                if i < j and t1['user_id'] == t2['user_id'] and t1['type'] in ['contribution', 'loan_repayment'] and t1['date'] == t2['date']:
                    duplicate_transactions_found.append({
                        'user_name': conn.execute("SELECT name FROM users WHERE id = ?", (t1['user_id'],)).fetchone()['name'],
                        'transaction_type': t1['type'],
                        'transaction_amount': t1['amount'],
                        'transaction_date': t1['date'],
                        'row_num_1': t1['row_num'],
                        'row_num_2': t2['row_num']
                    })
        
        if duplicate_transactions_found and not request.form.get('confirm_duplicates'):
            session['transactions_to_process'] = transactions_to_process # Store for next request
            session['group_id_for_upload'] = group_id
            return render_template('confirm_duplicates.html', 
                                   duplicates=duplicate_transactions_found, 
                                   get_marathi_label=get_marathi_label)

        # Process transactions (after duplicate confirmation or if no duplicates)
        for t in transactions_to_process:
            try:
                if t['type'] == 'contribution':
                    conn.execute('INSERT INTO transactions (user_id, group_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                (t['user_id'], t['group_id'], t['type'], t['amount'], t['date'], t['is_cash_payment'], t['is_paid']))
                
                elif t['type'] == 'loan_disbursement':
                    if t['loan_id'] is not None:
                        raise ValueError(get_marathi_label('loan_id_not_for_new_loan'))
                    if t['new_loan_interest_rate'] is None or not (0 <= t['new_loan_interest_rate'] <= 100): # Check for None explicitly
                        raise ValueError(get_marathi_label('invalid_interest_rate').format(rate=t['new_loan_interest_rate']))
                    
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO loans (user_id, group_id, original_amount, outstanding_balance, current_interest_rate, issue_date, last_interest_calc_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                (t['user_id'], t['group_id'], t['amount'], t['amount'], t['new_loan_interest_rate'], t['date'], t['date'], 'active'))
                    loan_id = cursor.lastrowid
                    conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                (t['user_id'], t['group_id'], loan_id, t['type'], t['amount'], t['date'], t['is_cash_payment'], t['is_paid']))

                elif t['type'] == 'loan_repayment':
                    loan_id = t['loan_id']
                    if loan_id is None:
                        raise ValueError(get_marathi_label('loan_id_missing'))
                    
                    loan = conn.execute("SELECT * FROM loans WHERE id = ? AND user_id = ? AND group_id = ?", (loan_id, t['user_id'], t['group_id'])).fetchone()
                    if not loan:
                        raise ValueError(get_marathi_label('loan_not_found').format(loan_id=loan_id))
                    if loan['status'] == 'paid_off':
                        raise ValueError(get_marathi_label('loan_already_paid_off'))
                    
                    outstanding_balance = loan['outstanding_balance']
                    current_interest_rate = loan['current_interest_rate']
                    last_interest_calc_date_str = loan['last_interest_calc_date']

                    interest_accrued_for_repayment = calculate_interest_due(
                        outstanding_balance,
                        current_interest_rate,
                        last_interest_calc_date_str,
                        t['date'] # Use transaction date from CSV
                    )
                    
                    interest_paid_amount = min(t['amount'], interest_accrued_for_repayment)
                    principal_repaid_amount = t['amount'] - interest_paid_amount
                    new_outstanding_balance = outstanding_balance - principal_repaid_amount

                    # DEBUG: Print loan repayment details before update in bulk upload
                    print(f"DEBUG BULK REPAY: Loan ID: {loan_id}, Original Outstanding: {outstanding_balance}, "
                          f"Repayment Amount: {t['amount']}, Interest Accrued: {interest_accrued_for_repayment}, "
                          f"Interest Paid: {interest_paid_amount}, Principal Repaid: {principal_repaid_amount}, "
                          f"New Outstanding: {new_outstanding_balance}")

                    conn.execute("UPDATE loans SET outstanding_balance = ?, last_interest_calc_date = ? WHERE id = ?",
                                (new_outstanding_balance, t['date'], loan_id))

                    conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                (t['user_id'], t['group_id'], loan_id, t['type'], t['amount'], t['date'], t['is_cash_payment'], t['is_paid']))
                    
                    if interest_paid_amount > 0:
                        conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                    (t['user_id'], t['group_id'], loan_id, 'interest_paid', interest_paid_amount, t['date'], t['is_cash_payment'], t['is_paid']))
                        conn.execute("UPDATE groups SET group_profit = group_profit + ? WHERE id = ?", (interest_paid_amount, t['group_id']))

                    if new_outstanding_balance <= 0:
                        conn.execute("UPDATE loans SET status = 'paid_off', outstanding_balance = 0 WHERE id = ?", (loan_id,))
                    
                    # DEBUG: Verify updated loan status and outstanding balance after commit (within this try block)
                    # Note: This conn.execute will be part of the larger transaction.
                    # It's better to fetch *after* the final conn.commit() if possible for true verification.
                    # For immediate debugging, this is fine.
                    updated_loan = conn.execute("SELECT outstanding_balance, status FROM loans WHERE id = ?", (loan_id,)).fetchone()
                    print(f"DEBUG BULK REPAY: After Loan Update - Loan ID: {loan_id}, DB Outstanding: {updated_loan['outstanding_balance']}, DB Status: {updated_loan['status']}")


                else:
                    errors.append(get_marathi_label('unknown_transaction_type').format(transaction_type=t['type']))
                    error_count += 1
                    continue
                
                processed_count += 1

            except Exception as e:
                errors.append(get_marathi_label('error_processing_row').format(row_num=t['row_num'], error=e))
                error_count += 1
                continue # Continue to next row even if one fails
        
        conn.commit()
        flash(get_marathi_label('upload_complete').format(processed_count=processed_count, error_count=error_count), 'success')
        for err in errors:
            flash(err, 'danger')

    except Exception as e:
        flash(get_marathi_label('upload_error').format(error=e), 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index', group_id=group_id))

@app.route('/confirm_duplicate_transactions', methods=['POST'])
def confirm_duplicate_transactions():
    print(f"DEBUG: confirm_duplicate_transactions request.form: {request.form}") # DEBUG PRINT
    transactions_to_process = session.pop('transactions_to_process', None)
    group_id = session.pop('group_id_for_upload', None)

    if not transactions_to_process or not group_id:
        flash("Session data missing for duplicate confirmation.", 'danger')
        # Attempt to redirect to index without a group_id if not available
        return redirect(url_for('index'))

    if request.form.get('action') == 'accept':
        flash(get_marathi_label('processing_duplicates_accepted'), 'info')
        # Re-call the bulk_upload_transactions logic to process, now with confirmation
        # This is a bit of a hack as it re-processes from session. Better would be to have a helper function.
        # For simplicity, we'll mimic the logic here.
        processed_count = 0
        error_count = 0
        errors = []
        conn = get_db_connection()
        try:
            for t in transactions_to_process:
                try:
                    if t['type'] == 'contribution':
                        conn.execute('INSERT INTO transactions (user_id, group_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                    (t['user_id'], t['group_id'], t['type'], t['amount'], t['date'], t['is_cash_payment'], t['is_paid']))
                    
                    elif t['type'] == 'loan_disbursement':
                        if t['loan_id'] is not None:
                            raise ValueError(get_marathi_label('loan_id_not_for_new_loan'))
                        if t['new_loan_interest_rate'] is None or not (0 <= t['new_loan_interest_rate'] <= 100): # Check for None explicitly
                            raise ValueError(get_marathi_label('invalid_interest_rate').format(rate=t['new_loan_interest_rate']))
                        
                        cursor = conn.cursor()
                        cursor.execute('INSERT INTO loans (user_id, group_id, original_amount, outstanding_balance, current_interest_rate, issue_date, last_interest_calc_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                    (t['user_id'], t['group_id'], t['amount'], t['amount'], t['new_loan_interest_rate'], t['date'], t['date'], 'active'))
                        loan_id = cursor.lastrowid
                        conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                    (t['user_id'], t['group_id'], loan_id, t['type'], t['amount'], t['date'], t['is_cash_payment'], t['is_paid']))

                    elif t['type'] == 'loan_repayment':
                        loan_id = t['loan_id']
                        if loan_id is None:
                            raise ValueError(get_marathi_label('loan_id_missing'))
                        
                        loan = conn.execute("SELECT * FROM loans WHERE id = ? AND user_id = ? AND group_id = ?", (loan_id, t['user_id'], t['group_id'])).fetchone()
                        if not loan:
                            raise ValueError(get_marathi_label('loan_not_found').format(loan_id=loan_id))
                        if loan['status'] == 'paid_off':
                            raise ValueError(get_marathi_label('loan_already_paid_off'))
                        
                        outstanding_balance = loan['outstanding_balance']
                        current_interest_rate = loan['current_interest_rate']
                        last_interest_calc_date_str = loan['last_interest_calc_date']

                        interest_accrued_for_repayment = calculate_interest_due(
                            outstanding_balance,
                            current_interest_rate,
                            last_interest_calc_date_str,
                            t['date'] # Use transaction date from CSV
                        )
                        
                        interest_paid_amount = min(t['amount'], interest_accrued_for_repayment)
                        principal_repaid_amount = t['amount'] - interest_paid_amount
                        new_outstanding_balance = outstanding_balance - principal_repaid_amount

                        conn.execute("UPDATE loans SET outstanding_balance = ?, last_interest_calc_date = ? WHERE id = ?",
                                    (new_outstanding_balance, t['date'], loan_id))

                        conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                    (t['user_id'], t['group_id'], loan_id, t['type'], t['amount'], t['date'], t['is_cash_payment'], t['is_paid']))
                        
                        if interest_paid_amount > 0:
                            conn.execute('INSERT INTO transactions (user_id, group_id, loan_id, type, amount, date, is_cash_payment, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                        (t['user_id'], t['group_id'], loan_id, 'interest_paid', interest_paid_amount, t['date'], t['is_cash_payment'], t['is_paid']))
                            conn.execute("UPDATE groups SET group_profit = group_profit + ? WHERE id = ?", (interest_paid_amount, t['group_id']))

                        if new_outstanding_balance <= 0:
                            conn.execute("UPDATE loans SET status = 'paid_off', outstanding_balance = 0 WHERE id = ?", (loan_id,))

                    else:
                        errors.append(get_marathi_label('unknown_transaction_type').format(transaction_type=t['type']))
                        error_count += 1
                        continue
                    
                    processed_count += 1
                except Exception as e:
                    errors.append(get_marathi_label('error_processing_row').format(row_num=t['row_num'], error=e))
                    error_count += 1
                    continue
            conn.commit()
            flash(get_marathi_label('upload_complete').format(processed_count=processed_count, error_count=error_count), 'success')
            for err in errors:
                flash(err, 'danger')
        except Exception as e:
            flash(get_marathi_label('upload_error').format(error=e), 'danger')
            conn.rollback()
        finally:
            conn.close()

    else: # Reject duplicates
        flash(get_marathi_label('duplicate_transactions_rejected'), 'info')
    
    return redirect(url_for('index', group_id=group_id))


@app.route('/transactions/<int:user_id>')
def view_transactions(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash(get_marathi_label('user_not_found'), 'danger')
        conn.close()
        return redirect(url_for('index'))

    group_id = user['group_id']
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')

    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]

    if from_date_str:
        query += " AND date >= ?"
        params.append(from_date_str)
    if to_date_str:
        query += " AND date <= ?"
        params.append(to_date_str)

    query += " ORDER BY date DESC"
    transactions = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('transactions.html', 
                           user=user, 
                           transactions=transactions, 
                           group_id=group_id,
                           from_date=from_date_str, 
                           to_date=to_date_str,
                           get_marathi_label=get_marathi_label)

@app.route('/download_transactions_csv/<int:user_id>')
def download_transactions_csv(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT name, group_id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash(get_marathi_label('user_not_found'), 'danger')
        conn.close()
        return redirect(url_for('index'))

    query = "SELECT type, amount, date, description, is_cash_payment, is_paid, loan_id FROM transactions WHERE user_id = ? ORDER BY date DESC"
    transactions = conn.execute(query, (user_id,)).fetchall()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si)

    headers = ['Type', 'Amount', 'Date', 'Description', 'Is Cash Payment', 'Is Paid', 'Loan ID']
    cw.writerow(headers)

    for transaction in transactions:
        row = [
            transaction['type'],
            transaction['amount'],
            transaction['date'],
            transaction['description'],
            'Yes' if transaction['is_cash_payment'] else 'No',
            'Yes' if transaction['is_paid'] else 'No',
            transaction['loan_id'] if transaction['loan_id'] else ''
        ]
        cw.writerow(row)

    output = io.BytesIO(si.getvalue().encode('utf-8'))
    output.seek(0)

    return send_from_directory(
        app.root_path,
        f'{user["name"]}_transactions.csv',
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{user["name"]}_transactions_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/download_users_csv/<int:group_id>')
def download_users_csv(group_id):
    conn = get_db_connection()
    group = conn.execute('SELECT name FROM groups WHERE id = ?', (group_id,)).fetchone()
    if not group:
        flash(get_marathi_label('group_not_found').format(row_num='N/A', group_identifier=group_id), 'danger')
        conn.close()
        return redirect(url_for('index'))

    users = conn.execute('SELECT name, is_admin, status FROM users WHERE group_id = ? ORDER BY name ASC', (group_id,)).fetchall()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si)

    headers = ['User Name', 'Is Admin', 'Status']
    cw.writerow(headers)

    for user in users:
        row = [
            user['name'],
            'Yes' if user['is_admin'] else 'No',
            user['status']
        ]
        cw.writerow(row)

    output = io.BytesIO(si.getvalue().encode('utf-8'))
    output.seek(0)

    return send_from_directory(
        app.root_path,
        f'{group["name"]}_users.csv',
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{group["name"]}_users_{datetime.now().strftime("%Y%m%d")}.csv'
    )

# --- Run the application ---
if __name__ == '__main__':
    # Create the sample CSV files in the application's root directory if they don't exist
    # This is for the `send_from_directory` to work correctly when deploying
    # For `app.run(debug=True)`, it often serves from memory or current directory,
    # but for production, having actual files is better.
    with open('sample_transactions_upload.csv', 'w', encoding='utf-8') as f:
        f.write("""user_name,type,amount,date,is_cash_payment,is_paid,loan_id,new_loan_interest_rate
अनिता ज्ञानोबा अडसुळे,contribution,1000,2024-05-01,0,1,
आशा सत्यशील कांबळे,loan_disbursement,5000,2024-05-01,,24.0,
आशा सत्यशील कांबळे,loan_repayment,1000,2024-05-02,0,1,1
""")
    with open('sample_users_upload.csv', 'w', encoding='utf-8') as f:
        f.write("""user_name,group_name,is_admin
नवीन सदस्य १,गट अ,0
नवीन सदस्य २,गट ब,1
""")
    init_db() # Initialize the database tables if they don't exist
    app.run(debug=True)