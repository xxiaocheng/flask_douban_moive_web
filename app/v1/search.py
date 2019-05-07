from app.extensions import api
from app.models import User,Celebrity,Movie
from flask_restful import Resource,reqparse
from .schemas import user_summary_schema,movie_summary_schema,celebrity_summary_schema,items_schema
from flask import url_for


# class Search(Resource):

#     def get(self):
#         parser = reqparse.RequestParser()
#         parser.add_argument('cate',location='args' ,required=True,choices=('movie','people','celebrity'))
#         parser.add_argument('q',location='args',required=True)
#         parser.add_argument('page', default=1, type=int, location='args')
#         parser.add_argument('per_page', default=20, type=int, location='args')
#         args = parser.parse_args()

#         if args['cate']=='people':
#             pagination=User.objects.search_text(args.q).paginate(page=args['page'], per_page=args['per_page'])
#             items = [user_summary_schema(user) for user in pagination.items if user.is_deleted==False]
#         if args['cate']=='movie':
#             pagination=Movie.objects.search_text(args.q).paginate(page=args['page'], per_page=args['per_page'])
#             items = [movie_summary_schema(movie) for movie in pagination.items if movie.is_deleted==False]
#         if args['cate']=='celebrity':
#             pagination=Celebrity.objects.search_text(args.q).paginate(page=args['page'], per_page=args['per_page'])
#             items = [celebrity_summary_schema(celebrity) for celebrity in pagination.items if celebrity.is_deleted==False]

#         prev = None
#         if pagination.has_prev:
#             prev = url_for(
#                 '.search', cate=args['cate'],q=args.q ,page=args['page']-1, per_page=args['per_page'], _external=True)

#         next = None
#         if pagination.has_next:
#             prev = url_for(
#                 '.search', cate=args['cate'],q=args.q , page=args['page']+1, per_page=args['per_page'], _external=True)

#         first = url_for(
#             '.search', cate=args['cate'], q=args.q ,page=1, perpage=args['per_page'], _external=True)
#         last = prev = url_for(
#             '.search', cate=args['cate'], q=args.q ,page=pagination.pages, perpage=args['per_page'], _external=True)
#         return items_schema(items, prev, next, first, last, pagination.total, pagination.pages)

# api.add_resource(Search,'/search')

class Search(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('cate',location='args' ,required=True,choices=('movie','people','celebrity'))
        parser.add_argument('q',location='args',required=True)
        args = parser.parse_args()

        if args['cate']=='people':
            pagination=User.objects.search_text(args.q)
            items = [user_summary_schema(user) for user in pagination if user.is_deleted==False]
        if args['cate']=='movie':
            pagination=Movie.objects.search_text(args.q)
            items = [movie_summary_schema(movie) for movie in pagination if movie.is_deleted==False]
        if args['cate']=='celebrity':
            pagination=Celebrity.objects.search_text(args.q)
            items = [celebrity_summary_schema(celebrity) for celebrity in pagination if celebrity.is_deleted==False]

        prev = None 

        next = None
        
        return items_schema(items, prev, next, None, None, len(items), 1)

api.add_resource(Search,'/search')