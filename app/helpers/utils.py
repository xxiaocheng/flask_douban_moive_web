import requests
from flask import current_app
import os

def save_image(image_url,cate):
    # 传入图片url 保存到本地

    assert cate in ['avatar','celebrity','movie']
    if cate=='avatar':
        base_path=os.path.join(current_app.config['UPLOAD_PATH'],'avatar')

    if cate=='celebrity':
        base_path=os.path.join(current_app.config['UPLOAD_PATH'],'celebrity')
    
    if cate =='movie':
        base_path=os.path.join(current_app.config['UPLOAD_PATH'],'movie')

    file_name=image_url.split('/')[-1]

    with open(os.path.join(base_path,file_name), 'wb') as file:
        file.write(requests.get(image_url).content)