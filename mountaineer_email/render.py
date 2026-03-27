from pydantic import BaseModel, Field
from typing_extensions import dataclass_transform

from mountaineer import RenderBase
from mountaineer.render import ReturnModelMetaclass


class EmailMetadata(BaseModel):
    subject: str


@dataclass_transform(kw_only_default=True, field_specifiers=(Field,))
class EmailModelMetaclass(ReturnModelMetaclass):
    INTERNAL_RENDER_FIELDS = ["metadata", "email_metadata"]


class EmailRenderBase(RenderBase, metaclass=EmailModelMetaclass):
    """
    Values placed into the email renderbase will be accessible to the controller
    via its `useServer()` hook.

    """

    email_metadata: EmailMetadata = Field(exclude=True)

    model_config = {
        # Frozen parameters are required so we can hash the render values to check
        # for changes in our SSR renderer
        "frozen": True,
    }


class FilledOutEmail(BaseModel):
    subject: str
    html_body: str
