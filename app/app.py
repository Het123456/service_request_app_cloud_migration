
from flask import Flask, render_template, request, redirect, url_for
from db import get_connection
from time import perf_counter

app = Flask(__name__)

STATUSES = ["Pending", "In Progress", "Completed"]


@app.route("/")
def index():
    search_id = request.args.get("search_id", type=int)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 50
    timing = None

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM service_requests")
        total = cur.fetchone()["total"]
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)

        if search_id is not None:
            start = perf_counter()
            cur.execute(
                "SELECT * FROM service_requests WHERE id = %s",
                (search_id,)
            )
            ms = (perf_counter() - start) * 1000
            timing = f"SELECT BY ID executed in {ms:.2f} ms"
        else:
            offset = (page - 1) * per_page
            cur.execute(
                "SELECT * FROM service_requests "
                "ORDER BY id DESC LIMIT %s OFFSET %s",
                (per_page, offset)
            )

        requests_list = cur.fetchall()

    return render_template(
        "index.html",
        requests=requests_list,
        total=total,
        statuses=STATUSES,
        timing=timing,
        page=page,
        total_pages=total_pages
    )


@app.route("/add", methods=["POST"])
def add_request():
    name = request.form.get("customer_name", "").strip()
    product = request.form.get("product_name", "").strip()
    issue = request.form.get("issue", "").strip()

    if name and product and issue:
        with get_connection() as conn, conn.cursor() as cur:
            start = perf_counter()

            cur.execute(
                "INSERT INTO service_requests (customer_name, product_name, issue) "
                "VALUES (%s, %s, %s)",
                (name, product, issue),
            )

            ms = (perf_counter() - start) * 1000

        return redirect(
            url_for("index", timing=f"INSERT executed in {ms:.2f} ms")
        )

    return redirect(url_for("index"))


@app.route("/update/<int:request_id>", methods=["POST"])
def update_status(request_id):
    status = request.form.get("status")

    if status in STATUSES:
        with get_connection() as conn, conn.cursor() as cur:
            start = perf_counter()

            cur.execute(
                "UPDATE service_requests SET status = %s WHERE id = %s",
                (status, request_id),
            )

            ms = (perf_counter() - start) * 1000

        return redirect(
            url_for("index", timing=f"UPDATE executed in {ms:.2f} ms")
        )

    return redirect(url_for("index"))


@app.route("/health")
def health():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")

    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

