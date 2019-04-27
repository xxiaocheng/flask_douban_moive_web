from flask_restful import Resource,reqparse

from app.extensions import api
from .schemas import celebrity_schema,celebrity_summary_schema
from app.models import Celebrity
from .auth import permission_required,auth
from mongoengine.errors import ValidationError

class CelebrityInfo(Resource):
    
    def get(self,id):
        """返回单个影人详细信息
        """
        parser = reqparse.RequestParser()
        parser.add_argument('cate',default='detail',choices=['summary','detail'],location='args')
        args = parser.parse_args()
        try:
            celebrity=Celebrity.objects(id=id,is_deleted=False).first()
        except ValidationError:
            return{
                'message':'celebrity not found.'
            },404

        if not celebrity:
            
            return{
                'message':'celebrity not found.'
            },404
        if args.cate=='summary':
             return celebrity_summary_schema(celebrity)
        return celebrity_schema(celebrity)

    # @auth.login_required
    # @permission_required('DELETE_CELEBRITY')
    def delete(self,id):
        # 删除一个艺人信息  ,需要验证具备权限的用户操作  
        try:
            celebrity=Celebrity.objects(id=id,is_deleted=False).first()
        except ValidationError:
            return{
                'message':'celebrity not found.'
            },404
            
        if not celebrity:
            return{
                'message':'celebrity not found.'
            },404

        celebrity.update(is_deleted=True)
        return {
            'message':'celebrity deleted.'
        }


api.add_resource(CelebrityInfo ,'/celebrity/<id>')



# class AddCelebrity(Resource):

#     # @auth.login_required
#     # @permission_require('UPLOAD_CELEBRITY')
#     def post(self):
#         parser = reqparse.RequestParser()
#         parser.add_argument('')
#         args = parser.parse_args()
        


# api.add_resource(AddCelebrity,'/celebrity')

