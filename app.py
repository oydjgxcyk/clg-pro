from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Task 3.1 — Graceful qrcode import
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("WARNING: qrcode package not installed. QR generation disabled.")

# Task 3.2 — Remove template_folder; keep static_folder
app = Flask(__name__, static_folder='static')

# CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///doms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'doms_secret_key'

CORS(app)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Task 3.2 — Ensure static/qr directory always exists at module level
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'qr'), exist_ok=True)


# =========================
# DATABASE MODELS
# =========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(50))
    department = db.Column(db.String(100))


class OutpassRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_name = db.Column(db.String(100))
    roll_number = db.Column(db.String(50))
    department = db.Column(db.String(100))

    reason = db.Column(db.String(300))
    destination = db.Column(db.String(200))

    exit_time = db.Column(db.String(100))
    return_time = db.Column(db.String(100))

    attendance = db.Column(db.Float)

    mentor_status = db.Column(db.String(20), default='Pending')
    parent_status = db.Column(db.String(20), default='Pending')
    hod_status = db.Column(db.String(20), default='Pending')
    dean_status = db.Column(db.String(20), default='Pending')

    final_status = db.Column(db.String(20), default='Pending')

    # Task 3.3 — Add created_at timestamp column
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# PAGE ROUTES (serve HTML dashboards)
# =========================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/student')
def student_page():
    return send_from_directory('.', 'student_dashboard.html')

@app.route('/mentor')
def mentor_page():
    return send_from_directory('.', 'mentor_dashboard.html')

@app.route('/parent')
def parent_page():
    return send_from_directory('.', 'parent_dashboard.html')

@app.route('/hod')
def hod_page():
    return send_from_directory('.', 'hod_dashboard.html')

@app.route('/dean')
def dean_page():
    return send_from_directory('.', 'dean_dashboard.html')

@app.route('/security')
def security_page():
    return send_from_directory('.', 'security_dashboard.html')


# =========================
# AUTHENTICATION
# =========================

@app.route('/register', methods=['POST'])
def register():
    data = request.json

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered'}), 409

    hashed_password = generate_password_hash(data['password'])

    user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password,
        role=data['role'],
        department=data.get('department', '')
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User Registered Successfully'})


@app.route('/login', methods=['POST'])
def login():
    data = request.json

    user = User.query.filter_by(email=data['email']).first()

    if user and check_password_hash(user.password, data['password']):
        # identity must be a string for flask-jwt-extended >= 4.x
        token = create_access_token(identity=str(user.id), additional_claims={
            'name': user.name,
            'role': user.role
        })

        return jsonify({
            'token': token,
            'role': user.role,
            'name': user.name
        })

    return jsonify({'message': 'Invalid Credentials'}), 401


# =========================
# STUDENT ROUTES
# =========================

@app.route('/apply-outpass', methods=['POST'])
def apply_outpass():
    data = request.json

    new_request = OutpassRequest(
        student_name=data['student_name'],
        roll_number=data['roll_number'],
        department=data.get('department', ''),
        reason=data['reason'],
        destination=data['destination'],
        exit_time=data['exit_time'],
        return_time=data['return_time'],
        attendance=float(data.get('attendance', 75))
    )

    db.session.add(new_request)
    db.session.commit()

    return jsonify({'message': 'Outpass Request Submitted', 'id': new_request.id})


@app.route('/student-requests', methods=['GET'])
def student_requests():
    roll = request.args.get('roll_number', '')
    if roll:
        requests_list = OutpassRequest.query.filter_by(roll_number=roll).all()
    else:
        requests_list = OutpassRequest.query.all()

    data = []
    for r in requests_list:
        data.append({
            'id': r.id,
            'student_name': r.student_name,
            'roll_number': r.roll_number,
            'reason': r.reason,
            'destination': r.destination,
            'exit_time': r.exit_time,
            'return_time': r.return_time,
            'mentor_status': r.mentor_status,
            'parent_status': r.parent_status,
            'hod_status': r.hod_status,
            'dean_status': r.dean_status,
            'status': r.final_status,
            # Task 3.3 — Include created_at in serialized output
            'created_at': r.created_at.isoformat() if r.created_at else None
        })

    return jsonify(data)


