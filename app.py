from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Length, Optional
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
# Linking table for the many-to-many relationship between debates and categories
debate_category = db.Table('debate_category',
    db.Column('debate_id', db.Integer, db.ForeignKey('debate.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    bio = db.Column(db.String(140))  # Optional short bio
    profile_image_url = db.Column(db.String(255))  # Optional profile image URL
    arguments = db.relationship('Argument', backref='author', lazy=True)

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[Length(min=2, max=20)])
    bio = StringField('Bio', validators=[Length(max=140), Optional()])
    submit = SubmitField('Update')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    debates = db.relationship('Debate', secondary='debate_category', backref=db.backref('categories', lazy='dynamic'))

class DebateSide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    side = db.Column(db.String(100), nullable=False)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Debate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    sides = db.relationship('DebateSide', backref='debate', lazy=True)

class Argument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    debate_id = db.Column(db.Integer, db.ForeignKey('debate.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        debates = Debate.query.all()
        return render_template('index.html', debates=debates)
    else:
        return redirect(url_for('login'))

@app.route('/debate/<int:debate_id>/waiting_room')
@login_required
def waiting_room(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    sides = DebateSide.query.filter_by(debate_id=debate_id).all()
    # Check if both sides have users
    if all(side.user_id for side in sides):
        return redirect(url_for('debate_room', debate_id=debate_id))
    return render_template('waiting_room.html', debate=debate)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        # Use default method for password hashing
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('home'))  # Redirect to the list of debates
        flash('Invalid login credentials.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/create_debate', methods=['GET', 'POST'])
def create_debate():
    if request.method == 'POST':
        title = request.form['title']
        side1 = request.form['side1']
        side2 = request.form['side2']

        new_debate = Debate(title=title)
        db.session.add(new_debate)
        db.session.commit()

        # Create sides for the debate
        new_side1 = DebateSide(side=side1, debate_id=new_debate.id)
        new_side2 = DebateSide(side=side2, debate_id=new_debate.id)
        db.session.add_all([new_side1, new_side2])
        db.session.commit()

        flash('Debate created successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('create_debate.html')


@app.route('/debate/<int:debate_id>', methods=['GET', 'POST'])
def debate(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form.get('content')
        if content:
            argument = Argument(content=content, user_id=current_user.id, debate_id=debate_id)
            db.session.add(argument)
            db.session.commit()
            flash('Your argument has been added!', 'success')
        else:
            flash('Argument cannot be empty.', 'danger')
    arguments = Argument.query.filter_by(debate_id=debate_id).all()
    return render_template('debate.html', debate=debate, arguments=arguments)

@app.route('/user/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_profile.html', user=user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('user_profile', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.bio.data = current_user.bio
    return render_template('edit_profile.html', form=form)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()  # Prevents any failed database sessions from hanging around
    return render_template('500.html'), 500

@app.route('/debate/<int:debate_id>/join', methods=['GET', 'POST'])
def join_debate(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    if request.method == 'POST':
        selected_side_id = request.form.get('selected_side')
        if selected_side_id:
            # Check if the side is already taken
            side = DebateSide.query.filter_by(id=selected_side_id).first()
            if not side.user_id:  # assuming the DebateSide model has a user_id field to track if it's taken
                side.user_id = current_user.id
                db.session.commit()
                flash('You have joined the debate!', 'success')
                return redirect(url_for('waiting_room', debate_id=debate.id))
            else:
                flash('This side is already taken.', 'danger')
    sides = DebateSide.query.filter_by(debate_id=debate_id).all()
    return render_template('join_debate.html', debate=debate, sides=sides)

@app.route('/check_debate_status/<int:debate_id>')
def check_debate_status(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    sides = DebateSide.query.filter_by(debate_id=debate_id).all()
    if all(side.user_id for side in sides):
        return {'status': 'ready', 'message': 'Both sides have joined the debate.'}
    else:
        return {'status': 'waiting', 'message': 'Waiting for participants on both sides.'}

# Flask route for the debate room
@app.route('/debate_room/<int:debate_id>')
@login_required
def debate_room(debate_id):
    debate = Debate.query.get_or_404(debate_id)
    return render_template('debate_room.html', debate=debate)

@socketio.on('join_room')
def handle_join_room(data):
    join_room(data['room'])
    # Check if both sides are filled and emit an update
    debate = Debate.query.get(data['room'])
    if debate.is_ready():  # You will need to implement this method
        emit('update', {'status': 'ready'}, room=data['room'])


if __name__ == '__main__':
    app.run(debug=True)