import React, { ReactNode } from "react";

const Layout = ({ children }: { children: ReactNode }) => {
  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-950/10 bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-6 lg:px-8">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-950">
            <svg
              className="h-3.5 w-3.5 text-white"
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
          <span className="text-sm/6 font-semibold text-zinc-950">
            Email Admin
          </span>
          <span className="text-sm/6 text-zinc-400">
            Preview & Testing
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
        {children}
      </main>
    </div>
  );
};

export default Layout;
