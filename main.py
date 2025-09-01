from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from sqlalchemy import or_ , func

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

import requests
from functools import lru_cache

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Use PostgreSQL from environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Expense(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    desc = db.Column(db.String(500), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(200), nullable=False)

    def __repr__(self) -> str:
        return f"{self.sno} - {self.amount}"

@app.route('/', methods=['GET'])
def home():
    searchtext = request.args.get('search')
    if searchtext:
        searchExpenses = Expense.query.filter(or_(
                func.cast(Expense.amount, db.String).ilike(f"%{searchtext}%"),
                Expense.desc.ilike(f"%{searchtext}%"),
                func.cast(Expense.date, db.String).ilike(f"%{searchtext}%")
            )).all()
        return render_template("index.html", allExpenses = searchExpenses)
    
    allExpenses = Expense.query.all()
    return render_template("index.html", allExpenses = allExpenses)

@app.route("/add-expense", methods=['GET','POST'])
def add():
    if request.method == 'POST':
        desc = request.form['desc']
        amount = request.form['amount']
        currency = request.form['currency']
        expense = Expense(desc=desc, amount=amount, currency=currency)
        db.session.add(expense)
        db.session.commit()
        return redirect("/")
    
    return render_template("add.html")

@app.route('/delete-expense/<int:sno>')
def delete(sno):
    delexpense = Expense.query.filter_by(sno=sno).first()
    db.session.delete(delexpense)
    db.session.commit()
    return redirect("/")

@app.route('/update-expense/<int:sno>', methods=['GET', 'POST'])
def update(sno):
    if request.method == 'POST':
        newamount = request.form['amount']
        newdesc = request.form['desc']
        newcurrency = request.form['currency']
        expense = Expense.query.filter_by(sno=sno).first()
        expense.amount = newamount
        expense.desc = newdesc
        expense.currency = newcurrency
        db.session.add(expense)
        db.session.commit()
        return redirect("/")

    updateexpense = Expense.query.filter_by(sno=sno).first()
    return render_template("update.html", updateexpense = updateexpense)


@lru_cache(maxsize=1)
def get_exchange_rates(base='INR'):
    url = f"https://api.exchangerate-api.com/v4/latest/{base}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to fetch exchange rates.")
    return response.json()["rates"]


def convert_to_inr(amount, currency, rates):
    if currency.upper() == 'INR':
        return amount
    try:
        rate = rates.get(currency.upper())
        if rate is None:
            raise ValueError(f"No exchange rate for {currency}")
        return amount / rate  # Since base is INR
    except Exception as e:
        print(f"Conversion error: {e}")
        return 0


@app.route("/report/summary")
def report_summary():
    expenses = Expense.query.all()
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

@app.route("/report/monthly")
def report_monthly():
    expenses = Expense.query.all()
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

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route('/report/pdf')
def download_pdf():
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Fetch summary data
    total = db.session.query(func.sum(Expense.amount)).scalar() or 0
    avg = db.session.query(func.avg(Expense.amount)).scalar() or 0
    max_expense = db.session.query(func.max(Expense.amount)).scalar() or 0

    # Fetch monthly data
    monthly_results = db.session.query(
       func.to_char(Expense.date, 'YYYY-MM').label("month"),
        func.sum(Expense.amount).label("total")
    ).group_by("month").order_by("month").all()

    # Document Title
    title_text = "Expense Report"
    p.setFont("Helvetica-Bold", 18)
    text_width = p.stringWidth(title_text, "Helvetica-Bold", 18)
    p.drawString((width - text_width) / 2, height - 1 * inch, title_text)


    # Summary
    p.setFont("Helvetica", 12)
    p.drawString(1 * inch, height - 1.5 * inch, f"Total Spent: Rs. {total}")
    p.drawString(1 * inch, height - 1.8 * inch, f"Average Expense: Rs. {round(avg, 2)}")
    p.drawString(1 * inch, height - 2.1 * inch, f"Max Expense: Rs. {max_expense}")

    # Monthly Header
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1 * inch, height - 2.7 * inch, "Monthly Breakdown")

    # Monthly Data
    p.setFont("Helvetica", 12)
    y = height - 3.0 * inch
    for month, total in monthly_results:
        p.drawString(1.2 * inch, y, f"{month}: Rs. {total}")
        y -= 0.25 * inch

        # Auto add page if we run out of space
        if y < 1 * inch:
            p.showPage()
            y = height - 1 * inch
            p.setFont("Helvetica", 12)

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='expense_report.pdf',
        mimetype='application/pdf'
    )

# Temporary route to initialize the PostgreSQL DB
@app.route('/setup')
def setup():
    db.create_all()
    return "Database tables created successfully! ✅"

if __name__ == '__main__':
    app.run(debug=True)