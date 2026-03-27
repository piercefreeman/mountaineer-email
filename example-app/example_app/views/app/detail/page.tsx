
import React, { useState } from "react";
import { useServer } from "./_server/useServer";

const Page = () => {
  const serverState = useServer();
  const [text, setText] = useState("");

  return (
    <div className="min-h-screen bg-white px-6 py-16">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <h1 className="text-lg/7 font-semibold text-zinc-950">Task Details</h1>
          <a
            className="group inline-flex items-center gap-1.5 text-sm/6 text-zinc-500 transition-colors hover:text-zinc-950"
            href={serverState.linkGenerator.homeController({})}
          >
            <svg
              className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-0.5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 19.5L8.25 12l7.5-7.5"
              />
            </svg>
            Back
          </a>
        </div>

        <div className="mt-1 h-px bg-zinc-950/10" />

        <div className="mt-8 rounded-lg border border-zinc-950/10">
          <div className="border-b border-zinc-950/5 px-5 py-4">
            <h2 className="text-xs/5 font-medium uppercase tracking-wide text-zinc-400">
              Current Description
            </h2>
            <p className="mt-2 text-sm/6 text-zinc-950">
              {serverState.description}
            </p>
          </div>

          <div className="px-5 py-5">
            <h2 className="text-xs/5 font-medium uppercase tracking-wide text-zinc-400">
              Update Description
            </h2>
            <div className="mt-3 flex gap-3">
              <input
                className="flex-1 rounded-lg border border-zinc-950/10 bg-transparent px-3.5 py-2 text-sm/6 text-zinc-950 placeholder:text-zinc-400 hover:border-zinc-950/20 focus:border-zinc-950 focus:outline-none focus:ring-2 focus:ring-zinc-950/5 transition-colors"
                type="text"
                value={text}
                placeholder="Enter new description..."
                onChange={(e) => setText(e.target.value)}
              />
              <button
                className="inline-flex items-center rounded-lg bg-zinc-950 px-4 py-2 text-sm/6 font-semibold text-white shadow-sm transition-colors hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-950 focus:ring-offset-2 active:bg-zinc-700 disabled:opacity-40"
                onClick={async () => {
                  await serverState.update_text({
                    detail_id: serverState.id,
                    requestBody: {
                      description: text,
                    },
                  });
                  setText("");
                }}
                disabled={!text.trim()}
              >
                Update
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Page;
