from app.extensions import api

from flask_restful import Resource,reqparse


class Search(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('cate',location='args' ,required=True,choices=('movie','people','celcebrity'))
        parser.add_argument('q',location='args',required=True)
        args = parser.parse_args()

        if args['cate']=='people':
            return{
                "message":"this is a dict of people."
            }
        if args['cate']=='movie':
            pass
        if args['cate']=='celebrity':
            pass


api.add_resource(Search,'/search')