import React from "react";
import { SimpleSchema } from "./_server/models";

const MockBody = ({
  schema,
  request,
  updateRequest,
}: {
  schema: SimpleSchema;
  request: any;
  updateRequest: (request: any) => void;
}) => {
  return (
    <div>
      <h3 className="text-xs/5 font-semibold uppercase tracking-widest text-zinc-950">
        {schema.title}
      </h3>
      <p className="mt-1 text-xs/5 text-zinc-500">
        Provide values to render the template.
      </p>
      <div className="mt-5 space-y-5">
        {schema.fields.map((field) => (
          <div key={field.field_name}>
            <div className="mb-2 flex items-baseline gap-2">
              <label className="text-sm/6 font-medium text-zinc-950">
                {field.field_name}
              </label>
              {field.required ? (
                <span className="text-[0.6875rem]/4 font-medium text-zinc-400">
                  required
                </span>
              ) : (
                <span className="text-[0.6875rem]/4 text-zinc-400">
                  optional
                </span>
              )}
            </div>
            <input
              type="text"
              className="w-full rounded-lg border border-zinc-950/10 bg-transparent px-3.5 py-2 text-sm/6 text-zinc-950 placeholder:text-zinc-400 hover:border-zinc-950/20 focus:border-zinc-950 focus:outline-none focus:ring-2 focus:ring-zinc-950/5 transition-colors"
              placeholder={`Enter ${field.field_name}...`}
              value={request[field.field_name] || ""}
              onChange={(e) => {
                updateRequest({
                  ...request,
                  [field.field_name]: e.target.value,
                });
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default MockBody;
