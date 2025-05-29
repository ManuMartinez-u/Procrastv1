from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Task
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_segura')

# Config SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///procrastinacion.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('panel_control'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password or not confirm_password:
            error = 'Todos los campos son obligatorios.'
        elif password != confirm_password:
            error = 'Las contraseñas no coinciden.'
        else:
            # Revisar si existe usuario con ese nombre
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                error = 'El nombre de usuario ya existe.'
            else:
                # Crear usuario nuevo con contraseña hasheada
                hashed_password = generate_password_hash(password)
                new_user = User(username=username, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()

                flash('Registro exitoso, ahora puedes iniciar sesión.')
                return redirect(url_for('login'))

    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Bienvenido, ' + user.username, 'success')
            return redirect(url_for('panel_control'))
        flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

@app.route('/panel', methods=['GET', 'POST'])
def panel_control():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']

    filter_status = request.args.get('filter', 'all')
    search_query = request.args.get('search', '').strip()

    query = Task.query.filter_by(user_id=user_id)

    if filter_status == 'completed':
        query = query.filter_by(completed=True)
    elif filter_status == 'pending':
        query = query.filter_by(completed=False)
    elif filter_status == 'important':
        query = query.filter_by(important=True)

    if search_query:
        query = query.filter(Task.task.contains(search_query))

    tasks = query.order_by(Task.created_at.desc()).all()

    return render_template('panel_control.html', username=session['username'], tasks=tasks, filter_status=filter_status, search_query=search_query)

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task_text = request.form['task'].strip()
    if task_text:
        new_task = Task(task=task_text, user_id=session['user_id'], created_at=datetime.utcnow())
        db.session.add(new_task)
        db.session.commit()
        flash('Tarea agregada con éxito.', 'success')
    return redirect(url_for('panel_control'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    task.completed = True
    task.completed_at = datetime.utcnow()
    db.session.commit()
    flash('Tarea marcada como completada.', 'success')
    return redirect(url_for('panel_control'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash('Tarea eliminada.', 'success')
    return redirect(url_for('panel_control'))

@app.route('/toggle_important_task/<int:task_id>')
def toggle_important_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    task.important = not task.important
    db.session.commit()
    flash(f"Tarea {'marcada como importante' if task.important else 'desmarcada como importante'}.", 'info')
    return redirect(url_for('panel_control'))

@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    new_task_text = request.form.get('task', '').strip()
    if not new_task_text:
        flash('El texto de la tarea no puede estar vacío.', 'warning')
        return redirect(url_for('panel_control'))

    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    task.task = new_task_text
    db.session.commit()
    flash('Tarea actualizada.', 'success')
    return redirect(url_for('panel_control'))

@app.route('/report')
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    total = Task.query.filter_by(user_id=user_id).count()
    completed = Task.query.filter_by(user_id=user_id, completed=True).count()
    pending = total - completed
    important = Task.query.filter_by(user_id=user_id, important=True).count()
    return render_template('report.html', username=session['username'], total=total, completed=completed, pending=pending, important=important)
    
if __name__ == '__main__':
    app.run(debug=True)
