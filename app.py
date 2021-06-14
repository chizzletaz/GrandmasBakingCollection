import os
from flask import (
    Flask, flash, render_template, redirect, 
    request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
if os.path.exists("env.py"):
    import env

# create an instance of Flask:
app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

# create an instance of PyMongo:
mongo = PyMongo(app)


# HOME
@app.route("/")
@app.route("/home")
def home():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("index.html", categories=categories)


# SEARCH
@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    for recipe in recipes:
        try:
            category = mongo.db.categories.find_one({'_id': ObjectId(recipe['category_name'])})
            recipe['category_name'] = category['category_name']
        except Exception as e:
            print('Exception %s' % str(e))
            pass
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("recipes.html", recipes=recipes, categories=categories)


# FILTER ON CATEGORY
@app.route("/recipes_filter/<category_name>")
def recipes_filter(category_name):
    recipes = list(mongo.db.recipes.find())
    for recipe in recipes:     
        category = mongo.db.categories.find_one({'_id': ObjectId(recipe['category_name'])})
        recipe['category_name'] = category['category_name']
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("recipes.html", recipes=recipes, categories=categories)


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if the username already exists in the database
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
        
        if existing_user:
            flash("This username already exists, try another username")
            return redirect(url_for('register'))

        register = {
            "username" : request.form.get("username").lower(),
            "password" : generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session ' cookie
        session['user'] = request.form.get('username').lower()
        flash('Registration succesful!')
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        #check if the username exists in the database
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
        
        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                existing_user["password"], request.form.get("password")):
                    session['user'] = request.form.get("username").lower()
                    flash("welcome, {}".format(
                        request.form.get("username")))
                    return redirect(url_for(
                        "profile", username=session["user"]))
                    
            else:
                # invalid password match
                flash("Incorrect username and/or password, try again.")
                return redirect(url_for('login'))

        else:
            #username doesn't exist
            flash("Incorrect username and/or password, try again.")
            return redirect(url_for('login'))

    return render_template("login.html")


# PROFILE PAGE
@app.route('/profile/<username>', methods=["GET", "POST"])
def profile(username):
    # get the session user's name from the database
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    
    if session['user']:
        categories = list(mongo.db.categories.find().sort("category_name", 1))
        return render_template("profile.html", username=username, categories=categories)

    return redirect(url_for('login'))


# LOGOUT
@app.route("/logout")
def logout():

    #remove user from session cookies
    flash("You have been logged out")
    session.pop('user')
    return redirect(url_for("login"))


# ALL RECIPES
@app.route("/recipes")
def recipes():
    recipes = list(mongo.db.recipes.find())
    # credit for the relations between collections using ObjectId: my mentor: Antonio Rodriguez
    for recipe in recipes:
        try:
            category = mongo.db.categories.find_one({'_id': ObjectId(recipe['category_name'])})
            recipe['category_name'] = category['category_name']
        except Exception as e:
            print('Exception %s' % str(e))
            pass
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("recipes.html", recipes=recipes, categories=categories)


# INDIVIDUAL RECIPE
@app.route("/recipe/<recipe_id>")
def recipe(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    # credit for the relations between collections using ObjectId: my mentor: Antonio Rodriguez
    try:
        user = mongo.db.users.find_one({'_id': ObjectId(recipe['created_by'])})
        recipe['created_by'] = user['username']
    except Exception as e:
        print('Exception %s' % str(e))
        pass
    return render_template("recipe.html", recipe=recipe)


# ADD RECIPE
@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        # credit for the relations between collections using ObjectId: my mentor: Antonio Rodriguez
        user = mongo.db.users.find_one({'username': session["user"]})
        recipe = {
            "category_name": ObjectId(request.form.get("category_name")),
            "recipe_title": request.form.get("recipe_title"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_image": request.form.get("recipe_image"),
            "prep_time": request.form.get("prep_time"),
            "bake_time": request.form.get("bake_time"),
            "total_time": request.form.get("total_time"),
            "servings": request.form.get("servings"),
            "tools": request.form.get("tools"),
            "ingredients": request.form.getlist("ingredient[]"),
            "steps": request.form.getlist("step[]"),
            "tips": request.form.get("tips"),
            "created_by": ObjectId(user['_id']),
            # credit specific time format: https://www.programiz.com/python-programming/datetime/current-datetime
            "date_added": date.today().strftime("%d %B %Y") 
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Your recipe has been added.")
        return redirect(url_for('profile', username=session["user"]))

    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("add_recipe.html", categories=categories)


# EDIT RECIPE
@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "POST":
        # credit for the relations between collections using ObjectId: my mentor: Antonio Rodriguez
        user = mongo.db.users.find_one({'username': session["user"]})
        submit = {
            "category_name": ObjectId(request.form.get("category_name")),
            "recipe_title": request.form.get("recipe_title"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_image": request.form.get("recipe_image"),
            "prep_time": request.form.get("prep_time"),
            "bake_time": request.form.get("bake_time"),
            "total_time": request.form.get("total_time"),
            "servings": request.form.get("servings"),
            "tools": request.form.get("tools"),
            "ingredients": request.form.getlist("ingredients[]"),
            "steps": request.form.getlist("steps"),
            "tips": request.form.get("tips"),
            "created_by": ObjectId(user['_id']),
            # credit specific time format: https://www.programiz.com/python-programming/datetime/current-datetime
            "date_added": date.today().strftime("%d %B %Y") 
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Your recipe has been updated.")

    
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    try:
        category = mongo.db.categories.find_one({'_id': ObjectId(recipe['category_name'])})
        recipe['category_name'] = category['category_name']
    except Exception as e:
        print('Exception %s' % str(e))
        pass
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("edit_recipe.html", recipe=recipe, categories=categories)


# DELETE RECIPE
@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    try:
        user = mongo.db.users.find_one({'_id': ObjectId(recipe['created_by'])})
        recipe['created_by'] = user['username']
    except Exception as e:
        print('Exception %s' % str(e))
        pass

    if session['user'].lower() == recipe['created_by'].lower():
        
        mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
        flash("Your recipe has been deleted.")
        return redirect(url_for('profile', username=session["user"]))
    
    else:
        flash("Action denied. This is not your recipe")
        return redirect(url_for('profile', username=session["user"]))


# MANAGE CATEGORIES
@app.route("/categories")
def categories():
    categories = list(mongo.db.categories.find().sort("category_name", 1))
    return render_template("categories.html", categories=categories)


# ADD CATEGORY
@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.insert_one(category)
        flash("New category has been added.")
        return redirect(url_for('categories'))

    return render_template("add_category.html")


# EDIT CATEGORY
@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    
    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.update({"_id": ObjectId(category_id)}, submit)
        flash('Category has been updated.')
        return redirect(url_for('categories'))

    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    return render_template("edit_category.html", category=category)


# DELETE CATEGORY
@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    if session['user'] == 'admin'.lower():
        mongo.db.categories.remove({"_id": ObjectId(category_id)})
        flash("Category has been deleted.")
        return redirect(url_for('categories'))
    
    flash('You have no permission to delete a category')
    return redirect(url_for('profile', username=session["user"]))


# ERROR HANDLERS
@app.errorhandler(403)
def forbidden_access(e):
    return render_template('/error_handlers/403.html'), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template('/error_handlers/404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('/error_handlers/500.html'), 500


# APP INITIALISATION
if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
    port=int(os.environ.get("PORT")),
    debug=True)
