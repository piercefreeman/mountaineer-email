import { useServer } from "./_server/useServer";

const Page = () => {
	const serverState = useServer();

	return (
		<div>
			<div>
				<h2 className="text-lg/7 font-semibold text-zinc-950">Templates</h2>
				<p className="mt-1 text-sm/6 text-zinc-500">
					Select an email template to preview and test.
				</p>
			</div>

			<div className="mt-6 overflow-hidden rounded-lg border border-zinc-950/10 bg-white">
				<table className="w-full text-left">
					<thead>
						<tr className="border-b border-zinc-950/10">
							<th className="px-5 py-3 text-xs/5 font-medium uppercase tracking-wide text-zinc-500">
								Template
							</th>
							<th className="px-5 py-3 text-xs/5 font-medium uppercase tracking-wide text-zinc-500">
								Identifier
							</th>
							<th className="w-10 px-5 py-3" />
						</tr>
					</thead>
					<tbody className="divide-y divide-zinc-950/5">
						{serverState.emails.map((email) => (
							<tr
								key={email.short_name}
								className="group relative transition-colors hover:bg-zinc-950/[0.025]"
							>
								<td className="px-5 py-4">
									<a
										href={serverState.linkGenerator.emailDetailController({
											email_short: email.short_name,
										})}
										className="text-sm/6 font-medium text-zinc-950 before:absolute before:inset-0"
									>
										{email.full_name}
									</a>
								</td>
								<td className="px-5 py-4">
									<span className="font-mono text-xs/5 text-zinc-500">
										{email.short_name}
									</span>
								</td>
								<td className="px-5 py-4 text-right">
									<svg
										aria-hidden="true"
										className="inline-block h-4 w-4 text-zinc-400 transition-transform group-hover:translate-x-0.5 group-hover:text-zinc-600"
										fill="none"
										stroke="currentColor"
										strokeWidth={1.5}
										viewBox="0 0 24 24"
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											d="M8.25 4.5l7.5 7.5-7.5 7.5"
										/>
									</svg>
								</td>
							</tr>
						))}
					</tbody>
				</table>

				{serverState.emails.length === 0 && (
					<div className="flex flex-col items-center py-16 text-center">
						<div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100">
							<svg
								aria-hidden="true"
								className="h-5 w-5 text-zinc-400"
								fill="none"
								stroke="currentColor"
								strokeWidth={1.5}
								viewBox="0 0 24 24"
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
								/>
							</svg>
						</div>
						<p className="mt-4 text-sm/6 font-medium text-zinc-950">
							No templates
						</p>
						<p className="mt-1 text-sm/6 text-zinc-500">
							Register email controllers to see them here.
						</p>
					</div>
				)}
			</div>
		</div>
	);
};

export default Page;
