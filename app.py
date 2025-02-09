from flask import Flask, request, jsonify
import uuid
import math
from datetime import datetime
import re

app = Flask(__name__)

# In-memory store for receipts
receipts_store = {}

def calculate_points(receipt):
    points = 0

    # Rule 1: 1 point for each alphanumeric character in retailer name
    points += sum(c.isalnum() for c in receipt["retailer"])

    # Rule 2: 50 points if total is a round dollar amount
    total = float(receipt["total"])
    if total.is_integer():
        points += 50

    # Rule 3: 25 points if total is a multiple of 0.25
    if total % 0.25 == 0:
        points += 25

    # Rule 4: 5 points for every two items
    points += (len(receipt["items"]) // 2) * 5

    # Rule 5: Item description length multiple of 3
    for item in receipt["items"]:
        desc_length = len(item["shortDescription"].strip())
        if desc_length % 3 == 0:
            price = float(item["price"])
            points += math.ceil(price * 0.2)

    # Rule 6: 6 points if purchase day is odd
    purchase_date = datetime.strptime(receipt["purchaseDate"], "%Y-%m-%d")
    if purchase_date.day % 2 == 1:
        points += 6

    # Rule 7: 10 points if time is between 2:00 PM and 4:00 PM
    purchase_time = datetime.strptime(receipt["purchaseTime"], "%H:%M")
    if 14 <= purchase_time.hour < 16:
        points += 10

    return points


def validate_receipt(receipt):
    required_fields = {"retailer", "purchaseDate", "purchaseTime", "total", "items"}

    if not isinstance(receipt, dict) or not required_fields.issubset(receipt.keys()):
        return "Missing required fields."

    if not re.match(r"^[\w\s\-&]+$", receipt["retailer"]):
        return "Invalid retailer name format."

    try:
        datetime.strptime(receipt["purchaseDate"], "%Y-%m-%d")
    except ValueError:
        return "Invalid purchaseDate format. Expected YYYY-MM-DD."

    try:
        datetime.strptime(receipt["purchaseTime"], "%H:%M")
    except ValueError:
        return "Invalid purchaseTime format. Expected HH:MM."

    if not re.match(r"^\d+\.\d{2}$", receipt["total"]):
        return "Invalid total format. Expected decimal with two places."

    if not isinstance(receipt["items"], list) or len(receipt["items"]) < 1:
        return "Items must be a non-empty list."

    for item in receipt["items"]:
        if (
            not isinstance(item, dict)
            or "shortDescription" not in item
            or "price" not in item
        ):
            return "Each item must have shortDescription and price."
        if not re.match(r"^[\w\s\-]+$", item["shortDescription"]):
            return "Invalid shortDescription format."
        if not re.match(r"^\d+\.\d{2}$", item["price"]):
            return "Invalid price format for item. Expected decimal with two places."

    return None


@app.route("/receipts/process", methods=["POST"])
def process_receipt():
    try:
        receipt = request.get_json()
        validation_error = validate_receipt(receipt)
        if validation_error:
            return jsonify({"error": validation_error}), 400

        receipt_id = str(uuid.uuid4())
        points = calculate_points(receipt)
        receipts_store[receipt_id] = points
        return jsonify({"id": receipt_id})
    except Exception:
        return jsonify({"error": "Invalid receipt data."}), 400


@app.route("/receipts/<receipt_id>/points", methods=["GET"])
def get_points(receipt_id):
    if receipt_id in receipts_store:
        return jsonify({"points": receipts_store[receipt_id]})
    else:
        return jsonify({"error": "No receipt found for that ID."}), 404


if __name__ == "__main__":
    app.run(debug=True)
