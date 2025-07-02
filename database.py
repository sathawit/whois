from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class WhoisRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    registrar = db.Column(db.String(255))
    creation_date = db.Column(db.String(255)) # Store as string for flexibility
    expiration_date = db.Column(db.String(255)) # Store as string for flexibility
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    full_whois_text = db.Column(db.Text) # To store the raw WHOIS output

    def __repr__(self):
        return f"<WhoisRecord {self.domain_name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'domain_name': self.domain_name,
            'registrar': self.registrar,
            'creation_date': self.creation_date,
            'expiration_date': self.expiration_date,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'full_whois_text': self.full_whois_text
        }