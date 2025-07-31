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
import bleach
import uuid
import os
import secrets
import random

app = Flask(__name__)


#setting images per page in gallery
IMAGES_PER_PAGE = 20

#cleaning HTML in input using bleach
ALLOWED_TAGS = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'p',
    'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'img', 'div',
    'span', 'pre', 'code']

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'width', 'height', 'style', 'class'],
    'div': ['class'],
    'span': ['class']
}

def sanitize_html(html_content):
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
        strip_comments=True
    )
#rendering of html for preview
def render_content_for_preview(text_content):
    rendered_html = sanitize_html(text_content)
    return rendered_html

#IMG UPLOAD PATH CONFIG
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'jpg', 'png', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024

#db: setting and initializing
app.config['SECRET_KEY'] = 'DEV_SECRET_KEY_123'
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///db.sqlite'
app.config["SQLITE_TRACK_MODIFICATIONS"] = False
app.config['REGISTRATION_SECRET_TOKEN'] = "MY_SECRET_TOKEN"

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    image_file = db.Column(db.String(28), nullable=True, default=None)
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
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    username = db.Column(db.String(28), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_picture = db.Column(db.String(50), nullable=False, default='default.png')
    role = db.Column(db.String(20), default="contributor", nullable=False)
    bio = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(255), nullable=True)
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
    if not allowed_file(form_picture.filename):
        raise ValueError('File type not allowed.')
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
    search_query = request.args.get('q', type=str)
    
    if search_query:
        posts = Post.query.filter(
            (Post.title.ilike(f'%{search_query}%')) |
            (Post.content.ilike(f'%{search_query}%'))
        ).order_by(Post.creation_date.desc()).paginate(page=page, per_page=5)
        return render_template('index.html', posts=posts, search_query=search_query)
    else:
        posts = Post.query.order_by(Post.creation_date.desc()).paginate(page=page, per_page=5)
        return render_template('index.html', posts=posts, search_query="")

