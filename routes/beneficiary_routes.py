from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from __init__ import db
from models import Beneficiary

bp = Blueprint('beneficiary', __name__, url_prefix='/api/beneficiaries')


@bp.route('', methods=['GET', 'POST'])
@jwt_required()
def beneficiaries():
    """Get all beneficiaries or create new one"""
    try:
        current_user_id = get_jwt_identity()

        if request.method == 'GET':
            beneficiaries = Beneficiary.query.filter_by(user_id=current_user_id).all()
            return jsonify({
                'success': True,
                'beneficiaries': [b.to_dict() for b in beneficiaries]
            }), 200

        # POST - Create new beneficiary
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        wallet_id = data.get('wallet_id')

        if not all([name, email, wallet_id]):
            return jsonify({'error': 'Name, email, and wallet number are required'}), 400

        beneficiary = Beneficiary(
            user_id=current_user_id,
            name=name.strip(),
            email=email.lower().strip(),
            wallet_id=wallet_id.strip(),
            relationship=data.get('relationship', '').strip() if data.get('relationship') else None
        )

        db.session.add(beneficiary)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Beneficiary added successfully',
            'beneficiary': beneficiary.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error in beneficiaries: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:beneficiary_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def beneficiary_detail(beneficiary_id):
    """Get, update or delete beneficiary"""
    try:
        current_user_id = get_jwt_identity()
        beneficiary = Beneficiary.query.get(beneficiary_id)
        
        if not beneficiary:
            return jsonify({'error': 'Beneficiary not found'}), 404
        
        # Check ownership
        if beneficiary.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'beneficiary': beneficiary.to_dict()
            }), 200
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            if 'name' in data:
                beneficiary.name = data['name'].strip()
            if 'email' in data:
                beneficiary.email = data['email'].lower().strip()
            if 'wallet_id' in data:
                beneficiary.wallet_id = data['wallet_id'].strip() if data['wallet_id'] else None
            if 'relationship' in data:
                beneficiary.relationship = data['relationship'].strip() if data['relationship'] else None
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Beneficiary updated successfully',
                'beneficiary': beneficiary.to_dict()
            }), 200
        
        elif request.method == 'DELETE':
            db.session.delete(beneficiary)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Beneficiary deleted successfully'
            }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in beneficiary_detail: {str(e)}")
        return jsonify({'error': str(e)}), 500