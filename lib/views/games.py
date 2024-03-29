import os
import requests
import json
from bs4 import BeautifulSoup
from flask import (
    Flask, flash, render_template, Blueprint,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from lib.helper import db
if os.path.exists("env.py"):
    import env

blueprint = Blueprint("games", __name__, url_prefix="/games")
API_KEY = os.environ.get("API_KEY")


def insert_review():
    '''adds review into db'''
    review = {
            "game_name": request.form.get("game_name"),
            "game_id": request.form.get("game_id"),
            "game_rating": request.form.get("rating"),
            "game_img": request.form.get("game_img"),
            "user": session["user"],
            "game_review": request.form.get("review")
        }
    db().reviews.insert_one(review)


def check_review_exists():
    '''checks if user reviewed already'''
    already_reviewed = {
            "game_name": request.form.get("game_name"),
            "user": session["user"]
        }
    return db().reviews.find_one(already_reviewed)


def edit_review_data():
    '''data for editing review'''
    edit = {
            "game_name": request.form.get("game_name"),
            "game_rating": request.form.get("rating"),
            "game_img": request.form.get("game_img"),
            "user": session["user"],
            "game_review": request.form.get("review")
        }
    return edit


@blueprint.route("/")
def get_games():
    '''requests game data from api'''
    parameters = {
        "page_size": 8
    }
    try:
        response = requests.get(
            f"https://api.rawg.io/api/games?key={API_KEY}", params=parameters)
        data = response.json()
    except requests.exceptions.RequestException as request_exception:
        raise SystemExit from request_exception

    return render_template("games.html", data=data)


@blueprint.route("/search", methods=["GET", "POST"])
def search():
    '''Allows user to search games using the rawg API as the database'''
    query = request.form.get("query")
    parameters = {
        "page_size": 8,
        "search": query
    }
    try:
        response = requests.get(
            f"https://api.rawg.io/api/games?key={API_KEY}", params=parameters)
        data = response.json()
    except requests.exceptions.RequestException as request_exception:
        raise SystemExit from request_exception

    return render_template("games.html", data=data)


@blueprint.route("/<game_id>")
def game(game_id):
    '''gets individual game information'''
    try:
        response = requests.get(
            f"https://api.rawg.io/api/games/{game_id}?key={API_KEY}")
        game = response.json()
    except requests.exceptions.RequestException as request_exception:
        raise SystemExit from request_exception

    total = 0
    game_id = str(game['id'])
    reviews = db().reviews.find(
        {'game_id': game_id}, {'_id': 0, 'game_rating': 1})
    count = reviews.count()
    for review in reviews:
        total += int(review['game_rating'])
    average = round(total / count, 1)
    print(average)

    htmlDescription = json.dumps(game['description'])
    soup = BeautifulSoup(htmlDescription, 'html.parser')
    description = soup.get_text()

    # doesn't work
    # clean = description.replace("\n", "")

    return render_template(
        "game.html", game=game, description=description, average=average)


@blueprint.route("/get_reviews")
def get_reviews():
    '''Shows list of reviews from Mongodb'''
    reviews = db().reviews.find()
    return render_template("reviews.html", reviews=reviews)


@blueprint.route("/search_reviews", methods=["GET", "POST"])
def search_reviews():
    '''Searches through user reviews'''
    query = request.form.get("query")
    reviews = list(db().reviews.find({"$text": {"$search": query}}))
    if not reviews:
        flash("Couldn't find any reviews to match your search", "error-msg")
    return render_template("reviews.html", reviews=reviews)


@blueprint.route("/add_review", methods=["GET", "POST"])
def add_review():
    '''adds review to db'''
    if request.method == "POST":
        if check_review_exists() is None:
            insert_review()
            flash("Review added successfully", "success-msg")
            return redirect(url_for("games.get_reviews"))

        flash("You've Already reviewed this game", "error-msg")
    return redirect(url_for("games.get_reviews"))


@blueprint.route("/edit_review/<review_id>", methods=["GET", "POST"])
def edit_review(review_id):
    '''Finds review by id and edits it'''
    review = db().reviews.find_one({"_id": ObjectId(review_id)})
    if request.method == "POST":
        db().reviews.update({"_id": ObjectId(review_id)}, edit_review_data())
        flash("Review updated successfully", "success-msg")
        return redirect(url_for("games.get_reviews"))

    return render_template("edit_review.html", review=review)


@blueprint.route("/delete_review/<review_id>")
def delete_review(review_id):
    '''Deletes Review by id'''
    db().reviews.delete_one({"_id": ObjectId(review_id)})
    flash("Review deleted successfully", "success-msg")
    return redirect(url_for("games.get_reviews"))
