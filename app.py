from flask import Flask, render_template, url_for, redirect, request, flash, current_app, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from flask_migrate import Migrate
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import secrets
import uuid
import os
import random

app = Flask(__name__)

#IMG UPLOAD PATH CONFIG
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'jpg', 'png', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
app.config['MAX_CONTENT_LENGHT'] = 3 * 1024 * 1024

#db: setting and initializing
app.config['SECRET_KEY'] = 'DEV_SECRET_KEY_123'
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db.sqlite'
app.config["SQLITE_TRACK_MODIFICATIONS"]= False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#______class / models_____
#tags table 
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

#Post model
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_file = db.Column(db.String(28), nullable=True, default='default.jpg')
    tags = db.relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'))
    
    def __repr__(self):
        return f"<Text: {self.id}, title: {self.title}>"

#tag model
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(28), nullable=False, unique=True)
    
    def __repr__(self):
        return f"<Tag: {self.id} named {self.tag_name}>"


#comment model
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime, default=datetime.now())
    
def __repr__(self):
    return f"<Comment id: {self.id} from {self.author}>"
    

#user model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    is_admin = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(28), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    post = db.relationship('Post', backref='author', lazy='dynamic')
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User: {self.username} email: {self.email}'


#contact
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"ContactMessage('{self.name}, {self.subject}, {self.timestamp})"

#_______FUNCTIONS_______

#import img logic
#1) check file extention
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

#save the load image
def save_picture(form_picture):
    random_hex = str(uuid.uuid4())
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_fn)
    form_picture.save(picture_path)
    
    return picture_fn

#______ROUTES_______
@app.route('/')
@app.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.creation_date.desc()).paginate(page=page, per_page=5)
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method=='POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        #basics checks
        if not username or not email or not password or not confirm_password:
            flash('All fields are mandatory', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords are not matching, try again', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('This username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('This email already exists', 'error')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title="Register")

#login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False 
        
        user = User.query.filter_by(email=email).first()
    
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Successfully logged in!', 'success')
        
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Access deniet. Check email and password', 'error')

    return render_template('login.html', title='login')

      
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been disconnected', 'info')
    return redirect(url_for('index'))

#PROTECTED ROUTE -DASHBOARD
@app.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    user_posts = current_user.post.order_by(Post.creation_date.desc()).paginate(page=page, per_page=5)
    return render_template('dashboard.html', title='dashboard', user_posts=user_posts)

@app.route("/post/new", methods=['GET', 'POST'])
@login_required 
def create_post():
    if request.method == 'POST':
        # print(f'DEBUG: request.files content {request.files}') #DEBUG!!!!!!!!
        title = request.form.get('post_title')
        content = request.form.get('text_content')
        tags_string = request.form.get('tags_input', '')
        
        picture_file = 'default.jpg'
        
        if not title:
            flash('Title cannot be empty!', 'error')
            return render_template('create_post.html', title='Crea Post',
                                   post_title=title, post_content=content,
                                   post_tags=tags_string) 
            
        if not content:
            flash('Content cannot be empty', 'error')
            return render_template('create_post.html', title='Crea Post',
                                   post_title=title, post_content=content,
                                   post_tags=tags_string) 
        
        #file uploading logic
        
        if 'post_picture' in request.files:
            picture = request.files['post_picture']
            if picture.filename != '':
                if allowed_file(picture.filename):
                    try:
                        picture_file = save_picture(picture)
                    except Exception as e:
                        flash(f'Error during uploading image: {e}')
                        print(f'Error during uploading file {e}')
                        return render_template('create_post.html', title='Create new post', 
                                               post_title=title, post_content=content,
                                               post_tags=tags_string)
                else:
                    flash('File type not supported (png, jpg, jpeg, gif, webp)', 'error')
                    return render_template('create_post.html', title='Create post',
                                           post_title=title, post_content=content,
                                           post_tags=tags_string)  
    
        
        try:
            new_post = Post(
                title=title,
                content=content,
                author=current_user,
                creation_date=datetime.now(),
                image_file=picture_file
            )
            
            db.session.add(new_post)
            
            tags_list = [tag.strip().lower() for tag in tags_string.split(',') if tag.strip()]
            for tag_name in tags_list:
                tag = Tag.query.filter_by(tag_name=tag_name).first()
                if not tag:
                    tag = Tag(tag_name=tag_name)
                    db.session.add(tag)
                new_post.tags.append(tag)
            
            db.session.commit()
            
            flash('Your post has been successfully added!', 'success')
            return redirect(url_for('view_post', post_id=new_post.id))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred', 'error')
            app.logger.error(f'Error during the creation of post: {e}')
            return render_template('create_post.html', title='Create post', post_title=title, post_content=content, post_tags=tags_string)

    return render_template('create_post.html', title='Create post')

