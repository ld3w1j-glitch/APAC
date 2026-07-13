from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('portal', __name__)

@bp.route('/portal')
@login_required
def index():
    return render_template('portal/index.html')
