import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";

function slug(label: string): string {
  return `field-${label.replace(/\W+/g, "-").toLowerCase()}`;
}

type FieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** Codes and times read as data, so they get the mono face. */
  data?: boolean;
};

export function Field({
  label,
  value,
  onChange,
  data,
  ...rest
}: FieldProps & Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  const id = slug(label);
  return (
    <label className={data ? "field data" : "field"} htmlFor={id}>
      <span>{label}</span>
      <input
        id={id}
        value={value}
        required
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      />
    </label>
  );
}

export function TextField({
  label,
  value,
  onChange,
  ...rest
}: Omit<FieldProps, "data"> &
  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "onChange">) {
  const id = slug(label);
  return (
    <label className="field" htmlFor={id}>
      <span>{label}</span>
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      />
    </label>
  );
}
