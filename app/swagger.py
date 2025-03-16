from flasgger import Swagger

def init_swagger(app):
    swagger = Swagger(app)
    return swagger
