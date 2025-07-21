from typing import Optional, Generic, TypeVar, Any, TypedDict

from pydantic import BaseModel

class DocumentStatusModify(TypedDict):
    document_id: str
    document_status: int



class ChunkStatusModify(TypedDict):
    document_id: str
    document_status: int



# if __name__ == '__main__':
#     document_status_modify = DocumentStatusModify(document_id="1", document_status="1")
#     print(document_status_modify, type(document_status_modify))
#
#     dict1 =  {'document_id': '2', 'document_status': '1'}
#
#     chunk_status_modify = ChunkStatusModify(**dict1)
#     print(chunk_status_modify, type(chunk_status_modify))
#
#
#     chunk_status_modify2 = ChunkStatusModify(document_id="3", document_status="222")
#     print(chunk_status_modify2, type(chunk_status_modify2))
#
#
#     print(chunk_status_modify.document_id)
