from flask_restful import reqparse, abort, Api, Resource
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask import Flask, render_template, make_response, session, redirect
import sqlite3
import flask_reqparse


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

    def get(self, recipes_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (str(recipes_id)))
        row = cursor.fetchone()
        return row

    def get_all(self, user_id=None):
        cursor = self.connection.cursor()
        if user_id:
            cursor.execute("SELECT * FROM recipes WHERE user_id = ?",
                           (str(user_id)))
        else:
            cursor.execute("SELECT * FROM recipes")
        rows = cursor.fetchall()
        return rows

    def change(self, recipes_id, title, ingredient, content, img_src, user_id):
        cursor = self.connection.cursor()
        cursor.execute('''UPDATE recipes SET title = ?, ingredient = ?
                          content = ?, img_src, user_id = ? 
                          WHERE id = ?''', (title, content, ingredient, img_src, str(user_id), str(recipes_id)))
        cursor.close()
        self.connection.commit()

    def delete(self, recipes_id):
        cursor = self.connection.cursor()
        cursor.execute('''DELETE FROM recipes WHERE id = ?''', (str(recipes_id)))
        cursor.close()
        self.connection.commit()


class RecipesList(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}
        recipes = RecipesModel(db.get_connection()).get_all()
        return make_response(render_template('recipes.html', recipes=recipes), 200, headers)


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
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
        return make_response(render_template('login.html', form=self.form, uncorrect=1), 200, headers)



def abort_if_recipe_not_found(recipe_id):
    if not RecipesModel(db.get_connection()).get(recipe_id):
        abort(404, message="Recipe {} not found".format(recipe_id))


api.add_resource(RecipesList, '/recipes', '/')
api.add_resource(Login, '/login')

if __name__ == '__main__':
    db = DB()
    RecipesModel(db.get_connection()).init_table()
    UsersModel(db.get_connection()).init_table()
    app.run(port=8080, host='127.0.0.1')
