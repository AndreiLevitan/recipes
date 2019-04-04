from flask_restful import reqparse, abort, Api, Resource
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileField
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired
from flask import Flask, render_template, make_response, session, redirect
import sqlite3
import os
import transliterate

app = Flask(__name__)
api = Api(app)
app.secret_key = "super secret key"


class DB:
    def __init__(self):
        conn = sqlite3.connect('recipes.db', check_same_thread=False)
        self.conn = conn

    def get_connection(self):
        return self.conn

    def __del__(self):
        self.conn.close()


class UsersModel:
    def __init__(self, connection):
        self.connection = connection

    def init_table(self):
        cursor = self.connection.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                             user_name VARCHAR(50),
                             password_hash VARCHAR(128),
                             administrator INTEGER
                             )''')
        cursor.close()
        self.connection.commit()

    def insert(self, user_name, password_hash, administrator):
        cursor = self.connection.cursor()
        cursor.execute('''INSERT INTO users 
                          (user_name, password_hash, administrator) 
                          VALUES (?,?,?)''', (user_name, password_hash, str(administrator)))
        cursor.close()
        self.connection.commit()

    def get(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (str(user_id),))
        row = cursor.fetchone()
        return row

    def get_all(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        return rows

    def exists(self, user_name, password_hash):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE user_name = ? AND password_hash = ?",
                       (user_name, password_hash))
        row = cursor.fetchone()
        return (True, row[0], row[3]) if row else (False,)

    def is_unique(self, user_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE user_name = ?",
                       (user_name,))
        row = cursor.fetchone()
        return False if row else True

    def set_administrator(self, user_id, value):
        cursor = self.connection.cursor()
        cursor.execute("UPDATE users SET administrator = ? WHERE id = ?",
                       (str(value), str(user_id)))

    def clean(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM users")
        cursor.close()
        self.connection.commit()


class RecipesModel:
    def __init__(self, connection):
        self.connection = connection

    def init_table(self):
        cursor = self.connection.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS recipes 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                             title VARCHAR(100),
                             ingredient VARCHAR(1000),
                             content VARCHAR(2000),
                             img_src VARCHAR(100),
                             user_id INTEGER
                             )''')
        cursor.close()
        self.connection.commit()

    def insert(self, title, ingredient, content, img_src, user_id):
        cursor = self.connection.cursor()
        cursor.execute('''INSERT INTO recipes 
                          (title, ingredient, content, img_src, user_id) 
                          VALUES (?,?,?,?,?)''', (title, ingredient, content, img_src, str(user_id)))
        cursor.close()
        self.connection.commit()

    def get(self, recipe_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (str(recipe_id),))
        row = cursor.fetchone()
        return row

    def get_all(self, user_id=None):
        cursor = self.connection.cursor()
        if user_id:
            cursor.execute("SELECT * FROM recipes WHERE user_id = ?",
                           (str(user_id),))
        else:
            cursor.execute("SELECT * FROM recipes")
        rows = cursor.fetchall()
        return reversed(rows)

    def check_unique_title(self, user_id, title):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM recipes WHERE title = ? AND user_id = ?",
                       (title, str(user_id)))
        titles = cursor.fetchall()
        return not bool(titles)

    def change(self, recipe_id, title, ingredient, content, img_src, user_id):
        cursor = self.connection.cursor()
        cursor.execute('''UPDATE recipes SET title = ?, ingredient = ?
                          content = ?, img_src, user_id = ? 
                          WHERE id = ?''', (title, content, ingredient, img_src, str(user_id), str(recipe_id)))
        cursor.close()
        self.connection.commit()

    def delete(self, recipe_id):
        cursor = self.connection.cursor()
        cursor.execute('''DELETE FROM recipes WHERE id = ?''', (str(recipe_id),))
        cursor.close()
        self.connection.commit()


class RecipesList(Resource):
    def get(self):
        if 'username' in session:
            headers = {'Content-Type': 'text/html'}
            recipes = RecipesModel(db.get_connection()).get_all()
            return make_response(render_template('recipes.html', recipes=recipes), 200, headers)
        return redirect('/login')


class Recipe(Resource):
    def get(self, recipe_id):
        if 'username' in session:
            headers = {'Content-Type': 'text/html'}
            recipe = RecipesModel(db.get_connection()).get(recipe_id)
            if session['user_id'] == recipe[5] or session['administrator']:
                return make_response(render_template('recipe.html', recipe=recipe), 200, headers)
            else:
                return abort(403)
        return redirect('/login')


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(message='Введите корректные данные')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Введите корректные данные')])
    submit = SubmitField('Войти')


