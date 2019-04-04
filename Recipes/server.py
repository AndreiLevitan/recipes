from flask_restful import reqparse, abort, Api, Resource
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask import Flask, render_template, make_response
import sqlite3
import flask_reqparse

app = Flask(__name__)
api = Api(app)


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
                             password_hash VARCHAR(128)
                             )''')
        cursor.close()
        self.connection.commit()

    def insert(self, user_name, password_hash):
        cursor = self.connection.cursor()
        cursor.execute('''INSERT INTO users 
                          (user_name, password_hash) 
                          VALUES (?,?)''', (user_name, password_hash))
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
        return (True, row[0]) if row else (False,)


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


class Login(Resource):
    def get(self):
        headers = {'Content-Type': 'text/html'}

        return make_response(render_template('login.html'), 200, headers)

def abort_if_recipe_not_found(recipe_id):
    if not RecipesModel(db.get_connection()).get(recipe_id):
        abort(404, message="Recipe {} not found".format(recipe_id))


api.add_resource(RecipesList, '/recipes', '/')

if __name__ == '__main__':
    db = DB()
    RecipesModel(db.get_connection()).init_table()
    UsersModel(db.get_connection()).init_table()
    app.run(port=8080, host='127.0.0.1')
