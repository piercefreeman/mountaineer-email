import React from "react";
// eslint-disable-next-line import/no-unresolved
import { useServer } from "./_server";

const Page = () => {
  const serverState = useServer();

  return (
    <main className="space-y-3 rounded-lg border border-slate-300 p-4">
      <h1 className="text-lg font-semibold text-blue-500">
        Hello {serverState.recipient_name}
      </h1>
      <p className="text-sm text-slate-700">{serverState.message}</p>
    </main>
  );
};

export default Page;
