import React from "react";
import { useServer } from "./_server/useServer";

const Page = () => {
  const serverState = useServer();

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight text-zinc-950">
        Templates
      </h2>
      <p className="mt-1 text-sm text-zinc-500">
        Select an email template to preview and test.
      </p>

      <div className="mt-8 divide-y divide-zinc-100">
        {serverState.emails.map((email) => (
          <a
            key={email.short_name}
            href={serverState.linkGenerator.emailDetailController({
              email_short: email.short_name,
            })}
            className="group flex items-center justify-between py-4 transition-colors first:pt-0"
          >
            <div>
              <span className="text-sm font-medium text-zinc-950 group-hover:text-zinc-600">
                {email.full_name}
              </span>
              <span className="ml-3 text-xs text-zinc-400">
                {email.short_name}
              </span>
            </div>
            <span className="text-xs text-zinc-300 transition-colors group-hover:text-zinc-500">
              &rarr;
            </span>
          </a>
        ))}
      </div>
    </div>
  );
};

export default Page;
