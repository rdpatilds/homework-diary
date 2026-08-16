import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";

function slug(label: string): string {
  return `field-${label.replace(/\W+/g, "-").toLowerCase()}`;
}

type FieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** Columns to occupy on the six-column staff form. Ignored on narrow screens,
   * where every field is full width. */
  span?: 1 | 2 | 3 | 4 | 6;
};

function classes(span: FieldProps["span"]): string {
  return span ? `field c${span}` : "field";
}

export function Field({
  label,
  value,
  onChange,
  span,
  ...rest
}: FieldProps & Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  const id = slug(label);
  return (
    <div className={classes(span)}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        value={value}
        required
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      />
    </div>
  );
}

export function TextField({
  label,
  value,
  onChange,
  span,
  ...rest
}: FieldProps &
  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "onChange">) {
  const id = slug(label);
  return (
    <div className={classes(span)}>
      <label htmlFor={id}>{label}</label>
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...rest}
      />
    </div>
  );
}
