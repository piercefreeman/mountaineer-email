import React from "react";

const Home = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-100 px-6">
      <div className="max-w-md rounded-3xl bg-white p-10 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-stone-400">
          Example App
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-stone-950">
          Redirecting to email previews
        </h1>
        <p className="mt-3 text-sm leading-6 text-stone-600">
          If your browser does not follow the redirect automatically, open the
          email admin directly.
        </p>
        <a
          className="mt-6 inline-flex rounded-full bg-stone-950 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-stone-800"
          href="/admin/email/"
        >
          Open Email Admin
        </a>
      </div>
    </div>
  );
};

export default Home;
