from flask import Flask, render_template, request, redirect, url_for
from db import get_connection

app = Flask(__name__)

STATUSES = ["Pending", "In Progress", "Completed"]


@app.route("/")
def index():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, customer_name, product_name, issue, status, created_at "
            "FROM service_requests ORDER BY id DESC LIMIT 50"
        )
        requests_list = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS total FROM service_requests")
        total = cur.fetchone()["total"]
    return render_template("index.html", requests=requests_list,total=total, statuses=STATUSES)


@app.route("/add", methods=["POST"])
def add_request():
    name = request.form.get("customer_name", "").strip()
    product = request.form.get("product_name", "").strip()
    issue = request.form.get("issue", "").strip()
    if name and product and issue:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO service_requests (customer_name, product_name, issue) "
                "VALUES (%s, %s, %s)",
                (name, product, issue),
            )
    return redirect(url_for("index"))


@app.route("/update/<int:request_id>", methods=["POST"])
def update_status(request_id):
    status = request.form.get("status")
    if status in STATUSES:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE service_requests SET status = %s WHERE id = %s",
                (status, request_id),
            )
    return redirect(url_for("index"))


@app.route("/health")
def health():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
