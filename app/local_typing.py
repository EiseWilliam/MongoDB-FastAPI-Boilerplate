from pymongo.results import (
    BulkWriteResult as DBBulkWriteResult,
    DeleteResult as DBDeleteResult,
    InsertManyResult as DBInsertManyResult,
    InsertOneResult as DBInsertOneResult,
    UpdateResult as DBUpdateResult,
)
from motor.core import AgnosticCollection as AgnosticCollection, AgnosticCursor as AgnosticCursor