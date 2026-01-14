def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200

def test_add_expense(client):
    response = client.post("/add-expense", data={
        "desc": "Dinner",
        "amount": 300,
        "currency": "INR"
    }, follow_redirects=True)

    assert response.status_code == 200

    from main import Expense
    assert Expense.query.filter_by(desc="Dinner").count() == 1

def test_dashboard(client):
    response = client.get("/dashboard")
    assert response.status_code == 200