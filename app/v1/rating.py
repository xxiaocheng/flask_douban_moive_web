from flask_restful import Resource, reqparse
from app.extensions import api
from app.models import Rating
from .auth import auth
from flask import g

class RatingAction(Resource):

    @auth.login_required
    def post(self,ratingid):
        parser=reqparse.RequestParser()
        parser.add_argument('typename',choices=['like','unlike','report'],required=True,location='form',type=str)
        args=parser.parse_args()
        rating=Rating.objects(id=ratingid,is_deleted=False).first()
        if not rating:
            return{
                'message':'rating not found'
            },404
        user=g.current_user
        if args['typename']=='like':
            if user.is_like_rating(rating):
                return{
                    'message':'you already like this rating'
                },403
            else:
                rating.like_by(user)
                return{
                    'message':'like successfuly'
                }
        if args['typename']=='unlike':
            if not user.is_like_rating(rating):
                return{
                    'message':'you not like this rating before'
                },403
            else:
                rating.unlike_by(user)
                return{
                    'message':'unlike'
                }
        if args['typename']=='report':
            rating.report_by(user)
            return{
                'message':'succeed'
            }

    @auth.login_required    
    def delete(self,ratingid):
        user=g.current_user
        rating=Rating.objects(id=ratingid,is_deleted=False).first()
        if not rating:
            return{
                'message':'rating not found'
            },404
        rating.delete_self()
        return{
            'message':'rating has deleted'
        }


api.add_resource(RatingAction,'/rating/<ratingid>')