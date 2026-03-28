import { useState } from "react";
import { useServer } from "./_server/useServer";
import MockBody from "./mock_body";

const Page = () => {
	const serverState = useServer();
	const [mockBody, setMockBody] = useState(serverState.mock_body_echo || {});

	return (
		<div>
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-3">
					<a
						className="group inline-flex items-center gap-1.5 text-sm/6 text-zinc-500 transition-colors hover:text-zinc-950"
						href={serverState.linkGenerator.emailHomeController()}
					>
						<svg
							aria-hidden="true"
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
						Templates
					</a>
					<span className="text-zinc-300">/</span>
					<h2 className="text-sm/6 font-semibold text-zinc-950">
						{serverState.email_short}
					</h2>
				</div>
			</div>

			{serverState.exception && (
				<div
					className="mt-6 rounded-lg border border-zinc-950/10 bg-white px-5 py-4"
					role="alert"
				>
					<div className="flex items-start gap-3">
						<svg
							aria-hidden="true"
							className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400"
							fill="none"
							stroke="currentColor"
							strokeWidth={2}
							viewBox="0 0 24 24"
						>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
							/>
						</svg>
						<div className="min-w-0 flex-1">
							<p className="text-sm/6 font-medium text-zinc-950">
								Render failed
							</p>
							<p className="mt-1 text-sm/6 text-zinc-600 break-words">
								{serverState.exception}
							</p>
						</div>
					</div>
				</div>
			)}

			<div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
				{/* Left panel: controls */}
				<div className="lg:col-span-1">
					<div className="rounded-lg border border-zinc-950/10 bg-white">
						<div className="border-b border-zinc-950/5 px-5 py-3">
							<h3 className="text-xs/5 font-semibold uppercase tracking-widest text-zinc-950">
								Parameters
							</h3>
						</div>
						<div className="px-5 py-5">
							{serverState.render_json_schema != null ? (
								<MockBody
									schema={serverState.render_json_schema}
									request={mockBody}
									updateRequest={setMockBody}
								/>
							) : (
								<p className="text-sm/6 text-zinc-500">
									No parameters required.
								</p>
							)}

							<button
								type="button"
								className="mt-6 inline-flex w-full items-center justify-center rounded-lg bg-zinc-950 px-4 py-2.5 text-sm/6 font-semibold text-white shadow-sm transition-colors hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-950 focus:ring-offset-2 active:bg-zinc-700"
								onClick={() => {
									window.location.href =
										serverState.linkGenerator.emailDetailController({
											email_short: serverState.email_short,
											mock_body: JSON.stringify(mockBody),
										});
								}}
							>
								Render Preview
							</button>
						</div>
					</div>
				</div>

				{/* Right panel: preview */}
				<div className="lg:col-span-2">
					{serverState.rendered ? (
						<div className="rounded-lg border border-zinc-950/10 bg-white">
							<div className="border-b border-zinc-950/5 px-5 py-3">
								<dl className="flex flex-wrap gap-x-6 gap-y-1">
									<div className="flex items-baseline gap-2">
										<dt className="text-xs/5 font-medium text-zinc-400 uppercase tracking-wide">
											To
										</dt>
										<dd className="text-sm/6 text-zinc-950">
											{serverState.rendered.to_email}
										</dd>
									</div>
									<div className="flex items-baseline gap-2">
										<dt className="text-xs/5 font-medium text-zinc-400 uppercase tracking-wide">
											Subject
										</dt>
										<dd className="text-sm/6 text-zinc-950">
											{serverState.rendered.subject}
										</dd>
									</div>
								</dl>
							</div>

							<HTMLPreview html={serverState.rendered.html_body} />
						</div>
					) : (
						<div className="flex h-full items-center justify-center rounded-lg border border-dashed border-zinc-950/10 bg-white py-24">
							<div className="text-center">
								<svg
									aria-hidden="true"
									className="mx-auto h-8 w-8 text-zinc-300"
									fill="none"
									stroke="currentColor"
									strokeWidth={1}
									viewBox="0 0 24 24"
								>
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
									/>
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
									/>
								</svg>
								<p className="mt-3 text-sm/6 text-zinc-500">
									Click{" "}
									<span className="font-medium text-zinc-700">
										Render Preview
									</span>{" "}
									to see the email output
								</p>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
};

const HTMLPreview = ({ html }: { html: string }) => {
	const [showCode, setShowCode] = useState(false);

	return (
		<div>
			<div className="flex items-center justify-between border-b border-zinc-950/5 px-5 py-2">
				<span className="text-xs/5 font-medium text-zinc-500">
					{showCode ? "HTML Source" : "Visual Preview"}
				</span>
				<div className="flex rounded-md bg-zinc-100 p-0.5">
					<button
						type="button"
						className={`rounded px-2.5 py-1 text-xs/4 font-medium transition-colors ${
							!showCode
								? "bg-white text-zinc-950 shadow-sm"
								: "text-zinc-500 hover:text-zinc-700"
						}`}
						onClick={() => setShowCode(false)}
					>
						Preview
					</button>
					<button
						type="button"
						className={`rounded px-2.5 py-1 text-xs/4 font-medium transition-colors ${
							showCode
								? "bg-white text-zinc-950 shadow-sm"
								: "text-zinc-500 hover:text-zinc-700"
						}`}
						onClick={() => setShowCode(true)}
					>
						Source
					</button>
				</div>
			</div>
			{!showCode ? (
				<iframe
					srcDoc={html}
					className="h-[40rem] w-full"
					style={{ display: "block" }}
					title="Email preview"
				/>
			) : (
				<div className="max-h-[40rem] overflow-auto bg-zinc-950 p-5">
					<pre className="whitespace-pre-wrap text-xs/5 text-zinc-400 font-mono">
						{breakLongLines(html)}
					</pre>
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
		const nextLine = currentLine.length > 0 ? `${currentLine} ${word}` : word;

		if (nextLine.length > maxLength && currentLine.length > 0) {
			formattedText += `${currentLine}\n`;
			currentLine = word;
		} else {
			currentLine = nextLine;
		}
	});

	formattedText += currentLine;

	return formattedText;
};

export default Page;
