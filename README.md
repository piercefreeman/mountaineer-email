# mountaineer-email

Dependencies to easily format and send email with Mountaineer or FastAPI.

## Getting Started

Since email deliverability is nearly zero if you send with local linux utilities, you'll almost always want to use a 3rd party service. AWS SES and Resend are two of the most popular. This package is vendor agnostic and instead delegates the email sending to [mountaineer-cloud](https://github.com/piercefreeman/mountaineer-cloud). `mountaineer-email` providers.

TODO: Full example

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
                to_email=user.email,
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

To send the email, you'll want to import your daemon client:

```python
from mountaineer_email import SendEmail, SendEmailInput

class MyController(ControllerBase):
    ...

    @passthrough
    async def send_email(
        self,
        user: models.User = Depends(AuthDependencies.require_valid_user),
        daemon_client: DaemonClient = Depends(DaemonDependencies.get_daemon_client),
    ):
        await daemon_client.run_workflow(
            SendEmail,
            f"send_email_{uuid4()}",
            SendEmailInput.from_email_input(
                EmailController,
                email_input=EmailControllerRequest(
                    user_id=new_user.id,
                ),
            ),
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

We bundle an admin panel that allows you to preview your emails with different imports. You'll have to add these explicitly to your AppController.

```python
import mountaineer_email.controllers as email_admin_controllers

controller.register(email_admin_controllers.EmailHomeController())
controller.register(email_admin_controllers.EmailDetailController())
```
