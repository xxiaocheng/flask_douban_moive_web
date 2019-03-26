from flask_restful import Resource, reqparse
from app.extensions import api
from app.models import Tag
from .auth import auth,  permission_required

class Tags(Resource):
    
    @auth.login_required
    @permission_required('UPLOAD_TAG')
    def post():
        pass

    @auth.login_required
    @permission_required('DELETED_TAG')
    def delete():
        pass
    

    def get():
        parser = reqparse.RequestParser()
        parser.add_argument('cate',choices=['sys','user'] ,default='sys',type=str, location='args')
        args = parser.parse_args()
        cate_=0 if args['user']=='user' else 1
        tag_query_set=Tag.objects(cate=cate_)
        return{
            'items':[{'name':tag.name,'id':str(tag.id)} for tag in tag_query_set if tag_query_set],
            'count':tag_query_set.count(),
            'cate':cate_,
        }


api.add_resource(Tags,'/tag')