@app.route('/register', methods=['GET', 'POST'])
def register():
    expected_token = current_app.config.get("REGISTRATION_SECRET_TOKEN")
    provided_token = request.args.get('token')
    
    if not expected_token:
        current_app.logger.error('REGISTRATION_SECRET_TOKEN is not set in app configuration')
        flash('Registration is currently unavailable due to a configuration error', 'danger')
        return redirect(url_for('index'))
    
    if not provided_token or provided_token != expected_token:
        flash('Access denied. Invalid or missing registration token', 'danger')
        return redirect(url_for('login'))
        
    if current_user.is_authenticated:
        flash('You are already logged in', 'info')
        return redirect(url_for('index'))
    
    if request.method=='POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        #basics checks
        if not username or not email or not password or not confirm_password:
            flash('All fields are mandatory', 'error')
            return redirect(url_for('register', token = provided_token))
        
        if password != confirm_password:
            flash('Passwords are not matching, try again', 'error')
            return redirect(url_for('register', token = provided_token))
        
        if User.query.filter_by(username=username).first():
            flash('This username already exists', 'error')
            return redirect(url_for('register', token = provided_token))
        
        if User.query.filter_by(email=email).first():
            flash('This email already exists', 'error')
            return redirect(url_for('register', token = provided_token))
        
        try:  
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Your account has been created!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error during user registration {e}')
            flash('An error occurred during registration. Pleaase, try again', ' error')
            return redirect(url_for('register', token = provided_token))           
    
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
            if user.is_banned:
                flash('Your account has been suspended. Please, contact the administrator.', 'Error')
            else:
                login_user(user, remember=remember)
                flash('Successfully logged in!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Access denied. Check email and password', 'error')

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
        
        # picture_file = 'default.jpg'
        new_post_image_file = None
        
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
                        new_post_image_file = save_picture(picture)
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
            sanitized_content = sanitize_html(content)
            new_post = Post(
                title=title,
                content=sanitized_content,
                author=current_user,
                creation_date=datetime.now(),
                image_file=new_post_image_file
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
            current_app.logger.error(f'Error during the creation of post: {e}')
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
    post_to_delete = Post.query.get_or_404(post_id)
    
    if post_to_delete.user_id != current_user.id and not current_user.is_admin:
        flash('Non hai il permesso per cancellare questo post', 'danger')
        return redirect(url_for('dashboard'))

    try:

        tags_associated_with_post = list(post_to_delete.tags) 

        db.session.delete(post_to_delete)
        db.session.commit() 


        for tag in tags_associated_with_post:

            if tag.posts.count() == 0: 
                db.session.delete(tag)
        
        db.session.commit() 
        flash('Il post è stato cancellato con successo!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash('Errore durante la cancellazione', 'error')
        print(f'Errore durante la cancellazione di {post_id}: {e}')
        return 'Error during the elimination of the content', 500

    
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
        content = request.form.get('content')
        tags_string = request.form.get('tags_input', '')
        
        sanitized_content = sanitize_html(content)
        
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
                        flash('Error while uploading the image.', 'error')
                        current_tags = ', '.join([t.tag_name for t in post.tags])
                        return render_template('edit_post.html', title = 'Edit post',
                                               post=post, current_tags=current_tags)
                
                else:
                    flash('File type not allowed (accepting: jpg, jpeg, png, gif, webp)', 'danger')
                    current_tags = ', '.join([t.tag_name for t in post.tags])
                    return render_template('edit_post.html', title = 'Edit post',
                                               post=post, current_tags=current_tags)
        
        post.content = sanitized_content
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
            current_app.logger.error(f'Error during updating the post {post.id}: {e}')
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


#____about___ (for now a static page)
@app.route('/about')
def about():
    authors = User.query.all()
    return render_template("about.html", authors=authors)


#___preview post___ !!!!!! TO CHECK
@app.route('/preview_post', methods=["POST"])
def preview_post():
    title = request.form.get('post_title') or request.form.get('title')
    content = request.form.get('text_content') or request.form.get('content')
    rendered_preview_content = render_content_for_preview(content)
    author = current_user.username
    return render_template('post_preview.html', title=title, content_html=rendered_preview_content, author=author)


#___gallery___
@app.route('/gallery', methods=['GET', 'POST'])
@login_required
def gallery():
    if request.method == 'POST':
        if 'image_file' not in request.files:
            flash('No images selected', 'danger')
            return redirect(url_for('gallery'))
        
        file = request.files['image_file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('gallery'))
            
        try:
            filename = save_picture(file)
            flash(f'Image {filename} successfully uploaded!', 'success')
        except Exception as e:
            flash(f'An unexpected error occurred during the upload {e}', 'danger')
        return redirect(url_for('gallery'))
    
    all_image_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            all_image_files.append(filename)
            
    all_image_files.sort(reverse=True)
    
    page = request.args.get('page', 1, type=int)
    
    total_images = len(all_image_files)
    total_pages = (total_images + IMAGES_PER_PAGE -1) // IMAGES_PER_PAGE
    start_index = (page -1) * IMAGES_PER_PAGE
    end_index = start_index + IMAGES_PER_PAGE
    
    current_page_files = all_image_files[start_index:end_index]
    
    image_files = []
    for filename in current_page_files:
        image_files.append({
            'filename': filename,
            'url': url_for('static', filename='uploads/' + filename)
        })
        
    return render_template('gallery.html', image_files=image_files, title='File manager', page=page,
                           total_pages=total_pages, total_images=total_images)

#____delete images____
@app.route('/gallery/delete/<string:filename>', methods=['POST'])
@login_required
def delete_uploaded_image(filename):
    if not current_user.is_admin:
        abort(403)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path) and allowed_file(filename):
        try:
            os.remove(file_path)
            flash(f'File {filename} successfully removed!', 'success')
        except Exception as e:
            flash(f'An error occurred during the elimination of the file {e}', 'danger')
    else:
        flash(f'File {filename} not found or extension is not allowed.', 'danger')
    return redirect(url_for('gallery'))

#___user___
@app.route("/user/<username>")
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.creation_date.desc()).all()
    return render_template("user_profile.html", user=user, posts=posts)

#___user edit___
@app.route("/user/<username>/edit", methods=['GET', 'POST'])
def edit_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user != current_user and not current_user.is_admin:
        flash("Denied! You cannot modify this profile!", "danger")
        return redirect(url_for('user_profile', username=username))
    if request.method == 'POST':
        user.bio = request.form['bio']
        user.link = request.form['link']
        
        if current_user.is_admin:
            user.role = request.form['role']
            
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                user.profile_picture = f"uploads/{filename}"
                
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('user_profile', username=user.username))
    return render_template('edit_profile.html', user=user)

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