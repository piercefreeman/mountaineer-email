import React, { ReactNode } from "react";

const Layout = ({ children }: { children: ReactNode }) => {
  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto max-w-3xl px-6 py-10">
        <header className="pb-8">
          <h1 className="text-sm font-semibold uppercase tracking-widest text-zinc-950">
            Admin
          </h1>
          <p className="mt-1 text-xs tracking-wide text-zinc-400">
            Email Preview
          </p>
          <div className="mt-4 h-px bg-zinc-200" />
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
};

export default Layout;
