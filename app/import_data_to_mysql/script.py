from app.sql_models import Genre, Image, Movie, Celebrity
from app.extensions import sql_db
import os
import json

basedir = os.path.abspath(os.path.dirname(__file__))


def import_images(cate="celebrity"):
    this_dir = os.path.join(basedir, "./images/" + cate)
    g = os.walk(this_dir)
    for path, dir_list, file_list in g:
        for file_name in file_list:
            file_path = os.path.join(path, file_name)
            with open(file_path, "rb") as f:
                image_obj = Image.create_one(f, file_name)
                sql_db.session.add(image_obj)
                sql_db.session.commit()


def import_genres():
    this_dir = os.path.join(basedir, "tag.json")
    with open(this_dir, "r") as f:
        b = json.load(f)
        for tag in b["RECORDS"]:
            if tag["cate"] == "1":
                g = Genre(genre_name=tag["name"], ext=tag["_id"])
                sql_db.session.add(g)
        sql_db.session.commit()


def import_celebrity():
    this_dir = os.path.join(basedir, "celebrity.json")
    with open(this_dir, "r") as f:
        b = json.load(f)
        for celebrity in b["RECORDS"]:
            c = Celebrity(
                ext=celebrity["_id"],
                douban_id=celebrity["douban_id"],
                name=celebrity["name"],
            )
            img = Image.query.filter_by(ext=celebrity["avatar"]).first()
            if img:
                c.image = img
                sql_db.session.add(c)
                sql_db.session.commit()


def import_movie():
    this_dir = os.path.join(basedir, "movie.json")
    with open(this_dir, "r") as f:
        b = json.load(f)
        for movie in b["RECORDS"]:
            image = Image.query.filter_by(ext=movie["image"]).first()
            if image:
                m = Movie.create_one(
                    title=movie["title"],
                    subtype=movie["subtype"],
                    image=image,
                    year=movie["year"],
                    douban_id=movie["douban_id"],
                    original_title=movie["original_title"],
                    summary=movie["summary"],
                    aka_list=json.loads(movie["aka"]),
                    countries_name=json.loads(movie["countries"]),
                )
                m.ext = movie["_id"]
                for g in json.loads(movie["genres"]):
                    gg = Genre.query.filter_by(ext=g["$oid"]).first()
                    if gg:
                        m.genres.append(gg)
                for d in json.loads(movie["directors"]):
                    cc = Celebrity.query.filter_by(ext=d["$oid"]).first()
                    if cc:
                        m.directors.append(cc)
                for c in json.loads(movie["casts"]):
                    cc = Celebrity.query.filter_by(ext=c["$oid"]).first()
                    if cc:
                        m.celebrities.append(cc)
                sql_db.session.add(m)
                sql_db.session.commit()


def import_all():
    print(basedir)
    import_images("movie")
    import_images("celebrity")
    import_genres()
    import_celebrity()
    import_movie()
