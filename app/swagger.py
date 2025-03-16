from flasgger import Swagger

def init_swagger(app):
    swagger_template = {
        "info": {
            "title": "API Documentation",
        },
    }
    swagger = Swagger(app,template=swagger_template)
    return swagger
