from pydantic import BaseModel


class WorkflowStatusSummary(BaseModel):
    public_id: str
    module: str
    status_code: str
    status_name: str
    is_active: bool
    sort_order: int