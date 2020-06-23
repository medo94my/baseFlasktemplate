from app import app,db
import secrets
import os
from PIL import Image

from flask_login import current_user
from app.modules.models import User

def save_picture(form_picture,id):
    user=User.query.filter_by(id=id).first()
    if user.profile_image:
        _path=os.path.join(app.root_path,'static/img/profile_pics',user.profile_image)
        if os.path.exists(_path):
            os.remove(_path)
    random_hex=secrets.token_hex(8)
    _,f_ext=os.path.splitext(form_picture.filename)
    picture_fn=random_hex+f_ext
    picture_path=os.path.join(app.root_path,'static/img/profile_pics',picture_fn)
    output_size=(125,125)
    resize=Image.open(form_picture)
    resize.thumbnail(output_size)
    resize.save(picture_path)
    return picture_fn
def picture_validation(picture,id):
    _,file_ext=os.path.splitext(picture.filename)
    file_ext=file_ext.replace('.','')
    allowed_ext=['jpg','png']
    if file_ext.lower() in allowed_ext:
        picture_file=save_picture(picture,id)
        return picture_file,True
    else:
        return  allowed_ext,False