#defining a route for viewing a single text
@app.route('/view/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('view.html', post=post)


#delete post
@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete(post_id):
    if request.method == 'POST':
        try:
            post_to_delete = Post.query.get_or_404(post_id)
            if post_to_delete.user_id != current_user.id and not current_user.is_admin: #try this logic
                flash('You do not have the permission to delete this post', 'danger')
                return redirect(url_for('dashboard'))
        
            db.session.delete(post_to_delete)
            db.session.commit()
            flash('Your post have been successfully deleted!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'error while deleting', 'error')
            print(f'error while deleting {post_id} error {e}')
            return 'Error during the elimination of the content', 500
        
    return redirect(url_for('dashboard'))
    
#edit post
@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have the authorization to edit this post', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # print(f'DEBUG: request.files content {request.files}') #DEBUG!!!!!!!!
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        tags_string = request.form.get('tags_input', '')
        
        
        #image upload logic
        if 'post_picture' in request.files:
            picture = request.files['post_picture']
            
            if picture.filename != '':
                if allowed_file(picture.filename):
                    if post.image_file and post.image_file != 'default.jpg':
                        old_picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.image_file)
                        if os.path.exists(old_picture_path):
                            try:
                                os.remove(old_picture_path)
                                current_app.logger.info(f'Old image {post.image_file} deleted')
                                
                            except OSError as e:
                                current_app.logger.info(f'Error while deleting {post.image_file}: {e}')
                                
                    try:
                        post.image_file = save_picture(picture)
                    except Exception as e:
                        current_app.logger.error(f'error during saving new picture: {e}')
                        flash('Error while uploading the image.')
                        current_tags = ', '.join([t.tag_name for t in post.tags])
                        return render_template('edit_post.html', title = 'Edit post',
                                               post=post, current_tags=current_tags)
                
                else:
                    flash('File type not allowed (accepting: jpg, jpeg, png, gif, webp)', 'danger')
                    current_tags = ', '.join([t.tag_name for t in post.tags])
                    return render_template('edit_post.html', title = 'Edit post',
                                               post=post, current_tags=current_tags)
        
        tags_list = [tag.strip().lower() for tag in tags_string.split(',') if tag.strip()]
        post.tags.clear()
        for tag_name in tags_list:
            tag = Tag.query.filter_by(tag_name=tag_name).first()
            if not tag:
                tag = Tag(tag_name=tag_name)
                db.session.add(tag)
            post.tags.append(tag)
            
        try:
            db.session.commit()
            flash('Your post have been successfully updated!', 'success')
            return redirect(url_for('view_post', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while editing the post: {e}', 'error')
            print(f'Error during the updating {e}')
            return render_template('edit_post.html', title='Edit post', post=post)
    current_tags = ', '.join([tag.tag_name for tag in post.tags])
    return render_template('edit_post.html', title = 'Edit post', post=post, current_tags=current_tags)
    
#route for posts by tags
@app.route('/tag/<string:tag_name>')
def posts_by_tags(tag_name):
    page = request.args.get('page', 1, type=int)
    tag = Tag.query.filter_by(tag_name=tag_name).first_or_404()
    tagged_posts = tag.posts.order_by(Post.creation_date.desc()).paginate(page=page, per_page=5)
    
    return render_template('tagged_post.html', title = f'Post with tag {tag.tag_name}', tag=tag, posts=tagged_posts)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm() 

    if request.method == 'GET':

        session['correct_math_answer'] = form.correct_result

        session['math_num1'] = form.num1
        session['math_num2'] = form.num2
        session['math_operation'] = form.operation
        
    elif form.validate_on_submit():
       
        correct_answer_from_session = session.pop('correct_math_answer', None) # .pop() rimuove la chiave dalla sessione dopo averla letta
        
        user_answer = form.math_question.data
        if correct_answer_from_session is None or user_answer != correct_answer_from_session:
            flash('Incorrect answer to the math question. Please try again.', 'danger')
           
            new_form = ContactForm()
            session['correct_math_answer'] = new_form.correct_result
            session['math_num1'] = new_form.num1
            session['math_num2'] = new_form.num2
            session['math_operation'] = new_form.operation
            return render_template('contact.html', form=new_form)


        new_message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data
        )
        db.session.add(new_message)
        db.session.commit()
        flash('Your message has been sent successfully!', 'success')
     
        session.pop('correct_math_answer', None) 
        session.pop('math_num1', None)
        session.pop('math_num2', None)
        session.pop('math_operation', None)
        return redirect(url_for('contact')) 
    

    return render_template('contact.html', form=form)

#____admin contact messages____
@app.route("/admin/contact_messages")
@login_required
def admin_contact_messages():
    if not current_user.is_admin:
        abort(403) #forbidden
    
    messages = ContactMessage.query.order_by(ContactMessage.timestamp.desc()).all()
    return render_template('admin_contact_messages.html', messages=messages)

#___mark read messages___
@app.route("/admin/contact_messages/<int:message_id>/read", methods=["POST"])
@login_required
def mark_message_read(message_id):
    if not current_user.is_admin:
        abort(403)
    
    message = ContactMessage.query.get_or_404(message_id)
    message.is_read = True
    db.session.commit()
    flash('Message marked as read!', 'success')
    return redirect(url_for("admin_contact_messages"))

#___delete messages___
@app.route("/admin/contact_messages/<int:message_id>/delete", methods=["POST"])
@login_required
def delete_contact_message(message_id):
    if not current_user.is_admin:
        abort(403)
        
    message = ContactMessage.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash('Message deleted successfully!', 'success')
    return redirect(url_for('admin_contact_messages'))
 


#______FORMS______
class ContactForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Your Email', validators=[DataRequired(), Email(), Length(max=120)])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    message = TextAreaField('Your Message', validators=[DataRequired(), Length(min=10, max=1000)])
    
    math_question = IntegerField('Math Question', validators=[DataRequired()]) 
    
    submit = SubmitField('Send Message')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Prova a recuperare i numeri e l'operazione dalla sessione
        # Se non sono in sessione (prima volta che carichi la pagina), generane di nuovi
        self.num1 = session.get('math_num1', random.randint(1, 10))
        self.num2 = session.get('math_num2', random.randint(1, 10))
        self.operation = session.get('math_operation', random.choice(['+', '-']))
        
        # --- avoid negative nums ---
        if self.operation == '-':
            if self.num1 < self.num2:
                self.num1, self.num2 = self.num2, self.num1 # Scambia i valori
            # --- end logic---
        
        if self.operation == '+':
            self.correct_result = self.num1 + self.num2
        else:
            self.correct_result = self.num1 - self.num2
        
        # Aggiorna l'etichetta del campo della domanda matematica
        self.math_question.label.text = f'What is {self.num1} {self.operation} {self.num2}?'


#initializing database
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)