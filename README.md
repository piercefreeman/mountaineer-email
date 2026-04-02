# mountaineer-email

Dependencies to easily format and send email with Mountaineer or FastAPI.

## Getting Started

Since email deliverability is nearly zero if you send with local linux utilities, you'll almost always want to use a 3rd party service. This package is provider agnostic and delegates delivery integrations to [mountaineer-cloud](https://github.com/piercefreeman/mountaineer-cloud) provider packages such as Resend.

The core flow is:

1. Define an `EmailControllerBase` with a typed payload model.
2. Register that controller on your `AppController`. If you want the bundled preview/admin UI, also register the `mountaineer-email` plugin.
3. Inject a typed email template with `Depends(get_email_template(...))`.
4. Call `await template.render(...)` with your payload to produce a `FilledOutEmail`.

```python
from fastapi import Depends
from pydantic import BaseModel

from mountaineer import AppController
from mountaineer_cloud.primitives import EmailBody, EmailMessage, EmailRecipient
from mountaineer_cloud.providers.resend import ResendCore, ResendDependencies
from mountaineer_email import (
    EmailControllerBase,
    EmailMetadata,
    EmailRenderBase,
    get_email_template,
)


class WelcomeEmailPayload(BaseModel):
    first_name: str
    last_name: str


class WelcomeEmailRender(EmailRenderBase):
    name: str


class WelcomeEmailController(EmailControllerBase):
    view_path = "emails/welcome/page.tsx"

    async def render(
        self,
        payload: WelcomeEmailPayload,
    ) -> WelcomeEmailRender:
        name = f"{payload.first_name} {payload.last_name}"

        return WelcomeEmailRender(
            name=name,
            email_metadata=EmailMetadata(
                subject=f"Welcome {name}",
            ),
        )


controller = AppController()
controller.register(WelcomeEmailController())


async def send_welcome_email(
    template: WelcomeEmailController = Depends(
        get_email_template(WelcomeEmailController)
    ),
    resend: ResendCore = Depends(ResendDependencies.get_resend_core),
) -> str:
    filled_email = await template.render(
        WelcomeEmailPayload(
            first_name="Ada",
            last_name="Lovelace",
        )
    )

    message = EmailMessage[ResendCore](
        sender=EmailRecipient(
            email="noreply@example.com",
            display_name="Example App",
        ),
        recipient=EmailRecipient(email="ada@example.com"),
        subject=filled_email.subject,
        body=EmailBody(html=filled_email.html_body),
    )

    return await message.send(resend)
```

## Designing

