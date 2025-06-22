from flask import Flask, render_template, url_for, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

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
    
#ROUTES
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
        title = request.form.get('post_title')
        content = request.form.get('text_content')
        tags_string = request.form.get('tags_input', '')
        
        if not title or not content:
            flash('Content and title cannot be empty!', 'error')
            return render_template('create_post.html', title='Crea Post') # Ricarica il form con l'errore
            
        if not content:
            flash('This cannot be empty', 'error')
            return render_template('create_post.html', title="Create posts")
        
        new_post = Post(
            title=title,
            content=content,
            author=current_user,
            creation_date=datetime.now()
        )
        
        try:
            new_post = Post(
                title=title,
                content=content,
                author=current_user,
                creation_date=datetime.now()
            )
            
            tags_list = [tag.strip().lower() for tag in tags_string.split(',') if tag.strip()]
            for tag_name in tags_list:
                tag = Tag.query.filter_by(tag_name=tag_name).first()
                if not tag:
                    tag = Tag(tag_name=tag_name)
                    db.session.add(tag)
                new_post.tags.append(tag)
            
            db.session.add(new_post)
            db.session.commit()
            flash('Your post has been successfully added!', 'success')
            return redirect(url_for('index'))
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
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        
        tags_string = request.form.get('tags_input', '')
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


#initializing database
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)