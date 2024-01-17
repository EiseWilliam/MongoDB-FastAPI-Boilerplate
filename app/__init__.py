# describe the project
"""
monterface is a reusable Python library that provides integration between FastAPI and MongoDB. It aims to simplify the process of building web applications with FastAPI and interacting with MongoDB databases.

Features:
- Seamless integration with FastAPI for building RESTful APIs.
- Simplified CRUD operations for MongoDB collections.
- Automatic validation and serialization of request and response data.
- Support for authentication and authorization mechanisms.
- Flexible query building and filtering options.
- Extensible architecture for adding custom functionality.

Usage:
1. Install monterface using pip: `pip install monterface`.
2. Import the necessary modules and classes from monterface in your FastAPI application.
3. Configure the connection to your MongoDB database.
4. Define your FastAPI routes and use monterface to interact with MongoDB collections.

For more information and examples, please refer to the documentation at <insert documentation link>.
"""
__VERSION__ = "0.1.0"


# make the imports for library users easier
from .schemas.core import ModelGenerator as Model
from .core.handlers.base import BaseCRUD as CRUD

MakeModel = Model.make_model