You want your emails to be beautiful, but email design is notoriously a headache. Email clients lag significantly in adoption of html features and only implement a subset of the CSS spec. If it gives you any sense of the current ecosystem, marking up with `<table>` still rules the day. See the [currently supported](https://www.campaignmonitor.com/css/) css attributes, for reference.

For complex email templates, you'll probably want to use a dedicated designer app or plugin for something like Figma. For simpler email layouts we bundle basic Tailwind support by inlining the CSS markup that are usually defined in classes.

## Usage

To setup a new email, you'll need both the view (equivalent to a Mountaineer frontend view) and a controller (similarly equivalent to a Mountaineer controller). A typical project layout looks like:

```
myproject/
├── controllers/
├── emails/
│   └── email1.py
└── views/
    ├── app/
    ├── emails/
    │   ├── email1/
    │   │   └── page.tsx
    │   └── template.tsx
    └── project.json
```

This layout mirrors the frontend views exactly - we support individual pages and the nesting of layouts to wrap your emails in a common design.

Unlike your conventional routes, emails aren't interactive. You can think of them as running without javascript within an email client. So the initial representation of your React component will be the permanent representation of the page.

We compile down your React components into raw html using Mountaineer's regular SSR renderer. We then perform some email-specific transformations that allow your styling to show up properly for browsers.

Define your view:

```tsx
import React from "react";
import { useServer } from "./_server/useServer";

const Page = () => {
  const serverState = useServer();

  return (
      <div className="space-y-4">
        {serverState.user_name && <div>Hi {serverState.user_name}!</div>}
      </div>
  );
};

export default Page;
```

And then your associated controller:

```python
from uuid import UUID

from fastapi import Depends
from mountaineer_email import EmailControllerBase, EmailMetadata, EmailRenderBase
from pydantic import BaseModel
from iceaxe import DBConnection

from mountaineer import CoreDependencies, LinkAttribute, ManagedViewPath, Metadata
from iceaxe.mountaineer import DatabaseDependencies

from myproject import models

class WelcomeEmailRequest(BaseModel):
    user_id: UUID


class WelcomeEmailRender(EmailRenderBase):
    user_name: str | None


class WelcomeEmailController(EmailControllerBase[WelcomeEmailRequest]):
    view_path = "emails/welcome/page.tsx"

    async def render(
        self,
        payload: WelcomeEmailRequest,
        db_session: DBConnection = Depends(DatabaseDependencies.get_db_connection),
    ) -> WelcomeEmailRender:
        user = await db_session.get(models.User, payload.user_id)
        if not user:
            raise ValueError(f"User not found: {payload.user_id}")

        return WelcomeEmailRender(
            user_name=user.name,
            email_metadata=EmailMetadata(
                subject="Welcome!",
            ),
            metadata=Metadata(
                links=[LinkAttribute(rel="stylesheet", href="/static/auth_main.css")]
            ),
        )
```

Dependencies declared on `render()` are resolved when you call `template.render(...)` or `template.render_email(...)`. For example, you can combine the payload with another injected value:

```python
from fastapi import Depends


def get_email_signature() -> str:
    return "Thanks for joining us!"


class WelcomeEmailController(EmailControllerBase[WelcomeEmailRequest]):
    view_path = "emails/welcome/page.tsx"

    async def render(
        self,
        payload: WelcomeEmailRequest,
        db_session: DBConnection = Depends(DatabaseDependencies.get_db_connection),
        signature: str = Depends(get_email_signature),
    ) -> WelcomeEmailRender:
        user = await db_session.get(models.User, payload.user_id)
        if not user:
            raise ValueError(f"User not found: {payload.user_id}")

        return WelcomeEmailRender(
            user_name=f"{user.name} {signature}",
            email_metadata=EmailMetadata(
                subject="Welcome!",
            ),
        )
```

Then register your application's email controllers on the `AppController`. If you want the bundled email admin routes, register the plugin separately:

```python
from mountaineer_email.plugin import plugin as email_plugin

from myproject import emails

controller = AppController(
    config=config,
    global_metadata=Metadata(
        links=[LinkAttribute(rel="stylesheet", href="/static/app_main.css")]
    ),
    custom_builders=[
        PostCSSBundler(),
    ],
)

controller.register(emails.WelcomeEmailController())

if ENV == "development":
    controller.register(email_plugin)
```

Registering `email_plugin` only adds the bundled preview controllers and their prebuilt assets. Your own `EmailControllerBase` subclasses still need their own `controller.register(...)` calls so Mountaineer can build and resolve them.

`mountaineer-email` only owns the rendering and preview flow. Provider-specific delivery settings should come from the matching `mountaineer-cloud` provider config, for example `ResendConfig` if you're sending through Resend.

To render a filled email from application code, resolve a typed template with `get_email_template(...)` and call `render(...)` with your request model:

```python
from fastapi import Depends

from mountaineer_email import get_email_template


async def send_preview(
    template: WelcomeEmailController = Depends(
        get_email_template(WelcomeEmailController)
    ),
) -> FilledOutEmail:
    filled_email = await template.render(
        WelcomeEmailRequest(user_id=user_id),
    )
```

To send the same email in a background workflow, we provide a convenience workflow that you can use in your own apps. Serialize the controller reference in the main app and pass the request payload through to `SendEmail`. This lets the worker reload the controller later, even though it does not have the full Mountaineer app graph mounted:

```python
from uuid import UUID

from pydantic import BaseModel, EmailStr

from mountaineer_email import SendEmail
from mountaineer_email.registry import serialize_controller
from my_app.email.welcome import WelcomeEmailController, WelcomeEmailRequest

async def enqueue_welcome_email(
    *,
    user_id: UUID,
    user_email: EmailStr,
    user_name: str | None,
) -> None:
    workflow = SendEmail()

    await workflow.run(
        email_controller=serialize_controller(WelcomeEmailController),
        email_input=WelcomeEmailRequest(user_id=user_id).model_dump(mode="json"),
        to_email=str(user_email),
        to_name=user_name,
        from_email="noreply@example.com",
        from_name="Example App",
    )
```

### Inliner

Since regular tailwind will render css to a 3rd party stylesheet - that can't be read by most email browsers - you'll want to inline the styles of your tailwind components so they show up as `<div style=xyz>`. We recommend you use `@react-email/tailwind` since it has a lot of helper utilities out of the box for tailwind's variables:

```bash
cd project/views && npm install @react-email/tailwind
```

```tsx
import { Tailwind } from "@react-email/tailwind";

const Email = () => {
  return (
    <Tailwind>
      <button className="bg-blue-500">Click me!</button>
    </Tailwind>
  );
};

export default Email;
```

## Admin Panel

We bundle an admin panel at `/admin/email/` that lets you preview registered email controllers. Mountaineer plugins are registered directly on `AppController`, so add the packaged plugin instead of manually instantiating `EmailHomeController` and `EmailDetailController`:

```python
from mountaineer_email.plugin import plugin as email_plugin

if ENV == "development":
    controller.register(email_plugin)
```

This only mounts the preview UI. Continue to register each application email controller normally, for example `controller.register(emails.WelcomeEmailController())`.

## Development

If you update the admin UI files, you'll need to build the artifacts for inclusion in the published library. We do this automatically when distributing through CI, so this is just when you're making changes and testing locally:

```bash
uv run build-email
```
