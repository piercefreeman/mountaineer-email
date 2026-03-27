import React, { useState } from "react";
import { useServer } from "./_server/useServer";
import MockBody from "./mock_body";

const Page = () => {
  const serverState = useServer();
  const [mockBody, setMockBody] = useState(serverState.mock_body_echo || {});

  return (
    <div>
      <a
        className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 transition-colors hover:text-zinc-950"
        href={serverState.linkGenerator.emailHomeController()}
      >
        <span>&larr;</span>
        <span>Back</span>
      </a>

      <div className="mt-6">
        {serverState.exception && (
          <div
            className="mb-6 border border-zinc-200 bg-zinc-50 px-5 py-4 text-sm text-zinc-700"
            role="alert"
          >
            <span className="font-semibold">Error</span>
            <span className="mx-2 text-zinc-300">|</span>
            {serverState.exception}
          </div>
        )}

        {serverState.render_json_schema != null && (
          <div className="mt-6">
            <MockBody
              schema={serverState.render_json_schema}
              request={mockBody}
              updateRequest={setMockBody}
            />
          </div>
        )}

        <button
          className="mt-8 w-full bg-zinc-950 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 active:bg-zinc-700"
          onClick={() => {
            window.location.href =
              serverState.linkGenerator.emailDetailController({
                email_short: serverState.email_short,
                mock_body: JSON.stringify(mockBody),
              });
          }}
        >
          Render
        </button>

        {serverState.rendered && (
          <div className="mt-12">
            <div className="mb-6 space-y-3">
              <div className="flex items-baseline gap-4">
                <span className="w-16 text-right text-xs font-medium uppercase tracking-wider text-zinc-400">
                  To
                </span>
                <span className="text-sm text-zinc-950">
                  {serverState.rendered.to_email}
                </span>
              </div>
              <div className="flex items-baseline gap-4">
                <span className="w-16 text-right text-xs font-medium uppercase tracking-wider text-zinc-400">
                  Subject
                </span>
                <span className="text-sm text-zinc-950">
                  {serverState.rendered.subject}
                </span>
              </div>
              <div className="h-px bg-zinc-100" />
            </div>
            <HTMLPreview html={serverState.rendered.html_body} />
          </div>
        )}
      </div>
    </div>
  );
};

const HTMLPreview = ({ html }: { html: string }) => {
  const [showCode, setShowCode] = useState(false);

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <button
          className="text-xs font-medium text-zinc-400 transition-colors hover:text-zinc-950"
          onClick={() => setShowCode(!showCode)}
        >
          {showCode ? "Preview" : "Source"}
        </button>
      </div>
      {!showCode ? (
        <iframe
          srcDoc={html}
          className="h-[32rem] w-full border border-zinc-200"
        />
      ) : (
        <div className="max-h-[32rem] overflow-auto bg-zinc-950 p-6 text-xs leading-relaxed text-zinc-400">
          <pre className="whitespace-pre-wrap">{breakLongLines(html)}</pre>
        </div>
      )}
    </div>
  );
};

const breakLongLines = (text: string, maxLength = 100) => {
  const words = text.split(" ");

  let currentLine = "";
  let formattedText = "";

  words.forEach((word) => {
    if ((currentLine + word).length > maxLength) {
      formattedText += currentLine + "\n";
      currentLine = word;
    } else {
      currentLine += (currentLine.length > 0 ? " " : "") + word;
    }
  });

  formattedText += currentLine;

  return formattedText;
};

export default Page;
