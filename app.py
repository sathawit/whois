# app.py

from flask import Flask, render_template, request, flash, jsonify, redirect, url_for # Import redirect and url_for
import whois
from datetime import datetime
from config import Config
from database import db, WhoisRecord

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Function to parse WHOIS data (keep this as is)
def parse_whois_data(w_object):
    """Parses whois object for storing key details."""
    if not w_object:
        return None, None, None, None

    registrar = getattr(w_object, 'registrar', None)
    creation_date = getattr(w_object, 'creation_date', None)
    expiration_date = getattr(w_object, 'expiration_date', None)

    # Handle lists of dates, take the first one if multiple
    if isinstance(creation_date, list) and creation_date:
        creation_date = creation_date[0]
    if isinstance(expiration_date, list) and expiration_date:
        expiration_date = expiration_date[0]

    return (
        registrar,
        str(creation_date) if creation_date else None,
        str(expiration_date) if expiration_date else None,
        str(w_object) # Store full raw text
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    whois_info_display = None
    domain_searched = None
    historical_records = WhoisRecord.query.order_by(WhoisRecord.last_updated.desc()).limit(10).all()

    if request.method == 'POST':
        domain = request.form.get('domain', '').strip()
        domain_searched = domain

        if not domain:
            flash('Please enter a domain name.', 'danger')
            current_year = datetime.utcnow().year
            return render_template('index.html', domain_searched=domain_searched, historical_records=historical_records, current_year=current_year)

        try:
            w = whois.whois(domain)

            if w is None or not w.registrar:
                flash(f"WHOIS information not found or lookup failed for '{domain}'. It might not exist, be misspelled, or the WHOIS server is unreachable.", 'warning')
                whois_info_display = "No WHOIS information found for this domain."
            else:
                registrar, creation_date_str, expiration_date_str, full_whois_text = parse_whois_data(w)

                # Store or update in database
                record = WhoisRecord.query.filter_by(domain_name=domain).first()
                if record:
                    record.registrar = registrar
                    record.creation_date = creation_date_str
                    record.expiration_date = expiration_date_str
                    record.full_whois_text = full_whois_text
                    # last_updated is automatically updated
                else:
                    record = WhoisRecord(
                        domain_name=domain,
                        registrar=registrar,
                        creation_date=creation_date_str,
                        expiration_date=expiration_date_str,
                        full_whois_text=full_whois_text
                    )
                    db.session.add(record)
                db.session.commit()
                flash(f"Successfully looked up and saved '{domain}'.", 'success')

                # Prepare info for display
                whois_info_dict = {}
                for key in dir(w):
                    if not key.startswith('_') and key not in ['get', 'pop', 'items', 'keys', 'values', 'update', 'setdefault', 'clear', 'copy']:
                        try:
                            value = getattr(w, key)
                            if value:
                                whois_info_dict[key] = value
                        except Exception as e:
                            print(f"Error getting attribute {key}: {e}")

                if whois_info_dict:
                    formatted_info = ""
                    for key, value in whois_info_dict.items():
                        display_key = key.replace('_', ' ').title()
                        if isinstance(value, list):
                            formatted_info += f"{display_key}:\n"
                            for item in value:
                                formatted_info += f"  - {item}\n"
                        else:
                            formatted_info += f"{display_key}: {value}\n"
                    whois_info_display = formatted_info
                else:
                    whois_info_display = str(w) # Fallback to raw string

        except whois.parser.WhoisComaNotImplemented as e:
            flash(f"WHOIS lookup not implemented for this TLD ({domain.split('.')[-1].upper()}).", 'danger')
            whois_info_display = f"Error: WHOIS lookup not supported for this domain's TLD ({domain.split('.')[-1].upper()})."
        except Exception as e:
            flash(f"An unexpected error occurred during WHOIS lookup for '{domain}'. Please try again.", 'danger')
            whois_info_display = "An unexpected error occurred."
            print(f"Detailed error for '{domain}': {e}") # Log full error for debugging

        historical_records = WhoisRecord.query.order_by(WhoisRecord.last_updated.desc()).limit(10).all()

    current_year = datetime.utcnow().year
    return render_template('index.html', whois_info=whois_info_display, domain_searched=domain_searched,
                           historical_records=historical_records, current_year=current_year)

# NEW ROUTE TO CLEAR HISTORY
@app.route('/clear_history', methods=['POST'])
def clear_history():
    try:
        num_deleted = db.session.query(WhoisRecord).delete()
        db.session.commit()
        flash(f'Successfully cleared {num_deleted} historical records.', 'success')
    except Exception as e:
        db.session.rollback() # Rollback on error
        flash(f'Error clearing history: {e}', 'danger')
        print(f"Error clearing history: {e}") # Log for server-side debugging
    return redirect(url_for('index')) # Redirect back to the home page

@app.route('/api/whois/<domain_name>', methods=['GET'])
def api_whois(domain_name):
    if not domain_name:
        return jsonify({"error": "Domain name is required."}), 400

    try:
        w = whois.whois(domain_name)
        if w is None or not w.registrar:
            return jsonify({"error": f"WHOIS information not found for '{domain_name}'."}), 404
        
        # Convert whois object to a dictionary for JSON output
        whois_data = {}
        for key in dir(w):
            if not key.startswith('_') and not callable(getattr(w, key)):
                value = getattr(w, key)
                if value:
                    if isinstance(value, datetime):
                        whois_data[key] = value.isoformat()
                    elif isinstance(value, list) and all(isinstance(item, datetime) for item in value):
                        whois_data[key] = [item.isoformat() for item in value]
                    else:
                        whois_data[key] = value
        
        return jsonify(whois_data), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)