from flask_restful import Resource, reqparse
from app.extensions import api
from app.models import Tag,Movie
from .auth import auth,  permission_required
from app.extensions import cache

class Tags(Resource):
    
    # @auth.login_required
    # @permission_required('UPLOAD_TAG')
    def post(self):
        parser=reqparse.RequestParser()
        parser.add_argument('tagname',required=True,location='form',type=str)
        args=parser.parse_args()
        try:
            Tag(name=args['tagname'],cate=1).save()
            return{
                'message':'add tag successfuly'
            }
        except :
            return{
                'message':"tag already exist"
            },403


    # @auth.login_required
    # @permission_required('DELETED_TAG')
    def delete(self):
        parser=reqparse.RequestParser()
        parser.add_argument('tagname',required=True,location='form',type=str)
        args=parser.parse_args()
        n=Tag.objects(name=args['tagname'],cate=1).delete()
        if n==1:
            return{
                'message':'delete this tag successfuly'
            }
        else:
            return{
                'message':'this tag not exist'
            },403
    
    @cache.cached(timeout=60*60*24,query_string=True)
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('cate',choices=['sys','user'] ,default='sys',type=str, location='args')
        args = parser.parse_args()
        cate_=0 if args['cate']=='user' else 1
        tag_query_set=Tag.objects(cate=cate_)
        return{
            'items':[{'name':tag.name,'id':str(tag.id)} for tag in tag_query_set if tag_query_set],
            'count':tag_query_set.count(),
            'cate':cate_,
        }


api.add_resource(Tags,'/tags')


class Country(Resource):

    @cache.cached(timeout=60*60*24,query_string=True)
    def get(self):
        movies=Movie.objects()
        countries=[]
        for movie in movies:
            countries+=movie.countries
        
        countries=list(set(countries))

        return {
            'items':countries,
            'count':len(countries),
        }

api.add_resource(Country,'/country')


class Year(Resource):

    @cache.cached(timeout=60*60*24,query_string=True)
    def get(self):
        movies=Movie.objects()
        year=[]
        for movie in movies:
            year.append(movie.year)

        year=list(set(year))
        year.sort(reverse=True)

        return {
            'items':year,
            'count':len(year)
        }

api.add_resource(Year,'/year')