class Login(Resource):
    def __init__(self):
        self.form = LoginForm()

    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('login.html', form=self.form), 200, headers)

    def post(self):
        headers = {'Content-Type': 'text/html'}
        users = UsersModel(db.get_connection())
        if self.form.validate_on_submit() and users.exists(self.form.username.data, self.form.password.data):
            exists = users.exists(self.form.username.data, self.form.password.data)
            login = self.form.username.data
            if exists[0]:
                session['username'] = login
                session['user_id'] = exists[1]
                session['administrator'] = exists[2]
                return redirect('/recipes')
        return make_response(render_template('login.html', form=self.form, uncorrect='Неправильный логин/пароль'), 200,
                             headers)


class RegisterForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(message='Введите корректные данные')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Введите корректные данные')])
    submit = SubmitField('Зарегистрироваться')


class Register(Resource):
    def __init__(self):
        self.form = RegisterForm()

    def get(self):
        headers = {'Content-Type': 'text/html'}
        return make_response(render_template('register.html', form=self.form), 200, headers)

    def post(self):
        headers = {'Content-Type': 'text/html'}
        users = UsersModel(db.get_connection())
        if self.form.validate_on_submit():
            login = self.form.username.data
            password = self.form.password.data
            if users.is_unique(login):
                users.insert(login, password, 0)
                return redirect('/login')
            return make_response(render_template('register.html', form=self.form, uncorrect="Логин уже занят"), 200,
                                 headers)
        return make_response(render_template('register.html', form=self.form, uncorrect="Введите корректные данные"),
                             200,
                             headers)


class Logout(Resource):
    def get(self):
        session.pop('username', 0)
        session.pop('user_id', 0)
        session.pop('administrator', 0)
        return redirect('/login')


class RecipeForm(FlaskForm):
    UPLOAD_FOLDER = 'static\\img\\recipes'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    title = StringField('Название', validators=[DataRequired(message='Введите название рецепта')])
    description = TextAreaField('Описание и приготовление', validators=[DataRequired(message='Введите описание')])
    ingredients = TextAreaField('Ингредиенты', validators=[DataRequired(message='Введите ингридиенты')])
    img = FileField('Фото для обложки', validators=[FileRequired()])
    submit = SubmitField('Добавить')


class AddRecipe(Resource):
    def __init__(self):
        self.form = RecipeForm()

    def allowed_file(self, filename):
        ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def get(self):
        if 'username' in session:
            headers = {'Content-Type': 'text/html'}
            return make_response(render_template('add_recipe.html', form=self.form), 200, headers)
        return redirect('/login')

    def post(self):
        headers = {'Content-Type': 'text/html'}
        recipes = RecipesModel(db.get_connection())
        user_id = session['user_id']
        title = self.form.title.data
        if self.form.validate_on_submit() and recipes.check_unique_title(user_id, title):
            description = self.form.description.data
            ingredients = self.form.ingredients.data
            if self.allowed_file(self.form.img.data.filename):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                         transliterate.translit(title, reversed=True).replace(' ', '_') + '.' +
                                         self.form.img.data.filename.rsplit('.', 1)[1])
                self.form.img.data.save(file_path)
                recipes.insert(title, ingredients, description, file_path, user_id)
                return redirect('/recipes')
            return make_response(render_template('add_recipe.html', form=self.form,
                                                 uncorrect='Неверный тип файла (не jpg, jpeg, png, gif)'), 200, headers)


def abort_if_recipe_not_found(recipe_id):
    if not RecipesModel(db.get_connection()).get(recipe_id):
        abort(404, message="Recipe {} not found".format(recipe_id))


api.add_resource(RecipesList, '/recipes', '/')
api.add_resource(AddRecipe, '/recipes/add')
api.add_resource(Recipe, '/recipe/<int:recipe_id>')
api.add_resource(Login, '/login')
api.add_resource(Register, '/register')
api.add_resource(Logout, '/logout')

if __name__ == '__main__':
    db = DB()
    RecipesModel(db.get_connection()).init_table()
    UsersModel(db.get_connection()).init_table()
    app.run(port=8080, host='127.0.0.1')