# Task 3.4 — Add GET /student/profile route
@app.route('/student/profile', methods=['GET'])
def student_profile():
    roll = request.args.get('roll_number', '')
    reqs = OutpassRequest.query.filter_by(roll_number=roll).all()
    avg_att = round(sum(r.attendance for r in reqs) / len(reqs), 1) if reqs else 75.0
    dept = reqs[0].department if reqs else ''
    name = reqs[0].student_name if reqs else roll
    return jsonify({
        'name': name,
        'roll_number': roll,
        'department': dept,
        'attendance': avg_att
    })


# =========================
# MENTOR ROUTES
# =========================

@app.route('/mentor/pending', methods=['GET'])
def mentor_pending():
    requests_list = OutpassRequest.query.filter_by(mentor_status='Pending').all()

    data = []
    for r in requests_list:
        risk = 'SAFE'
        if r.attendance < 75:
            risk = 'HIGH RISK'
        elif r.attendance < 85:
            risk = 'WARNING'

        data.append({
            'id': r.id,
            'student_name': r.student_name,
            'roll_number': r.roll_number,
            'department': r.department,
            'reason': r.reason,
            'destination': r.destination,
            'exit_time': r.exit_time,
            'return_time': r.return_time,
            'attendance': r.attendance,
            'risk': risk
        })

    return jsonify(data)


