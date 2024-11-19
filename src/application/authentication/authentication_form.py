from fastapi.security import OAuth2PasswordBearer
from fastapi import Form

class OAuth2PasswordRequestFormCustom:
    def __init__(self, username: str = Form(...), user_tag: str = Form(...)):
        self.username = username
        self.user_tag = user_tag