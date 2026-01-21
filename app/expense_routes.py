from flask import Blueprint, render_template, request, redirect, send_file
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from .models import db, Expense
from decimal import Decimal
from functools import lru_cache
from io import BytesIO
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

expense_bp = Blueprint('expense', __name__)


@expense_bp.route('/')
@login_required
def home():
    search = request.args.get('search')

    query = Expense.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(or_(
            Expense.desc.ilike(f"%{search}%"),
            func.cast(Expense.amount, db.String).ilike(f"%{search}%"),
            func.cast(Expense.date, db.String).ilike(f"%{search}%")
        ))

    expenses = query.all()
    return render_template('index.html', allExpenses=expenses)


@expense_bp.route('/add-expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        expense = Expense(
            desc=request.form['desc'],
            amount=Decimal(request.form['amount']),
            currency=request.form['currency'],
            user_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        return redirect('/')

    return render_template('add.html')


@expense_bp.route('/delete-expense/<int:sno>')
@login_required
def delete_expense(sno):
    expense = Expense.query.filter_by(sno=sno, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    return redirect('/')


@expense_bp.route('/update-expense/<int:sno>', methods=['GET', 'POST'])
@login_required
def update_expense(sno):
    expense = Expense.query.filter_by(sno=sno, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        expense.desc = request.form['desc']
        expense.amount = request.form['amount']
        expense.currency = request.form['currency']
        db.session.commit()
        return redirect('/')

    return render_template('update.html', updateexpense=expense)

@expense_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

@lru_cache(maxsize=1)
def get_exchange_rates(base='INR'):
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Failed to fetch exchange rates.")
        return response.json()["rates"]

def convert_to_inr(amount, currency, rates):
        if currency.upper() == 'INR':
            return float(amount)  # cast to float
        try:
            rate = rates.get(currency.upper())
            if rate is None:
                raise ValueError(f"No exchange rate for {currency}")
            return float(amount) / rate  # always float
        except Exception as e:
            print(f"Conversion error: {e}")
            return 0.0

@expense_bp.route("/report/summary")
def report_summary():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    rates = get_exchange_rates(base='INR')

    converted_amounts = [
        convert_to_inr(exp.amount, exp.currency, rates) for exp in expenses
    ]

    total = sum(converted_amounts)
    avg = total / len(converted_amounts) if converted_amounts else 0
    max_expense = max(converted_amounts) if converted_amounts else 0

    return {
        "total_spent": round(total,2),
        "average_expense": round(avg,2),
        "max_expense": round(max_expense,2)
    }

@expense_bp.route("/report/monthly")
def report_monthly():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    rates = get_exchange_rates(base='INR')

    monthly_data = {}
    for exp in expenses:
        month = exp.date.strftime('%Y-%m')
        amount_in_inr = convert_to_inr(exp.amount, exp.currency, rates)

        if month not in monthly_data:
            monthly_data[month] = 0
        monthly_data[month] += amount_in_inr

    monthly_data = {month: round(total, 2) for month, total in monthly_data.items()}
    return monthly_data