@app.route('/mentor/approve/<int:id>', methods=['PUT'])
def mentor_approve(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404

    req.mentor_status = 'Approved'
    db.session.commit()

    return jsonify({'message': 'Approved By Mentor'})


@app.route('/mentor/reject/<int:id>', methods=['PUT'])
def mentor_reject(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404

    req.mentor_status = 'Rejected'
    req.final_status = 'Rejected'
    db.session.commit()

    return jsonify({'message': 'Rejected By Mentor'})


# =========================
# PARENT ROUTES
# =========================

@app.route('/parent/pending', methods=['GET'])
def parent_pending():
    requests_list = OutpassRequest.query.filter_by(
        mentor_status='Approved',
        parent_status='Pending'
    ).all()

    data = []
    for r in requests_list:
        data.append({
            'id': r.id,
            'student_name': r.student_name,
            'roll_number': r.roll_number,
            'department': r.department,
            'reason': r.reason,
            'destination': r.destination,
            'exit_time': r.exit_time,
            'return_time': r.return_time,
            'attendance': r.attendance
        })

    return jsonify(data)


@app.route('/parent/approve/<int:id>', methods=['PUT'])
def parent_approve(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404

    req.parent_status = 'Approved'
    db.session.commit()

    return jsonify({'message': 'Approved By Parent'})


@app.route('/parent/reject/<int:id>', methods=['PUT'])
def parent_reject(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404

    req.parent_status = 'Rejected'
    req.final_status = 'Rejected'
    db.session.commit()

    return jsonify({'message': 'Rejected By Parent'})


# =========================
# HOD ROUTES
# =========================

@app.route('/hod/pending', methods=['GET'])
def hod_pending():
    requests_list = OutpassRequest.query.filter_by(
        parent_status='Approved',
        hod_status='Pending'
    ).all()

    data = []
    for r in requests_list:
        data.append({
            'id': r.id,
            'student_name': r.student_name,
            'roll_number': r.roll_number,
            'department': r.department,
            'reason': r.reason,
            'destination': r.destination,
            'exit_time': r.exit_time,
            'return_time': r.return_time,
            'attendance': r.attendance
        })

    return jsonify(data)


@app.route('/hod/approve/<int:id>', methods=['PUT'])
def hod_approve(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404

    req.hod_status = 'Approved'
    db.session.commit()

    return jsonify({'message': 'Approved By HOD'})


@app.route('/hod/reject/<int:id>', methods=['PUT'])
def hod_reject(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404

    req.hod_status = 'Rejected'
    req.final_status = 'Rejected'
    db.session.commit()

    return jsonify({'message': 'Rejected By HOD'})


# =========================
# DEAN ROUTES
# =========================

@app.route('/dean/pending', methods=['GET'])
def dean_pending():
    requests_list = OutpassRequest.query.filter_by(
        hod_status='Approved',
        dean_status='Pending'
    ).all()

    data = []
    for r in requests_list:
        data.append({
            'id': r.id,
            'student_name': r.student_name,
            'roll_number': r.roll_number,
            'department': r.department,
            'reason': r.reason,
            'destination': r.destination,
            'exit_time': r.exit_time,
            'return_time': r.return_time,
            'attendance': r.attendance,
            'mentor_status': r.mentor_status,
            'parent_status': r.parent_status,
            'hod_status': r.hod_status,
            # Task 3.3 — Include created_at in dean_pending serialized output
            'created_at': r.created_at.isoformat() if r.created_at else None
        })

    return jsonify(data)


@app.route('/dean/approve/<int:id>', methods=['PUT'])
def dean_approve(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404

    req.dean_status = 'Approved'
    req.final_status = 'Approved'

    # Task 3.1 — Guard QR generation with QR_AVAILABLE flag
    if QR_AVAILABLE:
        qr_data = f"{req.student_name}-{req.roll_number}-{req.id}"
        qr = qrcode.make(qr_data)

        qr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'qr')
        os.makedirs(qr_dir, exist_ok=True)
        qr_filename = f"qr_{req.id}.png"
        qr.save(os.path.join(qr_dir, qr_filename))

        db.session.commit()

        return jsonify({
            'message': 'Final Approval Completed',
            'qr_file': f'/static/qr/{qr_filename}'
        })

    db.session.commit()

    return jsonify({
        'message': 'Final Approval Completed',
        'qr_file': None
    })


# Task 3.5 — Add PUT /dean/reject/<id> route
@app.route('/dean/reject/<int:id>', methods=['PUT'])
def dean_reject(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404
    req.dean_status = 'Rejected'
    req.final_status = 'Rejected'
    db.session.commit()
    return jsonify({'message': 'Rejected By Dean'})


# =========================
# SECURITY/WARDEN ROUTES
# =========================

@app.route('/security/verify/<int:id>', methods=['GET'])
def verify_qr(id):
    req = db.session.get(OutpassRequest, id)

    if req and req.final_status == 'Approved':
        return jsonify({
            'status': 'VALID',
            'student_name': req.student_name,
            'roll_number': req.roll_number,
            'destination': req.destination,
            'exit_time': req.exit_time,
            'return_time': req.return_time
        })

    return jsonify({'status': 'INVALID'})


# Task 3.6 — Add GET /security/stats route
@app.route('/security/stats', methods=['GET'])
def security_stats():
    outside = OutpassRequest.query.filter_by(final_status='Approved').count()
    rejected = OutpassRequest.query.filter_by(final_status='Rejected').count()
    total = OutpassRequest.query.count()
    pending = total - outside - rejected
    return jsonify({
        'outside_count': outside,
        'approved_count': outside,
        'rejected_count': rejected,
        'pending_count': pending
    })


# =========================
# DASHBOARD ANALYTICS
# =========================

# Task 3.7 — Add optional ?department= filter to GET /analytics
@app.route('/analytics', methods=['GET'])
def analytics():
    dept = request.args.get('department', '')
    if dept:
        query = OutpassRequest.query.filter_by(department=dept)
    else:
        query = OutpassRequest.query

    total = query.count()
    approved = query.filter_by(final_status='Approved').count()
    rejected = query.filter_by(final_status='Rejected').count()
    pending = total - approved - rejected

    return jsonify({
        'total_requests': total,
        'approved_requests': approved,
        'rejected_requests': rejected,
        'pending_requests': pending
    })


# =========================
# MAIN
# =========================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)
