from abc import abstractmethod
from inspect import isawaitable, isclass, signature
from typing import Any, Coroutine, Generic, ParamSpec, cast
from uuid import uuid4

from fastapi import params
from pydantic import BaseModel

from mountaineer import ControllerBase, ManagedViewPath
from mountaineer.dependencies import (
    get_function_dependencies,
    isolate_dependency_only_function,
)
from mountaineer.ssr import render_ssr

from mountaineer_email.render import EmailRenderBase, FilledOutEmail

RenderParameters = ParamSpec("RenderParameters")


class EmailControllerBase(ControllerBase[RenderParameters], Generic[RenderParameters]):
    """
    Inspired by our regular routing controllers, but these:

    - Only support rendering, since javascript actions can't be used as part
        of email bodies
    - Don't have accessible URLs since they'll be rendered adhoc
    - Must manually request and receive any user-based dependencies, since we don't
        have access to MountaineerAuth at email-send time

    """

    view_path: str | ManagedViewPath

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Auto-register email controller classes (but not the base class itself)
        if cls.__name__ != "EmailControllerBase":
            from mountaineer_email.registry import register_email_controller_class

            register_email_controller_class(cls)

    def __init__(self):
        # We need this definition to be included in our global OpenAPI spec, so we add
        # a synthetic URL
        # TODO: Generalize the LayoutController convention (ie. urlless) to support this
        # use case without having to mock the URL
        self.url = f"/email/{self.__class__.__name__}-{uuid4()}/"
        super().__init__()

    @abstractmethod
    def render(
        self, *payload: RenderParameters.args, **kwargs: RenderParameters.kwargs
    ) -> EmailRenderBase | Coroutine[Any, Any, EmailRenderBase]:
        pass

    async def _generate_email(
        self, *args: RenderParameters.args, **kwargs: RenderParameters.kwargs
    ) -> FilledOutEmail:
        async with get_function_dependencies(
            callable=isolate_dependency_only_function(self.render)
        ) as values:
            server_data_raw = self.render(*args, **kwargs, **values)  # type: ignore
            if isawaitable(server_data_raw):
                server_data_raw = await server_data_raw
            server_data = cast(EmailRenderBase, server_data_raw)

        # This isn't expected to happen, but we add a check to typeguard the following logic
        if not isinstance(server_data, EmailRenderBase):
            raise ValueError(
                f"EmailController.render() must return a EmailRenderBase instance, not {type(server_data)}"
            )

        cached_server_script: str
        # Support app-mounted routes (preview) and standalone routes (daemons)
        # TODO: We should probably mount email controllers to an AppController, even if that
        # app controller is only used within the daemon actions, to share the rendering logic
        # with the main codebase.
        if self._definition:
            cache = self._definition.resolve_cache()
            cached_server_script = cache.cached_server_script
        else:
            # Read from the SSR path itself
            if not self._ssr_path:
                raise ValueError(
                    f"{self.__class__.__name__} must have a _ssr_path defined since no _definition was found"
                )
            cached_server_script = self._ssr_path.read_text()

        render_params = {self.__class__.__name__: server_data.model_dump(mode="json")}

        ssr_html = render_ssr(
            cached_server_script,
            render_params,
            hard_timeout=10,
        )

        page_contents = f"""
        <html>
        <head>
        </head>
        <body>
        {ssr_html}
        </body>
        </html>
        """

        if not self._view_base_path:
            raise ValueError(
                f"{self.__class__.__name__} must have a view_base_path defined"
            )

        return FilledOutEmail(
            to_email=server_data.email_metadata.to_email,
            subject=server_data.email_metadata.subject,
            html_body=page_contents,
        )

    def get_input_model(self) -> tuple[str, BaseModel]:
        """
        Returns the primary BaseModel that defines the email, or None
        if one is not specified.

        """
        variable_inputs = [
            (key, signature_value.annotation)
            for key, signature_value in signature(self.render).parameters.items()
            if (
                isclass(signature_value.annotation)
                and issubclass(signature_value.annotation, BaseModel)
                and not isinstance(signature_value.default, params.Depends)
            )
        ]

        if len(variable_inputs) != 1:
            raise ValueError(
                f"Expected exactly one input model for {self.__class__.__name__} render(), got {variable_inputs}"
            )

        return cast(tuple[str, BaseModel], variable_inputs[0])
