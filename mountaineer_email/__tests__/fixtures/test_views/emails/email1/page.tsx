import React from "react";
// eslint-disable-next-line import/no-unresolved
import { useServer } from "./_server";

const Page = () => {
  const serverState = useServer();

  return (
    <div>
      <h1 className="text-blue-500">Page {serverState.initial_value}</h1>
    </div>
  );
};
export default Page;
