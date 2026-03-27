import React from "react";

const Home = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-6">
      <div className="max-w-sm text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-950">
          <svg
            className="h-5 w-5 text-white"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
            />
          </svg>
        </div>
        <h1 className="mt-6 text-lg/7 font-semibold tracking-tight text-zinc-950">
          Redirecting to email previews
        </h1>
        <p className="mt-2 text-sm/6 text-zinc-500">
          If your browser does not follow the redirect automatically, open the
          email admin directly.
        </p>
        <a
          className="mt-6 inline-flex items-center justify-center rounded-lg bg-zinc-950 px-4 py-2.5 text-sm/6 font-semibold text-white shadow-sm transition-colors hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-950 focus:ring-offset-2 active:bg-zinc-700"
          href="/admin/email/"
        >
          Open Email Admin
        </a>
      </div>
    </div>
  );
};

export default Home;
