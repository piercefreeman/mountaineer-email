from abc import abstractmethod
from collections.abc import Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from functools import wraps
from inspect import isawaitable, isclass, signature
from pathlib import Path
from typing import Any, Coroutine, Generic, ParamSpec, cast
from uuid import uuid4

from fastapi import Request, params
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from pydantic import BaseModel

from mountaineer import ControllerBase, ManagedViewPath
from mountaineer.dependencies import isolate_dependency_only_function
from mountaineer.ssr import render_ssr

from mountaineer_email.render import EmailRenderBase, FilledOutEmail

RenderParameters = ParamSpec("RenderParameters")
RAW_RENDER_METHOD_NAME = "_mountaineer_email_raw_render"
HYDRATED_VIEW_BASE_ATTR = "_mountaineer_email_view_base_path"
HYDRATED_SCRIPTS_PREFIX_ATTR = "_mountaineer_email_scripts_prefix"


@asynccontextmanager
async def resolve_email_dependencies(
    *,
    callable: Any,
    request: Request | None = None,
    url: str = "/synthetic",
):
    dependant = get_dependant(call=callable, path=url)

    async with AsyncExitStack() as async_exit_stack:
        if not request:
            request = Request(
                scope={
                    "type": "http",
                    "path": url,
                    "path_params": {},
                    "query_string": b"",
                    "headers": [],
                    "fastapi_inner_astack": async_exit_stack,
                    "fastapi_function_astack": async_exit_stack,
                }
            )
        else:
            request.scope.setdefault("fastapi_inner_astack", async_exit_stack)
            request.scope.setdefault("fastapi_function_astack", async_exit_stack)

        payload = await solve_dependencies(
            request=request,
            dependant=dependant,
            async_exit_stack=async_exit_stack,
            embed_body_fields=False,
        )
        if payload.background_tasks:
            raise RuntimeError(
                "Background tasks are not supported when calling a static function, due to undesirable side-effects."
            )
        if payload.errors:
            raise RuntimeError(
                f"Errors encountered while resolving dependencies: {payload.errors}"
            )

        yield payload.values


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
        if cls.__name__ == "EmailControllerBase":
            return

        raw_render = cls.__dict__.get("render")
        if raw_render:
            setattr(cls, RAW_RENDER_METHOD_NAME, raw_render)

            @wraps(raw_render)
            async def wrapped_render(self, *args, **kwargs):
                if self._should_render_filled_email(args, kwargs):
                    return await self.render_obj(
                        cast(BaseModel | dict[str, Any], args[0])
                    )

                server_data = self._call_raw_render(*args, **kwargs)
                if isawaitable(server_data):
                    server_data = await server_data
                return server_data

            setattr(cls, "render", wrapped_render)

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

    def _get_raw_render(self):
        return getattr(self, RAW_RENDER_METHOD_NAME)

    def _call_raw_render(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> EmailRenderBase | Coroutine[Any, Any, EmailRenderBase]:
        return self._get_raw_render()(*args, **kwargs)

    def _should_render_filled_email(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> bool:
        if kwargs or len(args) != 1:
            return False

        input_models = self.get_input_models()
        if len(input_models) != 1:
            return False

        _, input_model = input_models[0]
        return isinstance(args[0], input_model) or isinstance(args[0], Mapping)

    async def _generate_email(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> FilledOutEmail:
        return await self._generate_email_with_request(None, *args, **kwargs)

    async def _generate_email_with_request(
        self,
        request: Request | None,
        *args: Any,
        **kwargs: Any,
    ) -> FilledOutEmail:
        self.hydrate_for_render()

        async with resolve_email_dependencies(
            callable=isolate_dependency_only_function(self._get_raw_render()),
            request=request,
            url=self.url,
        ) as values:
            render_kwargs: dict[str, Any] = {**kwargs, **values}
            server_data_raw = self._call_raw_render(*args, **cast(Any, render_kwargs))
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
            subject=server_data.email_metadata.subject,
            html_body=page_contents,
        )

    async def render_email(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> FilledOutEmail:
        return await self._generate_email(*args, **kwargs)

    async def render_email_with_request(
        self,
        request: Request | None,
        *args: Any,
        **kwargs: Any,
    ) -> FilledOutEmail:
        return await self._generate_email_with_request(request, *args, **kwargs)

    async def render_obj(
        self,
        render_obj: BaseModel | dict[str, Any],
        *,
        request: Request | None = None,
    ) -> FilledOutEmail:
        variable_key, variable_input = self.get_input_model()
        parsed_render_obj = (
            render_obj
            if isinstance(render_obj, variable_input)
            else variable_input.model_validate(render_obj)
        )
        if request is not None:
            return await self.render_email_with_request(
                request,
                **{variable_key: parsed_render_obj},
            )
        return await self.render_email(**{variable_key: parsed_render_obj})

    def resolve_paths(self, view_base: Path, force: bool = True) -> bool:
        found_dependencies = super().resolve_paths(view_base, force=force)
        setattr(self.__class__, HYDRATED_VIEW_BASE_ATTR, Path(view_base))
        setattr(self.__class__, HYDRATED_SCRIPTS_PREFIX_ATTR, self._scripts_prefix)
        return found_dependencies

    def hydrate_for_render(self) -> None:
        if self._view_base_path is not None and self._ssr_path is not None:
            return

        hydrated_scripts_prefix = getattr(
            self.__class__,
            HYDRATED_SCRIPTS_PREFIX_ATTR,
            None,
        )
        if hydrated_scripts_prefix is not None:
            self._scripts_prefix = hydrated_scripts_prefix

        hydrated_view_base = getattr(self.__class__, HYDRATED_VIEW_BASE_ATTR, None)
        if hydrated_view_base is not None:
            self.resolve_paths(hydrated_view_base, force=True)
            return

        if isinstance(self.view_path, ManagedViewPath):
            try:
                self.resolve_paths(self.view_path.get_root_link(), force=True)
                return
            except ValueError:
                pass

        if self._definition is None:
            raise ValueError(
                f"{self.__class__.__name__} cannot render from a fresh instance because its view root is unknown. "
                "Mount the controller once or define view_path as a ManagedViewPath with a root link."
            )

    def get_input_models(self) -> list[tuple[str, type[BaseModel]]]:
        """
        Returns the BaseModel inputs that define the email payload.

        """
        return [
            (key, signature_value.annotation)
            for key, signature_value in signature(
                self._get_raw_render()
            ).parameters.items()
            if (
                isclass(signature_value.annotation)
                and issubclass(signature_value.annotation, BaseModel)
                and not isinstance(signature_value.default, params.Depends)
            )
        ]

    def get_input_model(self) -> tuple[str, type[BaseModel]]:
        """
        Returns the primary BaseModel that defines the email.

        """
        variable_inputs = self.get_input_models()

        if len(variable_inputs) != 1:
            raise ValueError(
                f"Expected exactly one input model for {self.__class__.__name__} render(), got {variable_inputs}"
            )

        return variable_inputs[0]
