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
      <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-950">
        {schema.title}
      </h3>
      <div className="mt-4 space-y-5">
        {schema.fields.map((field) => (
          <div key={field.field_name}>
            <div className="mb-1.5 flex items-baseline gap-2">
              <label className="text-sm font-medium text-zinc-950">
                {field.field_name}
              </label>
              <span className="text-xs text-zinc-400">
                {field.required ? "required" : "optional"}
              </span>
            </div>
            <input
              type="text"
              className="w-full border-0 border-b border-zinc-200 bg-transparent px-0 py-2 text-sm text-zinc-950 placeholder:text-zinc-300 focus:border-zinc-950 focus:ring-0"
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
