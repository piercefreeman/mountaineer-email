# mountaineer-email

Dependencies to easily format and send email with Mountaineer or FastAPI.

## Getting Started

Since email deliverability is nearly zero if you send with local linux utilities, you'll almost always want to use a 3rd party service. This package is provider agnostic and delegates delivery integrations to [mountaineer-cloud](https://github.com/piercefreeman/mountaineer-cloud) provider packages such as Resend.

The core flow is:

1. Define an `EmailControllerBase` with a typed payload model.
2. Register that controller on your `AppController`.
3. Inject the mounted email template with `Depends(get_email_template(...))`.
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

Then add these controllers to your AppController:

```python
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
```

`mountaineer-email` only owns the rendering and preview flow. Provider-specific delivery settings should come from the matching `mountaineer-cloud` provider config, for example `ResendConfig` if you're sending through Resend.

To render a filled email from application code, resolve the mounted template instance from the registry and call `render(...)` with your request model:

```python
from fastapi import Depends

from mountaineer_email import get_email_template


async def send_preview(
    template: WelcomeEmailController = Depends(
        get_email_template(WelcomeEmailController)
    ),
):
    filled_email = await template.render(
        WelcomeEmailRequest(user_id=user_id),
    )
```

### Inliner

To inline Tailwind (similar to the juice package), we recommend you use `@react-email/tailwind` since it has a lot of helper utilities out of the box for tailwind's variables:

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

We bundle an admin panel that allows you to preview your emails with different imports. You'll have to add these explicitly to your AppController. We suggest conditionally adding these to your webservice if you're running locally:

```python
import mountaineer_email.controllers as email_admin_controllers

if ENV == "development":
    controller.register(email_admin_controllers.EmailHomeController())
    controller.register(email_admin_controllers.EmailDetailController())
```

## Development

If you update the admin UI files, you'll need to build the artifacts for inclusion in the published library. We do this automatically when distributing through CI, so this is just when you're making changes and testing locally:

```bash
uv run build-email
```
